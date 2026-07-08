"""DDL idempotente — menú digital EPosOne (Etapa 17)."""

from __future__ import annotations

from sqlalchemy import inspect, text


def ensure_eposone_digital_menu_schema(db, engine, printfn=None) -> None:
    insp = inspect(engine)
    tables = set(insp.get_table_names())
    dialect = engine.dialect.name

    if 'eposone_digital_menu' not in tables:
        if dialect == 'postgresql':
            ddl = """
            CREATE TABLE IF NOT EXISTS eposone_digital_menu (
                id SERIAL PRIMARY KEY,
                organization_id INTEGER NOT NULL REFERENCES saas_organization(id) ON DELETE CASCADE,
                menu_ref VARCHAR(64) NOT NULL,
                name VARCHAR(200) NOT NULL,
                public_token VARCHAR(64) NOT NULL,
                active BOOLEAN NOT NULL DEFAULT TRUE,
                created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (NOW() AT TIME ZONE 'utc'),
                CONSTRAINT uq_eposone_digital_menu_ref UNIQUE (organization_id, menu_ref),
                CONSTRAINT uq_eposone_digital_menu_token UNIQUE (public_token)
            );
            CREATE INDEX IF NOT EXISTS ix_eposone_digital_menu_org ON eposone_digital_menu (organization_id);
            """
        else:
            ddl = """
            CREATE TABLE IF NOT EXISTS eposone_digital_menu (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                organization_id INTEGER NOT NULL,
                menu_ref VARCHAR(64) NOT NULL,
                name VARCHAR(200) NOT NULL,
                public_token VARCHAR(64) NOT NULL UNIQUE,
                active INTEGER NOT NULL DEFAULT 1,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (organization_id, menu_ref)
            );
            """
        _run(engine, ddl, printfn, 'eposone_digital_menu')

    if 'eposone_digital_menu_item' not in tables:
        if dialect == 'postgresql':
            ddl = """
            CREATE TABLE IF NOT EXISTS eposone_digital_menu_item (
                id SERIAL PRIMARY KEY,
                menu_id INTEGER NOT NULL REFERENCES eposone_digital_menu(id) ON DELETE CASCADE,
                name VARCHAR(200) NOT NULL,
                description VARCHAR(500),
                category VARCHAR(120),
                price DOUBLE PRECISION NOT NULL DEFAULT 0,
                available BOOLEAN NOT NULL DEFAULT TRUE,
                sort_order INTEGER NOT NULL DEFAULT 0
            );
            CREATE INDEX IF NOT EXISTS ix_eposone_digital_menu_item_menu ON eposone_digital_menu_item (menu_id);
            """
        else:
            ddl = """
            CREATE TABLE IF NOT EXISTS eposone_digital_menu_item (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                menu_id INTEGER NOT NULL,
                name VARCHAR(200) NOT NULL,
                description VARCHAR(500),
                category VARCHAR(120),
                price REAL NOT NULL DEFAULT 0,
                available INTEGER NOT NULL DEFAULT 1,
                sort_order INTEGER NOT NULL DEFAULT 0
            );
            """
        _run(engine, ddl, printfn, 'eposone_digital_menu_item')


def _run(engine, ddl: str, printfn, label: str) -> None:
    with engine.begin() as conn:
        for stmt in ddl.strip().split(';'):
            s = stmt.strip()
            if s:
                conn.execute(text(s))
    if printfn:
        printfn(f'{label}: tabla creada')
