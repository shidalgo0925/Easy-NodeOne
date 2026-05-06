"""Almacena la vista previa del import de participantes fuera de la cookie de sesión.

Gunicorn con cookie-session firma todo el payload JSON del Excel; nginx rechaza la respuesta
con «upstream sent too big header». Esta tabla SQLite (compartida entre workers) guarda el JSON;
la sesión solo lleva un token corto.
"""

from __future__ import annotations

import json
import os
import secrets
import sqlite3
import time
from typing import Any

_BACKEND_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
_INSTANCE_ROOT = os.path.join(os.path.dirname(_BACKEND_ROOT), 'instance')
_DEFAULT_DB_PATH = os.path.join(_INSTANCE_ROOT, 'participant_import_preview.sqlite3')

TTL_SECONDS_DEFAULT = 3600


def _db_path() -> str:
    p = (os.environ.get('PARTICIPANT_IMPORT_PREVIEW_SQLITE_PATH') or '').strip()
    return p if p else _DEFAULT_DB_PATH


_store_singleton: ParticipantImportPreviewStore | None = None


def get_participant_import_preview_store() -> 'ParticipantImportPreviewStore':
    global _store_singleton
    if _store_singleton is None:
        os.makedirs(os.path.dirname(_db_path()), exist_ok=True)
        _store_singleton = ParticipantImportPreviewStore(_db_path())
    return _store_singleton


class ParticipantImportPreviewStore:
    def __init__(self, path: str) -> None:
        self.path = path
        with sqlite3.connect(self.path, timeout=30.0) as conn:
            conn.execute('PRAGMA journal_mode=WAL')
            conn.execute('PRAGMA busy_timeout=5000')
            conn.execute(
                '''CREATE TABLE IF NOT EXISTS participant_import_preview (
                    token TEXT PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    event_id INTEGER NOT NULL,
                    payload TEXT NOT NULL,
                    exp REAL NOT NULL
                )'''
            )
            conn.commit()

    def put(
        self,
        user_id: int,
        event_id: int,
        payload: list[dict[str, Any]],
        ttl_seconds: int = TTL_SECONDS_DEFAULT,
    ) -> str:
        token = secrets.token_urlsafe(32)
        exp = time.time() + max(int(ttl_seconds), 120)
        blob = json.dumps(payload, separators=(',', ':'))
        with sqlite3.connect(self.path, timeout=30.0) as conn:
            conn.execute('PRAGMA busy_timeout=5000')
            conn.execute(
                '''INSERT INTO participant_import_preview (token, user_id, event_id, payload, exp)
                   VALUES (?, ?, ?, ?, ?)''',
                (token, int(user_id), int(event_id), blob, exp),
            )
            conn.commit()
        return token

    def get(self, token: str, user_id: int, event_id: int) -> list[dict[str, Any]] | None:
        now = time.time()
        with sqlite3.connect(self.path, timeout=30.0) as conn:
            conn.execute('PRAGMA busy_timeout=5000')
            row = conn.execute(
                '''SELECT payload, exp, user_id, event_id FROM participant_import_preview
                   WHERE token = ?''',
                (token,),
            ).fetchone()
            if not row:
                return None
            blob, exp, uid, eid = row[0], float(row[1]), int(row[2]), int(row[3])
            if exp < now:
                conn.execute('DELETE FROM participant_import_preview WHERE token = ?', (token,))
                conn.commit()
                return None
            if uid != int(user_id) or eid != int(event_id):
                return None
            try:
                out = json.loads(blob)
                if isinstance(out, list):
                    return out
            except json.JSONDecodeError:
                pass
            return None

    def delete(self, token: str) -> None:
        if not token:
            return
        with sqlite3.connect(self.path, timeout=30.0) as conn:
            conn.execute('PRAGMA busy_timeout=5000')
            conn.execute('DELETE FROM participant_import_preview WHERE token = ?', (token,))
            conn.commit()

