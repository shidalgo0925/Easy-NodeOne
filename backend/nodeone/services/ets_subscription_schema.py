"""DDL — ets_product_subscription (Subscription Registry V1)."""

from __future__ import annotations

from sqlalchemy import inspect, text


def ensure_ets_product_subscription_schema(db, engine, printfn=None) -> None:
    insp = inspect(engine)
    tables = set(insp.get_table_names())
    dialect = engine.dialect.name

    if 'ets_product_subscription' in tables:
        if printfn:
            printfn('ets_product_subscription: ya existe')
        # contract_id lo añade ensure_ets_commercial_schema (depende de ets_commercial_contract)
        return

    if dialect == 'postgresql':
        ddl = """
        CREATE TABLE IF NOT EXISTS ets_product_subscription (
            id SERIAL PRIMARY KEY,
            organization_id INTEGER NOT NULL REFERENCES saas_organization(id) ON DELETE CASCADE,
            product_code VARCHAR(64) NOT NULL,
            status VARCHAR(32) NOT NULL DEFAULT 'pending',
            starts_at TIMESTAMP WITHOUT TIME ZONE,
            ends_at TIMESTAMP WITHOUT TIME ZONE,
            trial_ends_at TIMESTAMP WITHOUT TIME ZONE,
            reason VARCHAR(200),
            metadata_json TEXT,
            contract_id INTEGER,
            created_by_user_id INTEGER,
            updated_by_user_id INTEGER,
            created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (NOW() AT TIME ZONE 'utc'),
            updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (NOW() AT TIME ZONE 'utc'),
            CONSTRAINT uq_ets_product_subscription_org_product UNIQUE (organization_id, product_code)
        );
        CREATE INDEX IF NOT EXISTS ix_ets_product_subscription_org
            ON ets_product_subscription (organization_id);
        CREATE INDEX IF NOT EXISTS ix_ets_product_subscription_product
            ON ets_product_subscription (product_code);
        CREATE INDEX IF NOT EXISTS ix_ets_product_subscription_status
            ON ets_product_subscription (status);
        CREATE INDEX IF NOT EXISTS ix_ets_sub_org_status
            ON ets_product_subscription (organization_id, status);
        """
    else:
        ddl = """
        CREATE TABLE IF NOT EXISTS ets_product_subscription (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            organization_id INTEGER NOT NULL,
            product_code VARCHAR(64) NOT NULL,
            status VARCHAR(32) NOT NULL DEFAULT 'pending',
            starts_at DATETIME,
            ends_at DATETIME,
            trial_ends_at DATETIME,
            reason VARCHAR(200),
            metadata_json TEXT,
            contract_id INTEGER,
            created_by_user_id INTEGER,
            updated_by_user_id INTEGER,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (organization_id, product_code)
        );
        """

    with engine.begin() as conn:
        for stmt in ddl.strip().split(';'):
            s = stmt.strip()
            if s:
                conn.execute(text(s))
    if printfn:
        printfn('ets_product_subscription: tabla creada')
