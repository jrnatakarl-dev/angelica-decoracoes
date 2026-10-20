"""Administrative commands for the local store."""
import getpass
import re
import sys

from server.db import initialize, transaction
from server.app import hash_password


def create_admin(email: str) -> None:
    name = input("Nome do administrador: ").strip()
    password = getpass.getpass("Senha (mínimo 10 caracteres): ")
    if len(name) < 2 or len(password) < 10 or not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
        raise SystemExit("Nome, e-mail ou senha inválido.")
    initialize()
    try:
        with transaction() as db:
            db.execute("INSERT INTO users(name,email,password_hash,role) VALUES(?,?,?,'admin')", (name, email.lower(), hash_password(password)))
    except Exception as exc:
        raise SystemExit(f"Não foi possível criar o administrador: {exc}") from exc
    print("Administrador criado.")


if __name__ == "__main__":
    if len(sys.argv) != 3 or sys.argv[1] != "create-admin":
        raise SystemExit("Uso: python3 -m server.manage create-admin email@dominio.com")
    create_admin(sys.argv[2])
