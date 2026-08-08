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
    _migrate_customer_under_provider(engine, dialect, printfn)
    _migrate_subscription_customer_id(engine, dialect, printfn)
    _migrate_expediente_columns(engine, dialect, printfn)
    _ensure_attribution(engine, dialect, printfn)


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


def _migrate_customer_under_provider(engine, dialect: str, printfn) -> None:
    """Varios clientes comerciales bajo la misma org proveedor ETS (ADR-031 §4.1)."""
    insp = inspect(engine)
    if 'ets_commercial_customer' not in set(insp.get_table_names()):
        return
    if dialect != 'postgresql':
        if printfn:
            printfn('ets_commercial_customer multi-provider: skip (non-pg)')
        return
    with engine.begin() as conn:
        conn.execute(text('ALTER TABLE ets_commercial_customer DROP CONSTRAINT IF EXISTS uq_ets_commercial_customer_org'))
        conn.execute(
            text(
                'CREATE UNIQUE INDEX IF NOT EXISTS uq_ets_commercial_customer_provider_email '
                'ON ets_commercial_customer (organization_id, email)'
            )
        )
    if printfn:
        printfn('ets_commercial_customer: unique (organization_id, email) — multi-cliente bajo ETS')


def _migrate_subscription_customer_id(engine, dialect: str, printfn) -> None:
    """Suscripción por cliente comercial (Standalone bajo ETS) sin romper Connected legado."""
    insp = inspect(engine)
    if 'ets_product_subscription' not in set(insp.get_table_names()):
        return
    cols = {c['name'] for c in insp.get_columns('ets_product_subscription')}
    if dialect != 'postgresql':
        if 'customer_id' not in cols:
            with engine.begin() as conn:
                conn.execute(text('ALTER TABLE ets_product_subscription ADD COLUMN customer_id INTEGER'))
        if printfn:
            printfn('ets_product_subscription.customer_id: added (non-pg, sin índices parciales)')
        return

    with engine.begin() as conn:
        if 'customer_id' not in cols:
            conn.execute(
                text(
                    'ALTER TABLE ets_product_subscription '
                    'ADD COLUMN IF NOT EXISTS customer_id INTEGER '
                    'REFERENCES ets_commercial_customer(id) ON DELETE SET NULL'
                )
            )
            conn.execute(
                text(
                    'CREATE INDEX IF NOT EXISTS ix_ets_product_subscription_customer '
                    'ON ets_product_subscription (customer_id)'
                )
            )
        conn.execute(
            text('ALTER TABLE ets_product_subscription DROP CONSTRAINT IF EXISTS uq_ets_product_subscription_org_product')
        )
        conn.execute(
            text(
                'CREATE UNIQUE INDEX IF NOT EXISTS uq_ets_sub_org_product_legacy '
                'ON ets_product_subscription (organization_id, product_code) '
                'WHERE customer_id IS NULL'
            )
        )
        conn.execute(
            text(
                'CREATE UNIQUE INDEX IF NOT EXISTS uq_ets_sub_customer_product '
                'ON ets_product_subscription (customer_id, product_code) '
                'WHERE customer_id IS NOT NULL'
            )
        )
    if printfn:
        printfn('ets_product_subscription.customer_id + uniques parciales OK')


def _add_col_pg(conn, table: str, col: str, ddl_type: str) -> None:
    conn.execute(text(f'ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {col} {ddl_type}'))


