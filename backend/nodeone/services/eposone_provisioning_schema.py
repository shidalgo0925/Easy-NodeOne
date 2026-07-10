"""DDL — eposone_provisioning_code (Hito EN1-02)."""

from __future__ import annotations

from sqlalchemy import inspect, text


def ensure_eposone_provisioning_schema(db, engine, printfn=None) -> None:
    insp = inspect(engine)
    if 'eposone_provisioning_code' in insp.get_table_names():
        return

    dialect = engine.dialect.name
    if dialect == 'postgresql':
        ddl = """
        CREATE TABLE IF NOT EXISTS eposone_provisioning_code (
            id SERIAL PRIMARY KEY,
            organization_id INTEGER NOT NULL REFERENCES saas_organization(id) ON DELETE CASCADE,
            branch_ref VARCHAR(64) NOT NULL,
            pos_ref VARCHAR(64) NOT NULL,
            register_ref VARCHAR(64) NOT NULL,
            code VARCHAR(64) NOT NULL UNIQUE,
            status VARCHAR(32) NOT NULL DEFAULT 'active',
            label VARCHAR(120),
            created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (NOW() AT TIME ZONE 'utc'),
            updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (NOW() AT TIME ZONE 'utc'),
            last_used_at TIMESTAMP WITHOUT TIME ZONE
        );
        CREATE INDEX IF NOT EXISTS ix_eposone_prov_code ON eposone_provisioning_code (code);
        CREATE INDEX IF NOT EXISTS ix_eposone_prov_org ON eposone_provisioning_code (organization_id);
        CREATE INDEX IF NOT EXISTS ix_eposone_prov_org_register
            ON eposone_provisioning_code (organization_id, register_ref);
        """
    else:
        ddl = """
        CREATE TABLE IF NOT EXISTS eposone_provisioning_code (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            organization_id INTEGER NOT NULL,
            branch_ref VARCHAR(64) NOT NULL,
            pos_ref VARCHAR(64) NOT NULL,
            register_ref VARCHAR(64) NOT NULL,
            code VARCHAR(64) NOT NULL UNIQUE,
            status VARCHAR(32) NOT NULL DEFAULT 'active',
            label VARCHAR(120),
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            last_used_at DATETIME
        );
        """
    with engine.begin() as conn:
        for stmt in ddl.strip().split(';'):
            s = stmt.strip()
            if s:
                conn.execute(text(s))
    if printfn:
        printfn('eposone_provisioning_code: tabla creada')
