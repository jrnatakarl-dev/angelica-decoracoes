"""Create or restore a consistent SQLite database backup."""
from __future__ import annotations

import argparse
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from server.db import DATA_DIR, DB_PATH


def backup(destination: Path) -> None:
    if not DB_PATH.is_file():
        raise SystemExit(f"Banco não encontrado: {DB_PATH}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    source = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    target = sqlite3.connect(destination)
    try:
        source.backup(target)
        result = target.execute("PRAGMA integrity_check").fetchone()[0]
        if result != "ok":
            raise RuntimeError(f"A cópia não passou na verificação: {result}")
    finally:
        target.close()
        source.close()
    os.chmod(destination, 0o600)


def restore(source_path: Path) -> None:
    if not source_path.is_file():
        raise SystemExit(f"Cópia não encontrada: {source_path}")
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    source = sqlite3.connect(f"file:{source_path.resolve()}?mode=ro", uri=True)
    target = sqlite3.connect(DB_PATH)
    try:
        source.backup(target)
        result = target.execute("PRAGMA integrity_check").fetchone()[0]
        if result != "ok":
            raise RuntimeError(f"A restauração não passou na verificação: {result}")
    finally:
        target.close()
        source.close()
    os.chmod(DB_PATH, 0o600)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", nargs="?", choices=("backup", "restore"), default="backup")
    parser.add_argument("path", nargs="?", type=Path)
    args = parser.parse_args()
    if args.action == "restore":
        if args.path is None:
            parser.error("informe o caminho da cópia para restaurar")
        restore(args.path)
        print(f"Banco restaurado de {args.path}")
        return
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    destination = args.path or DATA_DIR / "backups" / f"store-{stamp}.sqlite3"
    backup(destination)
    print(f"Cópia verificada em {destination}")


if __name__ == "__main__":
    main()
