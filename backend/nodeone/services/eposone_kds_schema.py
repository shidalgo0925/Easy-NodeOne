"""DDL idempotente — KDS EPosOne (Etapa 15)."""

from __future__ import annotations

from sqlalchemy import inspect, text


def ensure_eposone_kds_schema(db, engine, printfn=None) -> None:
    insp = inspect(engine)
    tables = set(insp.get_table_names())
    dialect = engine.dialect.name

    if 'eposone_kds_station' not in tables:
        if dialect == 'postgresql':
            ddl = """
            CREATE TABLE IF NOT EXISTS eposone_kds_station (
                id SERIAL PRIMARY KEY,
                organization_id INTEGER NOT NULL REFERENCES saas_organization(id) ON DELETE CASCADE,
                station_ref VARCHAR(64) NOT NULL,
                name VARCHAR(120) NOT NULL,
                station_type VARCHAR(32) NOT NULL DEFAULT 'kitchen',
                active BOOLEAN NOT NULL DEFAULT TRUE,
                created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (NOW() AT TIME ZONE 'utc'),
                CONSTRAINT uq_eposone_kds_station_ref UNIQUE (organization_id, station_ref)
            );
            CREATE INDEX IF NOT EXISTS ix_eposone_kds_station_org ON eposone_kds_station (organization_id);
            """
        else:
            ddl = """
            CREATE TABLE IF NOT EXISTS eposone_kds_station (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                organization_id INTEGER NOT NULL,
                station_ref VARCHAR(64) NOT NULL,
                name VARCHAR(120) NOT NULL,
                station_type VARCHAR(32) NOT NULL DEFAULT 'kitchen',
                active INTEGER NOT NULL DEFAULT 1,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (organization_id, station_ref)
            );
            """
        _run(engine, ddl, printfn, 'eposone_kds_station')

    if 'eposone_kds_ticket' not in tables:
        if dialect == 'postgresql':
            ddl = """
            CREATE TABLE IF NOT EXISTS eposone_kds_ticket (
                id SERIAL PRIMARY KEY,
                organization_id INTEGER NOT NULL REFERENCES saas_organization(id) ON DELETE CASCADE,
                order_id INTEGER NOT NULL REFERENCES core_commercial_order(id) ON DELETE CASCADE,
                order_ref VARCHAR(50) NOT NULL,
                station_id INTEGER REFERENCES eposone_kds_station(id) ON DELETE SET NULL,
                station_type VARCHAR(32) NOT NULL DEFAULT 'kitchen',
                status VARCHAR(32) NOT NULL DEFAULT 'pending',
                priority INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (NOW() AT TIME ZONE 'utc'),
                ready_at TIMESTAMP WITHOUT TIME ZONE,
                served_at TIMESTAMP WITHOUT TIME ZONE
            );
            CREATE INDEX IF NOT EXISTS ix_eposone_kds_ticket_org_status ON eposone_kds_ticket (organization_id, status);
            """
        else:
            ddl = """
            CREATE TABLE IF NOT EXISTS eposone_kds_ticket (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                organization_id INTEGER NOT NULL,
                order_id INTEGER NOT NULL,
                order_ref VARCHAR(50) NOT NULL,
                station_id INTEGER,
                station_type VARCHAR(32) NOT NULL DEFAULT 'kitchen',
                status VARCHAR(32) NOT NULL DEFAULT 'pending',
                priority INTEGER NOT NULL DEFAULT 0,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                ready_at DATETIME,
                served_at DATETIME
            );
            """
        _run(engine, ddl, printfn, 'eposone_kds_ticket')

    if 'eposone_kds_ticket_line' not in tables:
        if dialect == 'postgresql':
            ddl = """
            CREATE TABLE IF NOT EXISTS eposone_kds_ticket_line (
                id SERIAL PRIMARY KEY,
                ticket_id INTEGER NOT NULL REFERENCES eposone_kds_ticket(id) ON DELETE CASCADE,
                description VARCHAR(500) NOT NULL,
                quantity DOUBLE PRECISION NOT NULL DEFAULT 1,
                status VARCHAR(32) NOT NULL DEFAULT 'pending'
            );
            CREATE INDEX IF NOT EXISTS ix_eposone_kds_ticket_line_ticket ON eposone_kds_ticket_line (ticket_id);
            """
        else:
            ddl = """
            CREATE TABLE IF NOT EXISTS eposone_kds_ticket_line (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticket_id INTEGER NOT NULL,
                description VARCHAR(500) NOT NULL,
                quantity REAL NOT NULL DEFAULT 1,
                status VARCHAR(32) NOT NULL DEFAULT 'pending'
            );
            """
        _run(engine, ddl, printfn, 'eposone_kds_ticket_line')


def _run(engine, ddl: str, printfn, label: str) -> None:
    with engine.begin() as conn:
        for stmt in ddl.strip().split(';'):
            s = stmt.strip()
            if s:
                conn.execute(text(s))
    if printfn:
        printfn(f'{label}: tabla creada')
