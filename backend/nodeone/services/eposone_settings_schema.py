"""DDL idempotente — configuración EPosOne."""

from __future__ import annotations

from sqlalchemy import inspect, text


def ensure_eposone_settings_schema(db, engine, printfn=None) -> None:
    insp = inspect(engine)
    dialect = engine.dialect.name
    tables = insp.get_table_names()

    if 'eposone_settings' not in tables:
        if dialect == 'postgresql':
            ddl = """
            CREATE TABLE IF NOT EXISTS eposone_settings (
                id SERIAL PRIMARY KEY,
                organization_id INTEGER NOT NULL UNIQUE REFERENCES saas_organization(id) ON DELETE CASCADE,
                default_currency VARCHAR(3) NOT NULL DEFAULT 'USD',
                kds_auto_enqueue BOOLEAN NOT NULL DEFAULT TRUE,
                delivery_auto_create BOOLEAN NOT NULL DEFAULT TRUE,
                fiscal_on_payment BOOLEAN NOT NULL DEFAULT FALSE,
                supervisor_approval_required BOOLEAN NOT NULL DEFAULT TRUE,
                provisioning_code VARCHAR(64),
                updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (NOW() AT TIME ZONE 'utc')
            );
            CREATE INDEX IF NOT EXISTS ix_eposone_settings_org ON eposone_settings (organization_id);
            """
        else:
            ddl = """
            CREATE TABLE IF NOT EXISTS eposone_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                organization_id INTEGER NOT NULL UNIQUE,
                default_currency VARCHAR(3) NOT NULL DEFAULT 'USD',
                kds_auto_enqueue INTEGER NOT NULL DEFAULT 1,
                delivery_auto_create INTEGER NOT NULL DEFAULT 1,
                fiscal_on_payment INTEGER NOT NULL DEFAULT 0,
                supervisor_approval_required INTEGER NOT NULL DEFAULT 1,
                provisioning_code VARCHAR(64),
                updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            """
        with engine.begin() as conn:
            for stmt in ddl.strip().split(';'):
                s = stmt.strip()
                if s:
                    conn.execute(text(s))
        if printfn:
            printfn('eposone_settings: tabla creada')
        return

    cols = {c['name'] for c in insp.get_columns('eposone_settings')}
    if 'provisioning_code' not in cols:
        with engine.begin() as conn:
            if dialect == 'postgresql':
                conn.execute(
                    text(
                        'ALTER TABLE eposone_settings '
                        'ADD COLUMN IF NOT EXISTS provisioning_code VARCHAR(64)'
                    )
                )
            else:
                conn.execute(text('ALTER TABLE eposone_settings ADD COLUMN provisioning_code VARCHAR(64)'))
        if printfn:
            printfn('eposone_settings: columna provisioning_code añadida')
