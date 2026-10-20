"""Small same-origin JSON API and static server backed by SQLite."""
from __future__ import annotations

import hashlib
import hmac
import json
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
from urllib.parse import unquote, urlparse

from server.db import CATALOG_PATH, ROOT, initialize, transaction

COOKIE_NAME = "ac_session"
SESSION_DAYS = 14
PBKDF2_ROUNDS = 310_000
MAX_BODY = 1_000_000
ORDER_STATUSES = {"Aguardando pagamento", "Pago", "Em fabricação", "Enviado", "Entregue", "Cancelado"}


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


def public_order(row: sqlite3.Row) -> dict:
    data = json.loads(row["data_json"])
    data.update({
        "number": row["number"], "status": row["status"], "payment": row["payment_method"],
        "subtotal": row["subtotal_cents"] / 100, "discount": row["discount_cents"] / 100,
        "shippingPrice": row["shipping_cents"] / 100, "total": row["total_cents"] / 100,
        "date": row["created_at"],
    })
    return data


class StoreHandler(BaseHTTPRequestHandler):
    server_version = "AngelicaCasa/1.0"

    def log_message(self, fmt: str, *args) -> None:
        if os.environ.get("APP_ACCESS_LOG") == "1":
            super().log_message(fmt, *args)

    def end_headers(self) -> None:
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "strict-origin-when-cross-origin")
        self.send_header("X-Frame-Options", "DENY")
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
                    self.send_json(200, {"products": products, "categories": catalog["categories"], "faqs": catalog["faqs"]})
                elif parsed.path == "/api/me":
                    user = self.session_user(db)
                    self.send_json(200, {"user": {"name": user["name"], "email": user["email"], "role": user["role"]} if user else None})
                elif parsed.path == "/api/orders":
                    user = self.require_user(db)
                    rows = db.execute("SELECT * FROM orders WHERE user_id=? ORDER BY id DESC", (user["id"],)).fetchall()
                    self.send_json(200, {"orders": [public_order(row) for row in rows]})
                elif parsed.path == "/api/admin/orders":
                    self.require_user(db, admin=True)
                    rows = db.execute("SELECT * FROM orders ORDER BY id DESC").fetchall()
                    self.send_json(200, {"orders": [public_order(row) for row in rows]})
                elif parsed.path == "/api/admin/products":
                    self.require_user(db, admin=True)
                    self.send_json(200, {"products": [dict(id=r["id"], stock=r["stock"]) for r in db.execute("SELECT id,stock FROM products ORDER BY id")]})
                elif parsed.path.startswith("/api/orders/track/"):
                    number = unquote(parsed.path.rsplit("/", 1)[-1]).strip()
                    row = db.execute("SELECT number,status,created_at FROM orders WHERE number=?", (number,)).fetchone()
                    if not row:
                        raise ApiError(404, "Pedido não encontrado.")
                    self.send_json(200, {"number": row["number"], "status": row["status"], "date": row["created_at"]})
                elif parsed.path.startswith("/api/"):
                    raise ApiError(404, "Rota não encontrada.")
        except ApiError as exc:
            self.send_json(exc.status, {"error": exc.message})
        except (sqlite3.Error, OSError) as exc:
            print(f"Request error: {exc}")
            self.send_json(500, {"error": "Erro interno. Tente novamente."})

    def do_POST(self) -> None:
        try:
            data = self.read_json()
            with transaction() as db:
                if self.path == "/api/auth/register":
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
                    self.send_json(200, {"ok": True}, {"Set-Cookie": f"{COOKIE_NAME}=; Path=/; HttpOnly; SameSite=Lax; Max-Age=0"})
                elif self.path == "/api/orders":
                    user = self.session_user(db)
                    customer = data.get("customer") or {}
                    if not isinstance(customer, dict):
                        raise ApiError(400, "Dados do cliente inválidos.")
                    email = user["email"] if user else str(customer.get("email", "")).strip().lower()
                    name = user["name"] if user else str(customer.get("name", "")).strip()
                    cep = re.sub(r"\D", "", str(customer.get("cep", "")))
                    if len(name) < 2 or not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email) or len(cep) != 8 or not customer.get("street") or not customer.get("city"):
                        raise ApiError(400, "Informe nome, e-mail e endereço completo.")
                    items = data.get("items")
                    if not isinstance(items, list) or not items or len(items) > 30:
                        raise ApiError(400, "O pedido precisa ter entre 1 e 30 itens.")
                    payment = data.get("payment")
                    if not isinstance(payment, str) or payment not in {"pix", "card", "boleto"}:
                        raise ApiError(400, "Forma de pagamento inválida.")
                    subtotal, safe_items = 0, []
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
                        safe_items.append({"key": secrets.token_hex(8), "id": product_id, "name": info["name"], "image": info["image"], "color": str(item.get("color", ""))[:80], "install": "parede" if item.get("install") == "parede" else "vão", "width": width, "height": height, "price": line_cents / 100 / quantity, "qty": quantity})
                    coupon = str(data.get("coupon", "")).strip().upper()
                    discount = 0
                    if coupon == "CASA10":
                        discount = round(subtotal * 0.10)
                    elif coupon == "LUZ15" and subtotal >= 80000:
                        discount = round(subtotal * 0.15)
                    elif coupon not in {"", "FRETE0", "LUZ15"}:
                        raise ApiError(400, "Cupom inválido.")
                    if payment == "pix":
                        discount += round((subtotal - discount) * 0.05)
                    area_total = sum(i["width"] * i["height"] / 10000 * i["qty"] for i in safe_items)
                    shipping_mode = data.get("shipping", "pac")
                    if shipping_mode == "retirada":
                        shipping = 0
                    else:
                        base = min(18900, round(3900 + area_total * 1800))
                        shipping = round(base * 1.65) if shipping_mode == "sedex" else base
                    if coupon == "FRETE0":
                        shipping = 0
                    number = "AC-" + secrets.token_hex(6).upper()
                    order_data = {"items": safe_items, "customer": {"name": name, "email": email, "phone": re.sub(r"\D", "", str(customer.get("phone", "")))[:20], "cep": cep, "street": str(customer.get("street", ""))[:180], "number": str(customer.get("number", ""))[:30], "complement": str(customer.get("complement", ""))[:100], "neighborhood": str(customer.get("neighborhood", ""))[:100], "city": str(customer.get("city", ""))[:100], "uf": str(customer.get("uf", ""))[:2], "note": str(customer.get("note", ""))[:500]}, "shipping": shipping_mode}
                    total = max(0, subtotal - discount + shipping)
                    db.execute("INSERT INTO orders(number,user_id,email,payment_method,subtotal_cents,discount_cents,shipping_cents,total_cents,data_json) VALUES(?,?,?,?,?,?,?,?,?)", (number, user["id"] if user else None, email, payment, subtotal, discount, shipping, total, json.dumps(order_data, ensure_ascii=False)))
                    db.commit()
                    order = db.execute("SELECT * FROM orders WHERE number=?", (number,)).fetchone()
                    self.send_json(201, {"order": public_order(order)})
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
                        product_id, stock = int(self.path.rsplit("/", 1)[-1]), int(data.get("stock"))
                    except (ValueError, TypeError) as exc:
                        raise ApiError(400, "Estoque inválido.") from exc
                    if not 0 <= stock <= 100000:
                        raise ApiError(400, "Estoque fora do limite permitido.")
                    cursor = db.execute("UPDATE products SET stock=? WHERE id=?", (stock, product_id))
                    if not cursor.rowcount:
                        raise ApiError(404, "Produto não encontrado.")
                    db.commit()
                    self.send_json(200, {"ok": True})
                else:
                    raise ApiError(404, "Rota não encontrada.")
        except ApiError as exc:
            self.send_json(exc.status, {"error": exc.message})
        except sqlite3.Error as exc:
            print(f"Request error: {exc}")
            self.send_json(500, {"error": "Erro interno. Tente novamente."})

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
    ThreadingHTTPServer((host, port), StoreHandler).serve_forever()


if __name__ == "__main__":
    main()
