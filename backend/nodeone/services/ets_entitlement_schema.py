"""DDL — ets_product_entitlement (ADR-016 Licensing V2 Entitlement)."""

from __future__ import annotations

from sqlalchemy import inspect, text


def ensure_ets_product_entitlement_schema(db, engine, printfn=None) -> None:
    insp = inspect(engine)
    tables = set(insp.get_table_names())
    dialect = engine.dialect.name

    if 'ets_product_entitlement' in tables:
        if printfn:
            printfn('ets_product_entitlement: ya existe')
        return

    if dialect == 'postgresql':
        ddl = """
        CREATE TABLE IF NOT EXISTS ets_product_entitlement (
            id SERIAL PRIMARY KEY,
            subscription_id INTEGER NOT NULL REFERENCES ets_product_subscription(id) ON DELETE CASCADE,
            organization_id INTEGER NOT NULL REFERENCES saas_organization(id) ON DELETE CASCADE,
            product_code VARCHAR(64) NOT NULL,
            plan_code VARCHAR(64) NOT NULL DEFAULT 'starter',
            resource_limits_json TEXT,
            features_json TEXT,
            overrides_json TEXT,
            effective_state VARCHAR(32) NOT NULL DEFAULT 'trial',
            starts_at TIMESTAMP WITHOUT TIME ZONE,
            ends_at TIMESTAMP WITHOUT TIME ZONE,
            updated_by_user_id INTEGER,
            created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (NOW() AT TIME ZONE 'utc'),
            updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (NOW() AT TIME ZONE 'utc'),
            CONSTRAINT uq_ets_product_entitlement_subscription UNIQUE (subscription_id),
            CONSTRAINT uq_ets_product_entitlement_org_product UNIQUE (organization_id, product_code)
        );
        CREATE INDEX IF NOT EXISTS ix_ets_product_entitlement_org
            ON ets_product_entitlement (organization_id);
        CREATE INDEX IF NOT EXISTS ix_ets_product_entitlement_product
            ON ets_product_entitlement (product_code);
        CREATE INDEX IF NOT EXISTS ix_ets_product_entitlement_state
            ON ets_product_entitlement (effective_state);
        CREATE INDEX IF NOT EXISTS ix_ets_ent_org_state
            ON ets_product_entitlement (organization_id, effective_state);
        """
    else:
        ddl = """
        CREATE TABLE IF NOT EXISTS ets_product_entitlement (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subscription_id INTEGER NOT NULL UNIQUE,
            organization_id INTEGER NOT NULL,
            product_code VARCHAR(64) NOT NULL,
            plan_code VARCHAR(64) NOT NULL DEFAULT 'starter',
            resource_limits_json TEXT,
            features_json TEXT,
            overrides_json TEXT,
            effective_state VARCHAR(32) NOT NULL DEFAULT 'trial',
            starts_at DATETIME,
            ends_at DATETIME,
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
        printfn('ets_product_entitlement: tabla creada')
