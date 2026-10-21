"""SQLite schema and connection helpers."""
from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = Path(os.environ.get("APP_DATA_DIR", ROOT / "data")).resolve()
DB_PATH = DATA_DIR / "store.sqlite3"
CATALOG_PATH = ROOT / "public" / "assets" / "data" / "catalog.json"

SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS products (
  id INTEGER PRIMARY KEY,
  category TEXT NOT NULL,
  price_cents INTEGER NOT NULL CHECK (price_cents >= 0),
  stock INTEGER NOT NULL CHECK (stock >= 0),
  data_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY,
  name TEXT NOT NULL,
  email TEXT NOT NULL UNIQUE COLLATE NOCASE,
  password_hash TEXT NOT NULL,
  role TEXT NOT NULL DEFAULT 'customer' CHECK (role IN ('customer', 'admin')),
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS sessions (
  token_hash TEXT PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  expires_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS orders (
  id INTEGER PRIMARY KEY,
  number TEXT NOT NULL UNIQUE,
  user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
  email TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'Aguardando pagamento',
  payment_method TEXT NOT NULL,
  payment_provider TEXT NOT NULL DEFAULT '',
  payment_status TEXT NOT NULL DEFAULT 'pending',
  payment_id TEXT NOT NULL DEFAULT '',
  preference_id TEXT NOT NULL DEFAULT '',
  checkout_url TEXT NOT NULL DEFAULT '',
  shipping_id TEXT NOT NULL DEFAULT '',
  shipping_stage TEXT NOT NULL DEFAULT '',
  shipping_label_url TEXT NOT NULL DEFAULT '',
  subtotal_cents INTEGER NOT NULL,
  discount_cents INTEGER NOT NULL DEFAULT 0,
  shipping_cents INTEGER NOT NULL,
  total_cents INTEGER NOT NULL,
  inventory_reserved INTEGER NOT NULL DEFAULT 0 CHECK (inventory_reserved IN (0, 1)),
  data_json TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS orders_user_created ON orders(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS orders_email_created ON orders(email, created_at DESC);
CREATE INDEX IF NOT EXISTS sessions_expires ON sessions(expires_at);
CREATE TABLE IF NOT EXISTS contacts (
  id INTEGER PRIMARY KEY,
  name TEXT NOT NULL,
  email TEXT NOT NULL,
  interest TEXT NOT NULL,
  message TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS subscribers (
  id INTEGER PRIMARY KEY,
  email TEXT NOT NULL UNIQUE COLLATE NOCASE,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""


def connect() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.umask(0o077)
    db = sqlite3.connect(DB_PATH, timeout=10, cached_statements=128)
    os.chmod(DB_PATH, 0o600)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    db.execute("PRAGMA busy_timeout = 10000")
    return db


@contextmanager
def transaction():
    db = connect()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def initialize() -> None:
    with transaction() as db:
        # WAL is persistent for the database. Setting it on every HTTP request
        # adds unnecessary locking and disk work.
        db.execute("PRAGMA journal_mode = WAL")
        db.executescript(SCHEMA)
        order_columns = {row["name"] for row in db.execute("PRAGMA table_info(orders)")}
        if "inventory_reserved" not in order_columns:
            db.execute("ALTER TABLE orders ADD COLUMN inventory_reserved INTEGER NOT NULL DEFAULT 0 CHECK (inventory_reserved IN (0, 1))")
        payment_columns = {
            "payment_provider": "TEXT NOT NULL DEFAULT ''",
            "payment_status": "TEXT NOT NULL DEFAULT 'pending'",
            "payment_id": "TEXT NOT NULL DEFAULT ''",
            "preference_id": "TEXT NOT NULL DEFAULT ''",
            "checkout_url": "TEXT NOT NULL DEFAULT ''",
            "shipping_id": "TEXT NOT NULL DEFAULT ''",
            "shipping_stage": "TEXT NOT NULL DEFAULT ''",
            "shipping_label_url": "TEXT NOT NULL DEFAULT ''",
        }
        for column, definition in payment_columns.items():
            if column not in order_columns:
                db.execute(f"ALTER TABLE orders ADD COLUMN {column} {definition}")
        db.execute("DELETE FROM sessions WHERE expires_at <= ?", (datetime.now(timezone.utc).isoformat(),))
        catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
        for product in catalog["products"]:
            current = db.execute("SELECT id FROM products WHERE id=?", (product["id"],)).fetchone()
            clean = dict(product)
            if current:
                db.execute(
                    "UPDATE products SET category=?, data_json=? WHERE id=?",
                    (product["category"], json.dumps(clean, ensure_ascii=False), product["id"]),
                )
            else:
                clean = dict(product)
                db.execute(
                    "INSERT INTO products(id, category, price_cents, stock, data_json) VALUES (?, ?, ?, ?, ?)",
                    (product["id"], product["category"], round(product["price"] * 100), product["stock"], json.dumps(clean, ensure_ascii=False)),
                )
