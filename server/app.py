"""Small same-origin JSON API and static server backed by SQLite."""
from __future__ import annotations

import hashlib
import hmac
import json
import math
import mimetypes
import os
import re
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone
from http import HTTPStatus
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse
from urllib.request import Request, urlopen

from server.db import CATALOG_PATH, ROOT, initialize, transaction
from server.rate_limit import limiter

COOKIE_NAME = "ac_session"
SESSION_DAYS = 14
PBKDF2_ROUNDS = 310_000
MAX_BODY = 1_000_000
ORDER_STATUSES = {"Aguardando pagamento", "Aguardando análise", "Pago", "Em fabricação", "Enviado", "Entregue", "Cancelado"}


class ApiError(Exception):
    def __init__(self, status: int, message: str):
        self.status, self.message = status, message


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, PBKDF2_ROUNDS)
    return f"pbkdf2_sha256${PBKDF2_ROUNDS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, rounds, salt, expected = encoded.split("$")
        if algorithm != "pbkdf2_sha256":
            return False
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), int(rounds)).hex()
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def valid_cpf(value: object) -> bool:
    cpf = re.sub(r"\D", "", str(value or ""))
    if len(cpf) != 11 or cpf == cpf[0] * 11:
        return False
    digits = [int(char) for char in cpf]
    first = (sum(digit * weight for digit, weight in zip(digits[:9], range(10, 1, -1))) * 10) % 11 % 10
    second = (sum(digit * weight for digit, weight in zip(digits[:10], range(11, 1, -1))) * 10) % 11 % 10
    return digits[9:] == [first, second]


def public_order(row: sqlite3.Row, include_shipping_operations: bool = False) -> dict:
    data = json.loads(row["data_json"])
    data.update({
        "number": row["number"], "status": row["status"], "payment": "Mercado Pago" if row["payment_provider"] == "mercadopago" else row["payment_method"],
        "subtotal": row["subtotal_cents"] / 100, "discount": row["discount_cents"] / 100,
        "shippingPrice": row["shipping_cents"] / 100, "total": row["total_cents"] / 100,
        "date": row["created_at"],
        "paymentStatus": row["payment_status"],
        "paymentStatusLabel": {"pending": "Aguardando confirmação", "approved": "Aprovado", "rejected": "Recusado", "cancelled": "Cancelado", "expired": "Expirado", "refunded": "Reembolsado", "charged_back": "Contestação"}.get(row["payment_status"], row["payment_status"]),
        "paymentProvider": row["payment_provider"],
        "checkoutUrl": row["checkout_url"],
    })
    if include_shipping_operations:
        data["shippingStage"] = row["shipping_stage"]
        data["shippingLabelUrl"] = row["shipping_label_url"]
    return data


def payment_configuration() -> tuple[str, str, str]:
    token = os.environ.get("MP_ACCESS_TOKEN", "").strip()
    secret = os.environ.get("MP_WEBHOOK_SECRET", "").strip()
    public_url = os.environ.get("APP_PUBLIC_URL", "").strip().rstrip("/")
    if not token or not secret or not public_url.startswith("https://"):
        raise ApiError(503, "Checkout indisponível. Configure as credenciais e a URL HTTPS do Mercado Pago.")
    return token, secret, public_url


def mercado_pago_request(path: str, token: str, payload: dict | None = None) -> dict:
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    if body is not None:
        headers["Content-Type"] = "application/json"
        headers["X-Idempotency-Key"] = secrets.token_hex(16)
    request = Request(f"https://api.mercadopago.com{path}", data=body, headers=headers, method="GET" if body is None else "POST")
    try:
        with urlopen(request, timeout=12) as response:
            result = json.loads(response.read())
    except Exception as exc:
        print(f"Mercado Pago request failed: {type(exc).__name__}")
        raise ApiError(502, "Não foi possível iniciar o pagamento. Tente novamente.") from exc
    if not isinstance(result, dict):
        raise ApiError(502, "Resposta inválida do provedor de pagamento.")
    return result


def melhor_envio_request(path: str, payload: dict) -> list | dict:
    token = os.environ.get("ME_ACCESS_TOKEN", "").strip()
    origin_cep = re.sub(r"\D", "", os.environ.get("ME_FROM_POSTAL_CODE", ""))
    if not token or len(origin_cep) != 8:
        raise ApiError(503, "Frete indisponível. Configure o token e o CEP de origem do Melhor Envio.")
    base_url = "https://sandbox.melhorenvio.com.br" if os.environ.get("ME_SANDBOX", "1") == "1" else "https://melhorenvio.com.br"
    user_agent = os.environ.get("ME_USER_AGENT", "Angélica Casa (suporte@seudominio.com.br)").strip()
    body = json.dumps({"from": {"postal_code": origin_cep}, **payload}).encode("utf-8")
    request = Request(f"{base_url}{path}", data=body, headers={
        "Authorization": f"Bearer {token}", "Accept": "application/json",
        "Content-Type": "application/json", "User-Agent": user_agent,
    }, method="POST")
    try:
        with urlopen(request, timeout=12) as response:
            result = json.loads(response.read())
    except Exception as exc:
        print(f"Melhor Envio request failed: {type(exc).__name__}")
        raise ApiError(502, "O Melhor Envio não conseguiu calcular este frete. Confira o CEP e tente novamente.") from exc
    if not isinstance(result, (list, dict)):
        raise ApiError(502, "Resposta inválida do Melhor Envio.")
    return result


