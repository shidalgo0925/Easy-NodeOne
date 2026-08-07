"""DDL — dominio comercial ETS (ADR-031): Cliente + Contrato + FK en Suscripción."""

from __future__ import annotations

from sqlalchemy import inspect, text


def ensure_ets_commercial_schema(db, engine, printfn=None) -> None:
    insp = inspect(engine)
    tables = set(insp.get_table_names())
    dialect = engine.dialect.name

    _ensure_customer(engine, dialect, tables, printfn)
    tables = set(inspect(engine).get_table_names())
    _ensure_contract(engine, dialect, tables, printfn)
    _ensure_subscription_contract_id(engine, dialect, printfn)


def _ensure_customer(engine, dialect: str, tables: set[str], printfn) -> None:
    if 'ets_commercial_customer' in tables:
        if printfn:
            printfn('ets_commercial_customer: ya existe')
        return

    if dialect == 'postgresql':
        ddl = """
        CREATE TABLE IF NOT EXISTS ets_commercial_customer (
            id SERIAL PRIMARY KEY,
            organization_id INTEGER NOT NULL REFERENCES saas_organization(id) ON DELETE CASCADE,
            display_name VARCHAR(200) NOT NULL,
            email VARCHAR(200) NOT NULL,
            phone VARCHAR(64),
            country VARCHAR(120),
            status VARCHAR(32) NOT NULL DEFAULT 'registered',
            primary_user_id INTEGER,
            metadata_json TEXT,
            created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (NOW() AT TIME ZONE 'utc'),
            updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (NOW() AT TIME ZONE 'utc'),
            CONSTRAINT uq_ets_commercial_customer_org UNIQUE (organization_id)
        );
        CREATE INDEX IF NOT EXISTS ix_ets_commercial_customer_email
            ON ets_commercial_customer (email);
        CREATE INDEX IF NOT EXISTS ix_ets_commercial_customer_status
            ON ets_commercial_customer (status);
        """
    else:
        ddl = """
        CREATE TABLE IF NOT EXISTS ets_commercial_customer (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            organization_id INTEGER NOT NULL UNIQUE,
            display_name VARCHAR(200) NOT NULL,
            email VARCHAR(200) NOT NULL,
            phone VARCHAR(64),
            country VARCHAR(120),
            status VARCHAR(32) NOT NULL DEFAULT 'registered',
            primary_user_id INTEGER,
            metadata_json TEXT,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        """

    with engine.begin() as conn:
        for stmt in ddl.strip().split(';'):
            s = stmt.strip()
            if s:
                conn.execute(text(s))
    if printfn:
        printfn('ets_commercial_customer: tabla creada')


def _ensure_contract(engine, dialect: str, tables: set[str], printfn) -> None:
    if 'ets_commercial_contract' in tables:
        if printfn:
            printfn('ets_commercial_contract: ya existe')
        return

    if dialect == 'postgresql':
        ddl = """
        CREATE TABLE IF NOT EXISTS ets_commercial_contract (
            id SERIAL PRIMARY KEY,
            contract_number VARCHAR(64) NOT NULL,
            customer_id INTEGER NOT NULL REFERENCES ets_commercial_customer(id) ON DELETE CASCADE,
            organization_id INTEGER NOT NULL REFERENCES saas_organization(id) ON DELETE CASCADE,
            product_code VARCHAR(64) NOT NULL,
            plan_code VARCHAR(64) NOT NULL,
            modality VARCHAR(32) NOT NULL DEFAULT 'connected',
            status VARCHAR(32) NOT NULL DEFAULT 'active',
            starts_at TIMESTAMP WITHOUT TIME ZONE,
            ends_at TIMESTAMP WITHOUT TIME ZONE,
            source VARCHAR(64),
            metadata_json TEXT,
            created_by_user_id INTEGER,
            created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (NOW() AT TIME ZONE 'utc'),
            updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (NOW() AT TIME ZONE 'utc'),
            CONSTRAINT uq_ets_commercial_contract_number UNIQUE (contract_number)
        );
        CREATE INDEX IF NOT EXISTS ix_ets_commercial_contract_customer
            ON ets_commercial_contract (customer_id);
        CREATE INDEX IF NOT EXISTS ix_ets_commercial_contract_org
            ON ets_commercial_contract (organization_id);
        CREATE INDEX IF NOT EXISTS ix_ets_commercial_contract_product
            ON ets_commercial_contract (product_code);
        CREATE INDEX IF NOT EXISTS ix_ets_commercial_contract_status
            ON ets_commercial_contract (status);
        """
    else:
        ddl = """
        CREATE TABLE IF NOT EXISTS ets_commercial_contract (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            contract_number VARCHAR(64) NOT NULL UNIQUE,
            customer_id INTEGER NOT NULL,
            organization_id INTEGER NOT NULL,
            product_code VARCHAR(64) NOT NULL,
            plan_code VARCHAR(64) NOT NULL,
            modality VARCHAR(32) NOT NULL DEFAULT 'connected',
            status VARCHAR(32) NOT NULL DEFAULT 'active',
            starts_at DATETIME,
            ends_at DATETIME,
            source VARCHAR(64),
            metadata_json TEXT,
            created_by_user_id INTEGER,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        """

    with engine.begin() as conn:
        for stmt in ddl.strip().split(';'):
            s = stmt.strip()
            if s:
                conn.execute(text(s))
    if printfn:
        printfn('ets_commercial_contract: tabla creada')


def _ensure_subscription_contract_id(engine, dialect: str, printfn) -> None:
    insp = inspect(engine)
    if 'ets_product_subscription' not in set(insp.get_table_names()):
        return
    cols = {c['name'] for c in insp.get_columns('ets_product_subscription')}
    if 'contract_id' in cols:
        if printfn:
            printfn('ets_product_subscription.contract_id: ya existe')
        return

    if dialect == 'postgresql':
        stmt = (
            'ALTER TABLE ets_product_subscription '
            'ADD COLUMN IF NOT EXISTS contract_id INTEGER '
            'REFERENCES ets_commercial_contract(id) ON DELETE SET NULL'
        )
        idx = (
            'CREATE INDEX IF NOT EXISTS ix_ets_product_subscription_contract '
            'ON ets_product_subscription (contract_id)'
        )
    else:
        stmt = 'ALTER TABLE ets_product_subscription ADD COLUMN contract_id INTEGER'
        idx = None

    with engine.begin() as conn:
        conn.execute(text(stmt))
        if idx:
            conn.execute(text(idx))
    if printfn:
        printfn('ets_product_subscription.contract_id: columna añadida')
