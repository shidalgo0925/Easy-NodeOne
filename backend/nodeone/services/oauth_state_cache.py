"""Caché Authlib para el ``state`` OAuth2 (OpenID) compartida entre procesos.

Gunicorn usa varios workers; la sesión Flask va en cookie firmada, pero si el navegador
no la reenvía al volver de Google (SameSite, partición, etc.), Authlib lanza
``MismatchingStateError``. Con ``OAuth(..., cache=...)`` el state vive en SQLite bajo
``instance/``, visible por todos los workers.
"""

from __future__ import annotations

import json
import sqlite3
import time
from typing import Any, Optional


class SqliteOAuthStateCache:
    """Implementación mínima compatible con Authlib (get / set / delete)."""

    def __init__(self, path: str) -> None:
        self.path = path
        with sqlite3.connect(self.path, timeout=30.0) as conn:
            conn.execute('PRAGMA journal_mode=WAL')
            conn.execute('PRAGMA busy_timeout=5000')
            conn.execute(
                '''CREATE TABLE IF NOT EXISTS authlib_oauth_state (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    exp REAL NOT NULL
                )'''
            )
            conn.commit()

    def get(self, key: str) -> Optional[str]:
        now = time.time()
        with sqlite3.connect(self.path, timeout=30.0) as conn:
            conn.execute('PRAGMA busy_timeout=5000')
            row = conn.execute(
                'SELECT value, exp FROM authlib_oauth_state WHERE key = ?', (key,)
            ).fetchone()
            if not row:
                return None
            value, exp = row[0], float(row[1])
            if exp < now:
                conn.execute('DELETE FROM authlib_oauth_state WHERE key = ?', (key,))
                conn.commit()
                return None
            return value

    def set(self, key: str, value: Any, timeout: Optional[int] = None) -> None:
        ttl = int(timeout) if timeout is not None else 3600
        exp = time.time() + max(ttl, 60)
        if not isinstance(value, str):
            value = json.dumps(value)
        with sqlite3.connect(self.path, timeout=30.0) as conn:
            conn.execute('PRAGMA busy_timeout=5000')
            conn.execute(
                'INSERT OR REPLACE INTO authlib_oauth_state (key, value, exp) VALUES (?, ?, ?)',
                (key, value, exp),
            )
            conn.commit()

    def delete(self, key: str) -> None:
        with sqlite3.connect(self.path, timeout=30.0) as conn:
            conn.execute('PRAGMA busy_timeout=5000')
            conn.execute('DELETE FROM authlib_oauth_state WHERE key = ?', (key,))
            conn.commit()
