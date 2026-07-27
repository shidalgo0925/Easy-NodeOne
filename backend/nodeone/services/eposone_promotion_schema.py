"""DDL idempotente — promociones EPosOne."""

from __future__ import annotations

from sqlalchemy import inspect, text


def ensure_eposone_promotion_schema(db, engine, printfn=None) -> None:
    insp = inspect(engine)
    if 'eposone_promotion' in insp.get_table_names():
        return

    dialect = engine.dialect.name
    if dialect == 'postgresql':
        ddl = """
        CREATE TABLE IF NOT EXISTS eposone_promotion (
            id SERIAL PRIMARY KEY,
            organization_id INTEGER NOT NULL REFERENCES saas_organization(id) ON DELETE CASCADE,
            promo_ref VARCHAR(64) NOT NULL,
            name VARCHAR(200) NOT NULL,
            promo_type VARCHAR(32) NOT NULL DEFAULT 'percent',
            value DOUBLE PRECISION NOT NULL DEFAULT 0,
            code VARCHAR(64),
            active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (NOW() AT TIME ZONE 'utc'),
            CONSTRAINT uq_eposone_promotion_ref UNIQUE (organization_id, promo_ref),
            CONSTRAINT uq_eposone_promotion_code UNIQUE (organization_id, code)
        );
        CREATE INDEX IF NOT EXISTS ix_eposone_promotion_org_active ON eposone_promotion (organization_id, active);
        """
    else:
        ddl = """
        CREATE TABLE IF NOT EXISTS eposone_promotion (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            organization_id INTEGER NOT NULL,
            promo_ref VARCHAR(64) NOT NULL,
            name VARCHAR(200) NOT NULL,
            promo_type VARCHAR(32) NOT NULL DEFAULT 'percent',
            value REAL NOT NULL DEFAULT 0,
            code VARCHAR(64),
            active INTEGER NOT NULL DEFAULT 1,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (organization_id, promo_ref),
            UNIQUE (organization_id, code)
        );
        """
    with engine.begin() as conn:
        for stmt in ddl.strip().split(';'):
            s = stmt.strip()
            if s:
                conn.execute(text(s))
    if printfn:
        printfn('eposone_promotion: tabla creada')