def shipping_quote(db: sqlite3.Connection, items: object, destination_cep: str) -> list[dict]:
    cep = re.sub(r"\D", "", destination_cep)
    if len(cep) != 8 or not isinstance(items, list) or not items or len(items) > 30:
        raise ApiError(400, "Informe CEP e produtos válidos para calcular o frete.")
    try:
        weight_per_item = float(os.environ.get("ME_PRODUCT_WEIGHT_KG", "0"))
        depth_cm = float(os.environ.get("ME_PRODUCT_DEPTH_CM", "0"))
    except ValueError as exc:
        raise ApiError(503, "Configure peso e profundidade reais dos pacotes no Melhor Envio.") from exc
    if not math.isfinite(weight_per_item) or not math.isfinite(depth_cm) or weight_per_item <= 0 or depth_cm <= 0:
        raise ApiError(503, "Configure peso e profundidade reais dos pacotes no Melhor Envio.")
    products = []
    for item in items:
        try:
            product_id, quantity = int(item["id"]), int(item["qty"])
            width, height = float(item["width"]), float(item["height"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ApiError(400, "Produto inválido para cálculo do frete.") from exc
        if not 1 <= quantity <= 20 or not 40 <= width <= 500 or not 40 <= height <= 500:
            raise ApiError(400, "Medidas fora do limite para calcular o frete.")
        product = db.execute("SELECT price_cents,data_json FROM products WHERE id=?", (product_id,)).fetchone()
        if not product:
            raise ApiError(400, "Produto não encontrado para calcular o frete.")
        name = json.loads(product["data_json"])["name"]
        unitary_value = round(product["price_cents"] * max(0.4, width * height / 10000)) / 100
        products.append({
            "id": str(product_id), "name": str(name)[:100], "quantity": quantity,
            "width": width, "height": height, "length": depth_cm,
            "weight": weight_per_item, "unitary_value": unitary_value,
            "insurance_value": unitary_value,
        })
    result = melhor_envio_request("/api/v2/me/shipment/calculate", {"to": {"postal_code": cep}, "products": products})
    quotes = []
    for entry in result:
        if not isinstance(entry, dict) or entry.get("error"):
            continue
        try:
            price = float(entry.get("custom_price", entry.get("price")))
            delivery_days = int(entry.get("custom_delivery_time", entry.get("delivery_time", 0)))
            service_id = int(entry["id"])
        except (KeyError, TypeError, ValueError):
            continue
        if price < 0 or not math.isfinite(price):
            continue
        company = entry.get("company") or {}
        packages = []
        for package in entry.get("packages", []):
            dimensions = package.get("dimensions") or {}
            try:
                packages.append({
                    "height": float(dimensions["height"]), "width": float(dimensions["width"]),
                    "length": float(dimensions["length"]), "weight": float(package["weight"]),
                })
            except (KeyError, TypeError, ValueError):
                packages = []
                break
        quotes.append({
            "id": str(service_id), "name": str(entry.get("name", "Frete"))[:80],
            "company": str(company.get("name", "Transportadora"))[:80],
            "price": round(price, 2), "deliveryDays": delivery_days,
            "packages": packages,
        })
    return sorted(quotes, key=lambda quote: quote["price"])


def melhor_envio_sender() -> dict:
    document = re.sub(r"\D", "", os.environ.get("ME_FROM_DOCUMENT", ""))
    postal_code = re.sub(r"\D", "", os.environ.get("ME_FROM_POSTAL_CODE", ""))
    sender = {
        "name": os.environ.get("ME_FROM_NAME", "").strip(),
        "email": os.environ.get("ME_FROM_EMAIL", "").strip(),
        "phone": re.sub(r"\D", "", os.environ.get("ME_FROM_PHONE", "")),
        "address": os.environ.get("ME_FROM_ADDRESS", "").strip(),
        "number": os.environ.get("ME_FROM_NUMBER", "").strip(),
        "complement": os.environ.get("ME_FROM_COMPLEMENT", "").strip(),
        "district": os.environ.get("ME_FROM_DISTRICT", "").strip(),
        "city": os.environ.get("ME_FROM_CITY", "").strip(),
        "postal_code": postal_code,
        "state_abbr": os.environ.get("ME_FROM_UF", "").strip().upper(),
    }
    required = (sender["name"], sender["email"], sender["phone"], sender["address"], sender["number"], sender["district"], sender["city"])
    if not all(required) or len(postal_code) != 8 or len(document) not in {11, 14} or not re.fullmatch(r"[A-Z]{2}", sender["state_abbr"]):
        raise ApiError(503, "Configure os dados completos do remetente e CPF/CNPJ no ambiente da loja.")
    if len(document) == 11:
        sender["document"] = document
        sender["state_register"] = "ISENTO"
    else:
        sender["company_document"] = document
        sender["state_register"] = os.environ.get("ME_FROM_STATE_REGISTER", "ISENTO").strip() or "ISENTO"
    return sender


def extract_provider_id(response: list | dict) -> str:
    entries = response if isinstance(response, list) else [response]
    for item in entries:
        if isinstance(item, dict):
            identifier = item.get("id") or (item.get("shipment") or {}).get("id")
            if identifier is not None:
                return str(identifier)
    return ""


def create_payment_preference(order_number: str, email: str, name: str, payment_items: list[dict]) -> dict:
    token, _, public_url = payment_configuration()
    starts_at = datetime.now(timezone.utc)
    expires_at = starts_at + timedelta(days=3)
    return mercado_pago_request("/checkout/preferences", token, {
        "items": payment_items,
        "payer": {"email": email, "name": name[:120]},
        "external_reference": order_number,
        "metadata": {"order_number": order_number},
        "back_urls": {
            "success": f"{public_url}/?payment_return=success&external_reference={order_number}",
            "pending": f"{public_url}/?payment_return=pending&external_reference={order_number}",
            "failure": f"{public_url}/?payment_return=failure&external_reference={order_number}",
        },
        "auto_return": "approved",
        "notification_url": f"{public_url}/api/payments/mercadopago/webhook",
        "expires": True,
        "expiration_date_from": starts_at.isoformat(timespec="milliseconds").replace("+00:00", "Z"),
        "expiration_date_to": expires_at.isoformat(timespec="milliseconds").replace("+00:00", "Z"),
    })


def expire_unpaid_orders(db: sqlite3.Connection) -> None:
    expired = db.execute(
        "SELECT id,number,data_json FROM orders WHERE payment_status IN ('pending','rejected','cancelled') AND status='Aguardando pagamento' AND inventory_reserved=1 AND datetime(created_at)<=datetime('now','-3 days')"
    ).fetchall()
    for order in expired:
        for item in json.loads(order["data_json"])["items"]:
            db.execute("UPDATE products SET stock=stock+? WHERE id=?", (item["qty"], item["id"]))
        db.execute(
            "UPDATE orders SET status='Cancelado',payment_status='expired',inventory_reserved=0,checkout_url='' WHERE id=?",
            (order["id"],),
        )


def valid_mercado_pago_signature(signature: str, request_id: str, data_id: str, secret: str) -> bool:
    values = dict(part.strip().split("=", 1) for part in signature.split(",") if "=" in part)
    timestamp, received = values.get("ts", ""), values.get("v1", "")
    if not timestamp or not received or not data_id:
        return False
    manifest = f"id:{data_id};"
    if request_id:
        manifest += f"request-id:{request_id};"
    manifest += f"ts:{timestamp};"
    expected = hmac.new(secret.encode(), manifest.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, received)


class StoreHTTPServer(ThreadingHTTPServer):
    daemon_threads = True
    request_queue_size = 64


class StoreHandler(BaseHTTPRequestHandler):
    server_version = "AngelicaCasa/1.0"

    def log_message(self, fmt: str, *args) -> None:
        if os.environ.get("APP_ACCESS_LOG") == "1":
            super().log_message(fmt, *args)

    def end_headers(self) -> None:
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "strict-origin-when-cross-origin")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        super().end_headers()

    def send_json(self, status: int, value: object, headers: dict[str, str] | None = None) -> None:
        body = json.dumps(value, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        for key, val in (headers or {}).items():
            self.send_header(key, val)
        self.end_headers()
        self.wfile.write(body)

    def read_json(self) -> dict:
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError as exc:
            raise ApiError(400, "Tamanho de requisição inválido.") from exc
        if length <= 0 or length > MAX_BODY:
            raise ApiError(413 if length > MAX_BODY else 400, "Corpo da requisição inválido.")
        if "application/json" not in self.headers.get("Content-Type", ""):
            raise ApiError(415, "Envie dados no formato JSON.")
        try:
            value = json.loads(self.rfile.read(length))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise ApiError(400, "JSON inválido.") from exc
        if not isinstance(value, dict):
            raise ApiError(400, "Formato da requisição inválido.")
        return value

    def session_user(self, db: sqlite3.Connection) -> sqlite3.Row | None:
        cookie = SimpleCookie(self.headers.get("Cookie", ""))
        morsel = cookie.get(COOKIE_NAME)
        if not morsel:
            return None
        token_hash = hashlib.sha256(morsel.value.encode()).hexdigest()
        return db.execute(
            "SELECT users.* FROM sessions JOIN users ON users.id=sessions.user_id WHERE sessions.token_hash=? AND sessions.expires_at>?",
            (token_hash, now_iso()),
        ).fetchone()

    def require_user(self, db: sqlite3.Connection, admin: bool = False) -> sqlite3.Row:
        user = self.session_user(db)
        if not user:
            raise ApiError(401, "Entre na sua conta para continuar.")
        if admin and user["role"] != "admin":
            raise ApiError(403, "Acesso restrito.")
        return user

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        # Static files do not need a database connection. This keeps image,
        # CSS and JavaScript requests off the SQLite connection path.
        if not parsed.path.startswith("/api/"):
            self.serve_static(parsed.path)
            return
        try:
            with transaction() as db:
                expire_unpaid_orders(db)
                if parsed.path == "/api/health":
                    self.send_json(200, {"ok": True, "database": "sqlite"})
                elif parsed.path == "/api/catalog":
                    products = []
                    for row in db.execute("SELECT data_json, price_cents, stock FROM products ORDER BY id"):
                        product = json.loads(row["data_json"])
                        product["price"] = row["price_cents"] / 100
                        product["stock"] = row["stock"]
                        products.append(product)
                    catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
                    pickup_enabled = os.environ.get("STORE_PICKUP_ENABLED", "0") == "1"
                    pickup_address = os.environ.get("STORE_PICKUP_ADDRESS", "").strip()
                    pickup = {
                        "enabled": pickup_enabled and bool(pickup_address),
                        "label": os.environ.get("STORE_PICKUP_LABEL", "Retirada no ateliê").strip(),
                        "address": pickup_address,
                    }
                    self.send_json(200, {"products": products, "categories": catalog["categories"], "faqs": catalog["faqs"], "pickup": pickup})
                elif parsed.path == "/api/me":
                    user = self.session_user(db)
                    self.send_json(200, {"user": {"name": user["name"], "email": user["email"], "role": user["role"]} if user else None})
                elif parsed.path == "/api/orders":
                    user = self.require_user(db)
                    rows = db.execute("SELECT * FROM orders WHERE user_id=? ORDER BY id DESC", (user["id"],)).fetchall()
                    self.send_json(200, {"orders": [public_order(row, include_shipping_operations=True) for row in rows]})
                elif parsed.path == "/api/admin/orders":
                    self.require_user(db, admin=True)
                    rows = db.execute("SELECT * FROM orders ORDER BY id DESC").fetchall()
                    self.send_json(200, {"orders": [public_order(row) for row in rows]})
                elif parsed.path == "/api/admin/products":
                    self.require_user(db, admin=True)
                    self.send_json(200, {"products": [dict(id=r["id"], stock=r["stock"]) for r in db.execute("SELECT id,stock FROM products ORDER BY id")]})
                elif parsed.path == "/api/admin/contacts":
                    self.require_user(db, admin=True)
                    rows = db.execute("SELECT id,name,email,interest,message,created_at FROM contacts ORDER BY id DESC LIMIT 500").fetchall()
                    self.send_json(200, {"contacts": [dict(row) for row in rows]})
                elif parsed.path == "/api/admin/subscribers":
                    self.require_user(db, admin=True)
                    rows = db.execute("SELECT email,created_at FROM subscribers ORDER BY id DESC LIMIT 2000").fetchall()
                    self.send_json(200, {"subscribers": [dict(row) for row in rows]})
                elif parsed.path.startswith("/api/orders/track/"):
                    number = unquote(parsed.path.rsplit("/", 1)[-1]).strip()
                    row = db.execute("SELECT number,status,payment_status,checkout_url,created_at FROM orders WHERE number=?", (number,)).fetchone()
                    if not row:
                        raise ApiError(404, "Pedido não encontrado.")
                    self.send_json(200, {"number": row["number"], "status": row["status"], "paymentStatus": row["payment_status"], "paymentStatusLabel": {"pending": "Aguardando confirmação", "approved": "Aprovado", "rejected": "Recusado", "cancelled": "Cancelado", "expired": "Expirado", "refunded": "Reembolsado", "charged_back": "Contestação"}.get(row["payment_status"], row["payment_status"]), "checkoutUrl": row["checkout_url"], "date": row["created_at"]})
                elif parsed.path.startswith("/api/"):
                    raise ApiError(404, "Rota não encontrada.")
        except ApiError as exc:
            self.send_json(exc.status, {"error": exc.message})
        except (sqlite3.Error, OSError) as exc:
            print(f"Request error: {exc}")
            self.send_json(500, {"error": "Erro interno. Tente novamente."})

    def do_POST(self) -> None:
        try:
            parsed_path = urlparse(self.path).path
            limits = {
                "/api/auth/login": (10, 900),
                "/api/auth/register": (5, 3600),
                "/api/contact": (10, 3600),
                "/api/newsletter": (10, 3600),
                "/api/orders": (5, 3600),
                "/api/shipping/quote": (20, 3600),
            }
            if parsed_path in limits:
                address = self.client_address[0]
                if os.environ.get("APP_TRUST_PROXY") == "1":
                    address = self.headers.get("X-Forwarded-For", "").split(",", 1)[0].strip() or address
                limit, window = limits[parsed_path]
                retry_after = limiter.consume(f"{parsed_path}:{address}", limit, window)
                if retry_after:
                    self.send_json(429, {"error": "Muitas tentativas. Aguarde antes de tentar novamente."}, {"Retry-After": str(retry_after)})
                    return
            data = self.read_json()
            with transaction() as db:
                expire_unpaid_orders(db)
                parsed = urlparse(self.path)
                if parsed.path == "/api/payments/mercadopago/webhook":
                    token, secret, _ = payment_configuration()
                    query = parse_qs(parsed.query)
                    data_id = str((query.get("data.id") or [""])[0])
                    if data.get("type") != "payment" or not re.fullmatch(r"\d{1,30}", data_id):
                        self.send_json(200, {"ok": True})
                        return
                    signature = self.headers.get("x-signature", "")
                    request_id = self.headers.get("x-request-id", "")
                    if not valid_mercado_pago_signature(signature, request_id, data_id, secret):
                        raise ApiError(401, "Assinatura do webhook inválida.")
                    payment_resource = mercado_pago_request(f"/v1/payments/{data_id}", token)
                    number = str(payment_resource.get("external_reference", ""))
                    amount = payment_resource.get("transaction_amount")
                    if (payment_resource.get("currency_id") != "BRL" or not isinstance(amount, (int, float))
                            or not re.fullmatch(r"AC-[A-F0-9]{12}", number)):
                        self.send_json(200, {"ok": True})
                        return
                    order = db.execute("SELECT * FROM orders WHERE number=?", (number,)).fetchone()
                    if not order or round(float(amount) * 100) != order["total_cents"]:
                        self.send_json(200, {"ok": True})
                        return
                    gateway_status = str(payment_resource.get("status", "unknown"))[:40]
                    if gateway_status == "approved":
                        enough_stock = order["inventory_reserved"] == 1
                        if not enough_stock and order["status"] != "Cancelado":
                            needed: dict[int, int] = {}
                            for item in json.loads(order["data_json"])["items"]:
                                needed[item["id"]] = needed.get(item["id"], 0) + item["qty"]
                            enough_stock = all(
                                (product := db.execute("SELECT stock FROM products WHERE id=?", (product_id,)).fetchone())
                                and product["stock"] >= quantity
                                for product_id, quantity in needed.items()
                            )
                            if enough_stock:
                                for product_id, quantity in needed.items():
                                    db.execute("UPDATE products SET stock=stock-? WHERE id=?", (quantity, product_id))
                        if enough_stock and order["status"] != "Cancelado":
                            db.execute("UPDATE orders SET status=CASE WHEN status='Aguardando pagamento' THEN 'Pago' ELSE status END,inventory_reserved=1,payment_status='approved',payment_id=? WHERE id=?", (data_id, order["id"]))
                        else:
                            db.execute("UPDATE orders SET status='Aguardando análise',payment_status='approved',payment_id=? WHERE id=?", (data_id, order["id"]))
                    elif order["payment_status"] != "approved":
                        db.execute("UPDATE orders SET payment_status=?,payment_id=? WHERE id=?", (gateway_status, data_id, order["id"]))
                    self.send_json(200, {"ok": True})
                elif parsed.path == "/api/auth/register":
                    name, email, password = (str(data.get(k, "")).strip() for k in ("name", "email", "password"))
                    if len(name) < 2 or len(name) > 120 or not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email) or not 10 <= len(password) <= 128:
                        raise ApiError(400, "Informe nome, e-mail válido e senha com pelo menos 10 caracteres.")
                    try:
                        cursor = db.execute("INSERT INTO users(name,email,password_hash) VALUES(?,?,?)", (name, email.lower(), hash_password(password)))
                    except sqlite3.IntegrityError as exc:
                        raise ApiError(409, "Este e-mail já possui cadastro.") from exc
                    self.login_response(db, cursor.lastrowid)
                elif self.path == "/api/auth/login":
                    email, password = str(data.get("email", "")).strip().lower(), str(data.get("password", ""))
                    user = db.execute("SELECT * FROM users WHERE email=? COLLATE NOCASE", (email,)).fetchone()
                    if not user or len(password) > 128 or not verify_password(password, user["password_hash"]):
                        raise ApiError(401, "E-mail ou senha incorretos.")
                    self.login_response(db, user["id"])
                elif self.path == "/api/auth/logout":
                    cookie = SimpleCookie(self.headers.get("Cookie", ""))
                    morsel = cookie.get(COOKIE_NAME)
                    if morsel:
                        db.execute("DELETE FROM sessions WHERE token_hash=?", (hashlib.sha256(morsel.value.encode()).hexdigest(),))
                    db.commit()
                    secure = "; Secure" if os.environ.get("APP_SECURE_COOKIE") == "1" else ""
                    self.send_json(200, {"ok": True}, {"Set-Cookie": f"{COOKIE_NAME}=; Path=/; HttpOnly; SameSite=Lax; Max-Age=0{secure}"})
                elif parsed.path == "/api/shipping/quote":
                    cep = str(data.get("cep", ""))
                    quotes = shipping_quote(db, data.get("items"), cep)
                    self.send_json(200, {"quotes": quotes})
                elif re.fullmatch(r"/api/admin/orders/AC-[A-F0-9]{12}/shipping/(prepare|purchase|generate|print)", parsed.path):
                    self.require_user(db, admin=True)
                    match = re.fullmatch(r"/api/admin/orders/(AC-[A-F0-9]{12})/shipping/(prepare|purchase|generate|print)", parsed.path)
                    number, action = match.groups()
                    if not os.environ.get("ME_ACCESS_TOKEN", "").strip():
                        raise ApiError(503, "Conecte a conta Melhor Envio antes de preparar etiquetas.")
                    order = db.execute("SELECT * FROM orders WHERE number=?", (number,)).fetchone()
                    if not order:
                        raise ApiError(404, "Pedido não encontrado.")
                    if order["payment_status"] != "approved" or not order["inventory_reserved"] or order["status"] == "Cancelado":
                        raise ApiError(409, "Só é possível preparar o envio de um pedido pago e ativo.")
                    order_data = json.loads(order["data_json"])
                    if order_data.get("shipping") == "retirada":
                        raise ApiError(409, "Este pedido foi marcado para retirada no ateliê.")
                    shipment_id, stage = order["shipping_id"], order["shipping_stage"]
                    if action == "prepare":
                        if stage or shipment_id:
                            raise ApiError(409, "Este pedido já tem uma operação de envio iniciada.")
                        invoice_key = re.sub(r"\D", "", str(data.get("invoiceKey", "")))
                        if len(invoice_key) != 44:
                            raise ApiError(400, "Informe a chave de acesso de 44 dígitos da NF-e.")
                        sender = melhor_envio_sender()
                        recipient = order_data["customer"]
                        recipient_document = recipient.get("document", "")
                        if not re.fullmatch(r"\d{11}", recipient_document) or len(recipient.get("phone", "")) < 10:
                            raise ApiError(409, "O pedido precisa ter CPF e telefone do destinatário para gerar a etiqueta.")
                        packages = order_data.get("shippingPackages") or []
                        if not packages:
                            raise ApiError(409, "A cotação não retornou volumes compatíveis com a geração da etiqueta.")
                        products = [{"name": item["name"], "quantity": str(item["qty"]), "unitary_value": item["price"]} for item in order_data["items"]]
                        volumes = [{key: package[key] for key in ("height", "width", "length", "weight")} for package in packages]
                        payload = {
                            "service": int(order_data["shipping"]), "from": sender,
                            "to": {
                                "name": recipient["name"], "email": recipient["email"], "phone": recipient["phone"],
                                "document": recipient_document, "state_register": "ISENTO",
                                "address": recipient["street"], "complement": recipient["complement"],
                                "number": recipient["number"], "district": recipient["neighborhood"],
                                "city": recipient["city"], "postal_code": recipient["cep"],
                                "country_id": "BR", "state_abbr": recipient["uf"],
                            },
                            "products": products, "volumes": volumes,
                            "options": {
                                "platform": "Angelica Casa", "insurance_value": order["subtotal_cents"] / 100,
                                "receipt": False, "own_hand": False, "reverse": False,
                                "invoice": {"key": invoice_key},
                                "tags": [{"tag": number, "url": None}],
                            },
                        }
                        cursor = db.execute("UPDATE orders SET shipping_stage='preparing' WHERE number=? AND shipping_stage=''", (number,))
                        if cursor.rowcount != 1:
                            raise ApiError(409, "Outra ação já está preparando este envio.")
                        db.commit()
                        response = melhor_envio_request("/api/v2/me/cart", payload)
                        shipment_id = extract_provider_id(response)
                        if not shipment_id:
                            raise ApiError(502, "O Melhor Envio não retornou o identificador do envio.")
                        db.execute("UPDATE orders SET shipping_id=?,shipping_stage='cart' WHERE number=?", (shipment_id, number))
                        db.commit()
                        self.send_json(200, {"ok": True, "stage": "cart"})
                    elif action == "purchase":
                        if stage != "cart" or not shipment_id:
                            raise ApiError(409, "Prepare o envio antes de comprar a etiqueta.")
                        cursor = db.execute("UPDATE orders SET shipping_stage='checkout_started' WHERE number=? AND shipping_stage='cart'", (number,))
                        if cursor.rowcount != 1:
                            raise ApiError(409, "A compra desta etiqueta já foi iniciada. Verifique o painel Melhor Envio.")
                        db.commit()
                        melhor_envio_request("/api/v2/me/shipment/checkout", {"orders": [shipment_id]})
                        db.execute("UPDATE orders SET shipping_stage='purchased' WHERE number=?", (number,))
                        db.commit()
                        self.send_json(200, {"ok": True, "stage": "purchased"})
                    elif action == "generate":
                        if stage != "purchased" or not shipment_id:
                            raise ApiError(409, "Compre a etiqueta antes de solicitar a geração.")
                        cursor = db.execute("UPDATE orders SET shipping_stage='generation_started' WHERE number=? AND shipping_stage='purchased'", (number,))
                        if cursor.rowcount != 1:
                            raise ApiError(409, "A geração desta etiqueta já foi iniciada. Verifique o painel Melhor Envio.")
                        db.commit()
                        melhor_envio_request("/api/v2/me/shipment/generate", {"orders": [shipment_id]})
                        db.execute("UPDATE orders SET shipping_stage='generated' WHERE number=?", (number,))
                        db.commit()
                        self.send_json(200, {"ok": True, "stage": "generated"})
                    else:
                        if stage not in {"generated", "printed"} or not shipment_id:
                            raise ApiError(409, "Gere a etiqueta antes de solicitar o arquivo para impressão.")
                        response = melhor_envio_request("/api/v2/me/shipment/print", {"orders": [shipment_id], "mode": "private"})
                        label_url = ""
                        entries = response if isinstance(response, list) else [response]
                        for entry in entries:
                            if isinstance(entry, dict):
                                candidate = entry.get("url") or entry.get("link") or entry.get("label_url")
                                if isinstance(candidate, str) and candidate.startswith("https://"):
                                    label_url = candidate
                                    break
                        if not label_url:
                            raise ApiError(502, "O Melhor Envio não retornou o link privado da etiqueta.")
                        db.execute("UPDATE orders SET shipping_stage='printed',shipping_label_url=? WHERE number=?", (label_url, number))
                        db.commit()
                        self.send_json(200, {"ok": True, "stage": "printed", "labelUrl": label_url})
                elif self.path == "/api/orders":
                    user = self.session_user(db)
                    customer = data.get("customer") or {}
                    if not isinstance(customer, dict):
                        raise ApiError(400, "Dados do cliente inválidos.")
                    if customer.get("terms") is not True:
                        raise ApiError(400, "Aceite as políticas da loja antes de concluir o pedido.")
                    email = user["email"] if user else str(customer.get("email", "")).strip().lower()
                    name = user["name"] if user else str(customer.get("name", "")).strip()
                    cep = re.sub(r"\D", "", str(customer.get("cep", "")))
                    if len(name) < 2 or not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email) or len(cep) != 8 or not customer.get("street") or not customer.get("city"):
                        raise ApiError(400, "Informe nome, e-mail e endereço completo.")
                    items = data.get("items")
                    if not isinstance(items, list) or not items or len(items) > 30:
                        raise ApiError(400, "O pedido precisa ter entre 1 e 30 itens.")
                    payment = data.get("payment")
                    if payment != "mercado_pago":
                        raise ApiError(400, "Forma de pagamento inválida.")
                    payment_configuration()
                    subtotal, safe_items, payment_items = 0, [], []
                    requested_quantities: dict[int, int] = {}
                    for item in items:
                        try:
                            product_id, quantity = int(item["id"]), int(item["qty"])
                            width, height = float(item["width"]), float(item["height"])
                        except (KeyError, TypeError, ValueError) as exc:
                            raise ApiError(400, "Item do pedido inválido.") from exc
                        if not 1 <= quantity <= 20 or not 40 <= width <= 500 or not 40 <= height <= 500:
                            raise ApiError(400, "Quantidade ou medidas fora do limite permitido.")
                        product = db.execute("SELECT * FROM products WHERE id=?", (product_id,)).fetchone()
                        if not product:
                            raise ApiError(400, "Um produto do pedido não está disponível.")
                        requested_quantities[product_id] = requested_quantities.get(product_id, 0) + quantity
                        if product["stock"] < requested_quantities[product_id]:
                            raise ApiError(409, f"Estoque insuficiente para {json.loads(product['data_json'])['name']}.")
                        info = json.loads(product["data_json"])
                        price = product["price_cents"]
                        area = max(0.4, width * height / 10000)
                        line_cents = round(price * area) * quantity
                        subtotal += line_cents
                        payment_items.append({
                            "id": str(product_id),
                            "title": f"{info['name']} · {width:g} × {height:g} cm · {quantity} un.",
                            "quantity": 1,
                            "currency_id": "BRL",
                            "unit_price": round(line_cents / 100, 2),
                        })
                        safe_items.append({"key": secrets.token_hex(8), "id": product_id, "name": info["name"], "image": info["image"], "color": str(item.get("color", ""))[:80], "install": "parede" if item.get("install") == "parede" else "vão", "width": width, "height": height, "price": line_cents / 100 / quantity, "qty": quantity})
                    coupon = str(data.get("coupon", "")).strip()
                    discount = 0
                    if coupon:
                        raise ApiError(400, "Cupom inválido.")
                    shipping_mode = data.get("shipping", "retirada")
                    if not isinstance(shipping_mode, str):
                        raise ApiError(400, "Forma de entrega inválida.")
                    if shipping_mode == "retirada":
                        if os.environ.get("STORE_PICKUP_ENABLED", "0") != "1" or not os.environ.get("STORE_PICKUP_ADDRESS", "").strip():
                            raise ApiError(400, "Retirada no ateliê não está disponível. Escolha uma opção de entrega.")
                        shipping = 0
                        shipping_name = os.environ.get("STORE_PICKUP_LABEL", "Retirada no ateliê").strip()
                    else:
                        if not valid_cpf(customer.get("cpf")):
                            raise ApiError(400, "Informe o CPF do destinatário para concluir o frete.")
                        if (len(re.sub(r"\D", "", str(customer.get("phone", "")))) < 10
                                or not customer.get("number") or not customer.get("neighborhood")
                                or not re.fullmatch(r"[A-Za-z]{2}", str(customer.get("uf", "")))):
                            raise ApiError(400, "Complete telefone, número, bairro e UF para a entrega.")
                        quotes = shipping_quote(db, items, cep)
                        selected_quote = next((quote for quote in quotes if quote["id"] == shipping_mode), None)
                        if not selected_quote:
                            raise ApiError(409, "A cotação selecionada expirou. Calcule o frete novamente.")
                        shipping = round(selected_quote["price"] * 100)
                        shipping_name = f"{selected_quote['company']} · {selected_quote['name']}"
                    if shipping:
                        payment_items.append({
                            "id": "frete",
                            "title": f"Frete · {shipping_name}",
                            "quantity": 1,
                            "currency_id": "BRL",
                            "unit_price": round(shipping / 100, 2),
                        })
                    number = "AC-" + secrets.token_hex(6).upper()
                    order_data = {"items": safe_items, "customer": {"name": name, "email": email, "phone": re.sub(r"\D", "", str(customer.get("phone", "")))[:20], "document": re.sub(r"\D", "", str(customer.get("cpf", "")))[:11], "cep": cep, "street": str(customer.get("street", ""))[:180], "number": str(customer.get("number", ""))[:30], "complement": str(customer.get("complement", ""))[:100], "neighborhood": str(customer.get("neighborhood", ""))[:100], "city": str(customer.get("city", ""))[:100], "uf": str(customer.get("uf", ""))[:2], "note": str(customer.get("note", ""))[:500]}, "shipping": shipping_mode, "shippingName": shipping_name, "shippingPackages": selected_quote["packages"] if shipping_mode != "retirada" else []}
                    total = max(0, subtotal - discount + shipping)
                    preference = create_payment_preference(number, email, name, payment_items)
                    access_token = os.environ.get("MP_ACCESS_TOKEN", "")
                    checkout_url = preference.get("sandbox_init_point") if access_token.startswith("TEST-") else preference.get("init_point")
                    if not isinstance(checkout_url, str) or not checkout_url.startswith("https://"):
                        raise ApiError(502, "O provedor não retornou uma URL de pagamento válida.")
                    for product_id, quantity in requested_quantities.items():
                        cursor = db.execute("UPDATE products SET stock=stock-? WHERE id=? AND stock>=?", (quantity, product_id, quantity))
                        if cursor.rowcount != 1:
                            raise ApiError(409, "O estoque mudou durante o checkout. Revise sua sacola e tente novamente.")
                    db.execute("INSERT INTO orders(number,user_id,email,payment_method,payment_provider,payment_status,preference_id,checkout_url,subtotal_cents,discount_cents,shipping_cents,total_cents,inventory_reserved,data_json) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (number, user["id"] if user else None, email, payment, "mercadopago", "pending", str(preference.get("id", "")), checkout_url, subtotal, discount, shipping, total, 1, json.dumps(order_data, ensure_ascii=False)))
                    db.commit()
                    order = db.execute("SELECT * FROM orders WHERE number=?", (number,)).fetchone()
                    self.send_json(201, {"order": public_order(order), "checkoutUrl": checkout_url})
                elif self.path == "/api/contact":
                    name, email = str(data.get("name", "")).strip(), str(data.get("email", "")).strip().lower()
                    message, interest = str(data.get("message", "")).strip(), str(data.get("interest", "Dúvida sobre produto"))[:100]
                    if len(name) < 2 or not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email) or not message or len(message) > 4000:
                        raise ApiError(400, "Preencha nome, e-mail válido e mensagem.")
                    db.execute("INSERT INTO contacts(name,email,interest,message) VALUES(?,?,?,?)", (name[:120], email, interest, message))
                    db.commit()
                    self.send_json(201, {"ok": True})
                elif self.path == "/api/newsletter":
                    email = str(data.get("email", "")).strip().lower()
                    if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
                        raise ApiError(400, "E-mail inválido.")
                    db.execute("INSERT OR IGNORE INTO subscribers(email) VALUES(?)", (email,))
                    db.commit()
                    self.send_json(201, {"ok": True})
                else:
                    raise ApiError(404, "Rota não encontrada.")
        except ApiError as exc:
            self.send_json(exc.status, {"error": exc.message})
        except (sqlite3.Error, OSError) as exc:
            print(f"Request error: {exc}")
            self.send_json(500, {"error": "Erro interno. Tente novamente."})

    def login_response(self, db: sqlite3.Connection, user_id: int) -> None:
        token = secrets.token_urlsafe(32)
        digest = hashlib.sha256(token.encode()).hexdigest()
        expires = (datetime.now(timezone.utc) + timedelta(days=SESSION_DAYS)).isoformat()
        db.execute("INSERT INTO sessions(token_hash,user_id,expires_at) VALUES(?,?,?)", (digest, user_id, expires))
        db.commit()
        user = db.execute("SELECT name,email,role FROM users WHERE id=?", (user_id,)).fetchone()
        secure = "; Secure" if os.environ.get("APP_SECURE_COOKIE") == "1" else ""
        self.send_json(200, {"user": dict(user)}, {"Set-Cookie": f"{COOKIE_NAME}={token}; Path=/; HttpOnly; SameSite=Lax; Max-Age={SESSION_DAYS * 86400}{secure}"})

    def do_PATCH(self) -> None:
        try:
            data = self.read_json()
            with transaction() as db:
                expire_unpaid_orders(db)
                self.require_user(db, admin=True)
                if self.path.startswith("/api/admin/orders/"):
                    number = unquote(self.path.rsplit("/", 1)[-1])
                    status = str(data.get("status", ""))
                    if status not in ORDER_STATUSES:
                        raise ApiError(400, "Status inválido.")
                    order = db.execute("SELECT * FROM orders WHERE number=?", (number,)).fetchone()
                    if not order:
                        raise ApiError(404, "Pedido não encontrado.")
                    if status == "Cancelado" and order["inventory_reserved"]:
                        for item in json.loads(order["data_json"])["items"]:
                            db.execute("UPDATE products SET stock=stock+? WHERE id=?", (item["qty"], item["id"]))
                        db.execute("UPDATE orders SET status=?,inventory_reserved=0 WHERE number=?", (status, number))
                    elif status not in {"Cancelado", "Aguardando pagamento"} and not order["inventory_reserved"]:
                        for item in json.loads(order["data_json"])["items"]:
                            cursor = db.execute("UPDATE products SET stock=stock-? WHERE id=? AND stock>=?", (item["qty"], item["id"], item["qty"]))
                            if not cursor.rowcount:
                                raise ApiError(409, "Estoque insuficiente para reabrir este pedido.")
                        db.execute("UPDATE orders SET status=?,inventory_reserved=1 WHERE number=?", (status, number))
                    else:
                        db.execute("UPDATE orders SET status=? WHERE number=?", (status, number))
                    db.commit()
                    self.send_json(200, {"ok": True})
                elif self.path.startswith("/api/admin/products/"):
                    try:
                        product_id = int(self.path.rsplit("/", 1)[-1])
                    except ValueError as exc:
                        raise ApiError(400, "Produto inválido.") from exc
                    product = db.execute("SELECT stock,price_cents,data_json FROM products WHERE id=?", (product_id,)).fetchone()
                    if not product:
                        raise ApiError(404, "Produto não encontrado.")
                    stock, price_cents = product["stock"], product["price_cents"]
                    if "stock" in data:
                        try:
                            stock = int(data["stock"])
                        except (ValueError, TypeError) as exc:
                            raise ApiError(400, "Estoque inválido.") from exc
                        if not 0 <= stock <= 100000:
                            raise ApiError(400, "Estoque fora do limite permitido.")
                    if "price" in data:
                        try:
                            price = float(data["price"])
                        except (ValueError, TypeError) as exc:
                            raise ApiError(400, "Preço inválido.") from exc
                        if not math.isfinite(price) or not 0.01 <= price <= 100000:
                            raise ApiError(400, "Preço deve ficar entre R$ 0,01 e R$ 100.000,00 por m².")
                        price_cents = round(price * 100)
                    if "stock" not in data and "price" not in data:
                        raise ApiError(400, "Informe preço ou estoque para atualizar.")
                    product_data = json.loads(product["data_json"])
                    product_data["price"] = price_cents / 100
                    db.execute("UPDATE products SET stock=?,price_cents=?,data_json=? WHERE id=?", (stock, price_cents, json.dumps(product_data, ensure_ascii=False), product_id))
                    db.commit()
                    self.send_json(200, {"ok": True})
                else:
                    raise ApiError(404, "Rota não encontrada.")
        except ApiError as exc:
            self.send_json(exc.status, {"error": exc.message})
        except sqlite3.Error as exc:
            print(f"Request error: {exc}")
            self.send_json(500, {"error": "Erro interno. Tente novamente."})

    def do_DELETE(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path != "/api/me":
            self.send_json(404, {"error": "Rota não encontrada."})
            return
        try:
            with transaction() as db:
                user = self.require_user(db)
                if user["role"] == "admin":
                    raise ApiError(409, "Crie outro administrador antes de excluir esta conta administrativa.")
                orders = db.execute("SELECT id,number,data_json,payment_status,status,inventory_reserved FROM orders WHERE user_id=?", (user["id"],)).fetchall()
                for order in orders:
                    data = json.loads(order["data_json"])
                    data["customer"] = {
                        "name": "Dados removidos", "email": "", "phone": "", "cep": "",
                        "street": "", "number": "", "complement": "", "neighborhood": "",
                        "city": "", "uf": "", "note": "",
                    }
                    is_unpaid = order["status"] == "Aguardando pagamento" and order["payment_status"] in {"pending", "rejected", "cancelled"}
                    if is_unpaid and order["inventory_reserved"]:
                        for item in json.loads(order["data_json"])["items"]:
                            db.execute("UPDATE products SET stock=stock+? WHERE id=?", (item["qty"], item["id"]))
                    db.execute(
                        "UPDATE orders SET user_id=NULL,email=?,data_json=?,checkout_url='',status=CASE WHEN ? THEN 'Cancelado' ELSE status END,inventory_reserved=CASE WHEN ? THEN 0 ELSE inventory_reserved END WHERE id=?",
                        (f"removido+{order['number']}@invalid.local", json.dumps(data, ensure_ascii=False), int(is_unpaid), int(is_unpaid), order["id"]),
                    )
                db.execute("DELETE FROM contacts WHERE email=? COLLATE NOCASE", (user["email"],))
                db.execute("DELETE FROM subscribers WHERE email=? COLLATE NOCASE", (user["email"],))
                db.execute("DELETE FROM users WHERE id=?", (user["id"],))
                db.commit()
            secure = "; Secure" if os.environ.get("APP_SECURE_COOKIE") == "1" else ""
            self.send_json(200, {"ok": True}, {"Set-Cookie": f"{COOKIE_NAME}=; Path=/; HttpOnly; SameSite=Lax; Max-Age=0{secure}"})
        except ApiError as exc:
            self.send_json(exc.status, {"error": exc.message})
        except (sqlite3.Error, OSError, ValueError) as exc:
            print(f"Account deletion failed: {type(exc).__name__}")
            self.send_json(500, {"error": "Não foi possível excluir a conta."})

    def serve_static(self, request_path: str) -> None:
        relative = unquote(request_path).lstrip("/") or "index.html"
        static_root = ROOT / "dist"
        if not static_root.is_dir():
            self.send_error(HTTPStatus.NOT_FOUND, "Execute npm run build antes de servir a interface.")
            return
        target = (static_root / relative).resolve()
        if not target.is_relative_to(static_root) or any(part.startswith(".") for part in target.relative_to(static_root).parts):
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        if target.is_dir():
            target = target / "index.html"
        if not target.is_file():
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        body = target.read_bytes()
        content_type = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
        if content_type.startswith("text/") or content_type in {"application/javascript", "application/json"}:
            content_type += "; charset=utf-8"
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        if target.name == "index.html":
            cache_control = "no-cache"
        elif re.search(r"-[A-Za-z0-9_-]{8,}\.", target.name):
            cache_control = "public, max-age=31536000, immutable"
        else:
            cache_control = "public, max-age=3600"
        self.send_header("Cache-Control", cache_control)
        self.end_headers()
        self.wfile.write(body)


def main() -> None:
    initialize()
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8000"))
    print(f"Angélica Casa listening on http://{host}:{port}")
    StoreHTTPServer((host, port), StoreHandler).serve_forever()


if __name__ == "__main__":
    main()
