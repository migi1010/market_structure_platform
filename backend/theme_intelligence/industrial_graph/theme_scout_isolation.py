from __future__ import annotations

import hashlib
import json
import sqlite3
from typing import Any

from theme_intelligence.storage.theme_repository import ThemeRepository


DOWNSTREAM_PREFIXES = ("graph_", "controller_", "opportunity_", "decision_")


def _fingerprint_connection(conn: sqlite3.Connection) -> dict[str, dict[str, Any]]:
    tables = [
        str(row["name"])
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
        if str(row["name"]).startswith(DOWNSTREAM_PREFIXES)
    ]
    result: dict[str, dict[str, Any]] = {}
    for table in tables:
        columns = [
            str(row["name"]) for row in conn.execute(f'PRAGMA table_info("{table}")')
        ]
        rows = [
            dict(zip(columns, tuple(row)))
            for row in conn.execute(f'SELECT * FROM "{table}" ORDER BY rowid').fetchall()
        ]
        encoded = json.dumps(
            rows, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str
        ).encode("utf-8")
        result[table] = {
            "row_count": len(rows),
            "checksum": hashlib.sha256(encoded).hexdigest(),
        }
    return result


def downstream_fingerprint(repository: ThemeRepository) -> dict[str, dict[str, Any]]:
    repository.initialize()
    with repository._connect() as conn:
        return _fingerprint_connection(conn)


def connection_downstream_fingerprint(
    conn: sqlite3.Connection,
) -> dict[str, dict[str, Any]]:
    return _fingerprint_connection(conn)


def verify_connection_isolation(
    conn: sqlite3.Connection, before: dict[str, dict[str, Any]]
) -> None:
    after = connection_downstream_fingerprint(conn)
    if after != before:
        raise ValueError("downstream isolation mismatch")

