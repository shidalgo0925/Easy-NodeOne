"""DDL idempotente — Delivery EPosOne (Etapa 16)."""

from __future__ import annotations

from sqlalchemy import inspect, text


def ensure_eposone_delivery_schema(db, engine, printfn=None) -> None:
    insp = inspect(engine)
    if 'eposone_delivery' in insp.get_table_names():
        return

    dialect = engine.dialect.name
    if dialect == 'postgresql':
        ddl = """
        CREATE TABLE IF NOT EXISTS eposone_delivery (
            id SERIAL PRIMARY KEY,
            organization_id INTEGER NOT NULL REFERENCES saas_organization(id) ON DELETE CASCADE,
            order_id INTEGER NOT NULL REFERENCES core_commercial_order(id) ON DELETE CASCADE,
            order_ref VARCHAR(50) NOT NULL,
            status VARCHAR(32) NOT NULL DEFAULT 'pending',
            driver_name VARCHAR(200),
            driver_contact_id INTEGER REFERENCES en1_contact(id) ON DELETE SET NULL,
            destination_address TEXT,
            notes TEXT,
            total_qty DOUBLE PRECISION NOT NULL DEFAULT 0,
            delivered_qty DOUBLE PRECISION NOT NULL DEFAULT 0,
            assigned_at TIMESTAMP WITHOUT TIME ZONE,
            delivered_at TIMESTAMP WITHOUT TIME ZONE,
            created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (NOW() AT TIME ZONE 'utc'),
            CONSTRAINT uq_eposone_delivery_order UNIQUE (organization_id, order_id)
        );
        CREATE INDEX IF NOT EXISTS ix_eposone_delivery_org_status ON eposone_delivery (organization_id, status);
        """
    else:
        ddl = """
        CREATE TABLE IF NOT EXISTS eposone_delivery (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            organization_id INTEGER NOT NULL,
            order_id INTEGER NOT NULL,
            order_ref VARCHAR(50) NOT NULL,
            status VARCHAR(32) NOT NULL DEFAULT 'pending',
            driver_name VARCHAR(200),
            driver_contact_id INTEGER,
            destination_address TEXT,
            notes TEXT,
            total_qty REAL NOT NULL DEFAULT 0,
            delivered_qty REAL NOT NULL DEFAULT 0,
            assigned_at DATETIME,
            delivered_at DATETIME,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (organization_id, order_id)
        );
        """
    with engine.begin() as conn:
        for stmt in ddl.strip().split(';'):
            s = stmt.strip()
            if s:
                conn.execute(text(s))
    if printfn:
        printfn('eposone_delivery: tabla creada')