def _migrate_expediente_columns(engine, dialect: str, printfn) -> None:
    """Columnas de expediente comercial (contact_id, precio, evidencia contrato)."""
    insp = inspect(engine)
    tables = set(insp.get_table_names())
    if 'ets_commercial_customer' not in tables or 'ets_commercial_contract' not in tables:
        return
    if dialect != 'postgresql':
        if printfn:
            printfn('expediente columns: skip non-pg')
        return

    cust_cols = {c['name'] for c in insp.get_columns('ets_commercial_customer')}
    ctr_cols = {c['name'] for c in insp.get_columns('ets_commercial_contract')}
    with engine.begin() as conn:
        if 'contact_id' not in cust_cols:
            _add_col_pg(conn, 'ets_commercial_customer', 'contact_id', 'INTEGER')
            conn.execute(
                text(
                    'CREATE INDEX IF NOT EXISTS ix_ets_commercial_customer_contact '
                    'ON ets_commercial_customer (contact_id)'
                )
            )
        for col, typ in (
            ('agreed_price', 'NUMERIC(12,2)'),
            ('discount_percent', 'NUMERIC(5,2)'),
            ('discount_amount', 'NUMERIC(12,2)'),
            ('currency', 'VARCHAR(8)'),
            ('billing_period', 'VARCHAR(16)'),
            ('implementation_mode', 'VARCHAR(32)'),
            ('contract_type', 'VARCHAR(16)'),
            ('contract_version', 'VARCHAR(32)'),
            ('terms_version', 'VARCHAR(32)'),
            ('accepted_at', 'TIMESTAMP WITHOUT TIME ZONE'),
            ('accepted_by_user_id', 'INTEGER'),
            ('attachment_id', 'INTEGER'),
        ):
            if col not in ctr_cols:
                _add_col_pg(conn, 'ets_commercial_contract', col, typ)
    if printfn:
        printfn('expediente: customer.contact_id + contract commercial/evidence OK')


def _ensure_attribution(engine, dialect: str, printfn) -> None:
    insp = inspect(engine)
    if 'ets_commercial_attribution' in set(insp.get_table_names()):
        if printfn:
            printfn('ets_commercial_attribution: ya existe')
        return
    if dialect == 'postgresql':
        ddl = """
        CREATE TABLE IF NOT EXISTS ets_commercial_attribution (
            id SERIAL PRIMARY KEY,
            organization_id INTEGER NOT NULL REFERENCES saas_organization(id) ON DELETE CASCADE,
            customer_id INTEGER NOT NULL REFERENCES ets_commercial_customer(id) ON DELETE CASCADE,
            contract_id INTEGER,
            channel VARCHAR(64) NOT NULL DEFAULT 'web',
            source_detail VARCHAR(200),
            campaign VARCHAR(200),
            referral_code VARCHAR(64),
            advisor_user_id INTEGER,
            utm_source VARCHAR(120),
            utm_medium VARCHAR(120),
            utm_campaign VARCHAR(120),
            utm_content VARCHAR(120),
            utm_term VARCHAR(120),
            landing_url VARCHAR(500),
            attributed_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (NOW() AT TIME ZONE 'utc'),
            metadata_json TEXT,
            created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (NOW() AT TIME ZONE 'utc'),
            updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (NOW() AT TIME ZONE 'utc'),
            CONSTRAINT uq_ets_commercial_attribution_customer UNIQUE (customer_id)
        );
        CREATE INDEX IF NOT EXISTS ix_ets_commercial_attribution_org ON ets_commercial_attribution (organization_id);
        CREATE INDEX IF NOT EXISTS ix_ets_commercial_attribution_channel ON ets_commercial_attribution (channel);
        CREATE INDEX IF NOT EXISTS ix_ets_commercial_attribution_referral ON ets_commercial_attribution (referral_code);
        """
    else:
        ddl = """
        CREATE TABLE IF NOT EXISTS ets_commercial_attribution (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            organization_id INTEGER NOT NULL,
            customer_id INTEGER NOT NULL UNIQUE,
            contract_id INTEGER,
            channel VARCHAR(64) NOT NULL DEFAULT 'web',
            source_detail VARCHAR(200),
            campaign VARCHAR(200),
            referral_code VARCHAR(64),
            advisor_user_id INTEGER,
            utm_source VARCHAR(120),
            utm_medium VARCHAR(120),
            utm_campaign VARCHAR(120),
            utm_content VARCHAR(120),
            utm_term VARCHAR(120),
            landing_url VARCHAR(500),
            attributed_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
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
        printfn('ets_commercial_attribution: tabla creada')
