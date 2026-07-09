"""DDL idempotente — modelo maestro Core (Etapa 10b)."""

from __future__ import annotations

from sqlalchemy import inspect, text


def _exec(engine, ddl: str, printfn, label: str) -> None:
    with engine.begin() as conn:
        conn.execute(text(ddl))
    if printfn:
        printfn(label)


def ensure_core_master_schema(db, engine, printfn=None) -> None:
    insp = inspect(engine)
    dialect = engine.dialect.name
    tables = set(insp.get_table_names())

    if 'core_org_unit' not in tables:
        if dialect == 'postgresql':
            ddl = """
            CREATE TABLE IF NOT EXISTS core_org_unit (
                id SERIAL PRIMARY KEY,
                organization_id INTEGER NOT NULL REFERENCES saas_organization(id) ON DELETE CASCADE,
                parent_id INTEGER REFERENCES core_org_unit(id) ON DELETE SET NULL,
                unit_ref VARCHAR(64) NOT NULL,
                name VARCHAR(200) NOT NULL,
                unit_type VARCHAR(32) NOT NULL DEFAULT 'branch',
                status VARCHAR(32) NOT NULL DEFAULT 'active',
                notes TEXT,
                created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (NOW() AT TIME ZONE 'utc'),
                updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (NOW() AT TIME ZONE 'utc'),
                CONSTRAINT uq_core_org_unit_ref UNIQUE (organization_id, unit_ref)
            );
            CREATE INDEX IF NOT EXISTS ix_core_org_unit_org ON core_org_unit (organization_id);
            CREATE INDEX IF NOT EXISTS ix_core_org_unit_type ON core_org_unit (organization_id, unit_type);
            """
        else:
            ddl = """
            CREATE TABLE IF NOT EXISTS core_org_unit (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                organization_id INTEGER NOT NULL,
                parent_id INTEGER,
                unit_ref VARCHAR(64) NOT NULL,
                name VARCHAR(200) NOT NULL,
                unit_type VARCHAR(32) NOT NULL DEFAULT 'branch',
                status VARCHAR(32) NOT NULL DEFAULT 'active',
                notes TEXT,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (organization_id, unit_ref)
            );
            CREATE INDEX IF NOT EXISTS ix_core_org_unit_org ON core_org_unit (organization_id);
            """
        _exec(engine, ddl, printfn, 'core_org_unit')

    if 'core_address' not in tables:
        if dialect == 'postgresql':
            ddl = """
            CREATE TABLE IF NOT EXISTS core_address (
                id SERIAL PRIMARY KEY,
                organization_id INTEGER NOT NULL REFERENCES saas_organization(id) ON DELETE CASCADE,
                owner_type VARCHAR(32) NOT NULL,
                owner_id INTEGER NOT NULL,
                kind VARCHAR(32) NOT NULL DEFAULT 'fiscal',
                line1 VARCHAR(300),
                line2 VARCHAR(300),
                city VARCHAR(120),
                state VARCHAR(120),
                postal_code VARCHAR(32),
                country VARCHAR(8),
                created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (NOW() AT TIME ZONE 'utc')
            );
            CREATE INDEX IF NOT EXISTS ix_core_address_owner
                ON core_address (organization_id, owner_type, owner_id);
            """
        else:
            ddl = """
            CREATE TABLE IF NOT EXISTS core_address (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                organization_id INTEGER NOT NULL,
                owner_type VARCHAR(32) NOT NULL,
                owner_id INTEGER NOT NULL,
                kind VARCHAR(32) NOT NULL DEFAULT 'fiscal',
                line1 VARCHAR(300),
                line2 VARCHAR(300),
                city VARCHAR(120),
                state VARCHAR(120),
                postal_code VARCHAR(32),
                country VARCHAR(8),
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS ix_core_address_owner
                ON core_address (organization_id, owner_type, owner_id);
            """
        _exec(engine, ddl, printfn, 'core_address')

    if 'core_attachment' not in tables:
        if dialect == 'postgresql':
            ddl = """
            CREATE TABLE IF NOT EXISTS core_attachment (
                id SERIAL PRIMARY KEY,
                organization_id INTEGER NOT NULL REFERENCES saas_organization(id) ON DELETE CASCADE,
                mime_type VARCHAR(128),
                storage_path VARCHAR(500) NOT NULL,
                checksum VARCHAR(128),
                uploaded_by_user_id INTEGER REFERENCES "user"(id) ON DELETE SET NULL,
                created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (NOW() AT TIME ZONE 'utc')
            );
            CREATE INDEX IF NOT EXISTS ix_core_attachment_org ON core_attachment (organization_id);
            """
        else:
            ddl = """
            CREATE TABLE IF NOT EXISTS core_attachment (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                organization_id INTEGER NOT NULL,
                mime_type VARCHAR(128),
                storage_path VARCHAR(500) NOT NULL,
                checksum VARCHAR(128),
                uploaded_by_user_id INTEGER,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS ix_core_attachment_org ON core_attachment (organization_id);
            """
        _exec(engine, ddl, printfn, 'core_attachment')
