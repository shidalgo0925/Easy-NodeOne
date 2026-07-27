"""DDL idempotente — password_reset_token."""

from __future__ import annotations

from sqlalchemy import inspect, text


def _exec(engine, ddl: str, printfn, label: str) -> None:
    with engine.begin() as conn:
        conn.execute(text(ddl))
    if printfn:
        printfn(label)


def ensure_password_reset_schema(db, engine, printfn=None) -> None:
    insp = inspect(engine)
    dialect = engine.dialect.name
    tables = set(insp.get_table_names())
    if 'password_reset_token' in tables:
        return

    if dialect == 'postgresql':
        ddl = """
        CREATE TABLE IF NOT EXISTS password_reset_token (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
            token_hash VARCHAR(64) NOT NULL,
            expires_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
            used_at TIMESTAMP WITHOUT TIME ZONE,
            created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (NOW() AT TIME ZONE 'utc'),
            ip VARCHAR(64),
            user_agent VARCHAR(500),
            CONSTRAINT uq_password_reset_token_hash UNIQUE (token_hash)
        );
        CREATE INDEX IF NOT EXISTS ix_password_reset_token_user ON password_reset_token (user_id);
        CREATE INDEX IF NOT EXISTS ix_password_reset_token_expires ON password_reset_token (expires_at);
        """
    else:
        ddl = """
        CREATE TABLE IF NOT EXISTS password_reset_token (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            token_hash VARCHAR(64) NOT NULL UNIQUE,
            expires_at DATETIME NOT NULL,
            used_at DATETIME,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            ip VARCHAR(64),
            user_agent VARCHAR(500)
        );
        CREATE INDEX IF NOT EXISTS ix_password_reset_token_user ON password_reset_token (user_id);
        CREATE INDEX IF NOT EXISTS ix_password_reset_token_expires ON password_reset_token (expires_at);
        """
    _exec(engine, ddl, printfn, 'password_reset_token')
