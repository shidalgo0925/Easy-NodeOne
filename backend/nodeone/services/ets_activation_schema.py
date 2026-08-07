"""DDL — ets_activation_license + ets_activation_token (ADR-035)."""

from __future__ import annotations

from sqlalchemy import inspect, text


def ensure_ets_activation_schema(db, engine, printfn=None) -> None:
    insp = inspect(engine)
    tables = set(insp.get_table_names())
    dialect = engine.dialect.name
    _ensure_license(engine, dialect, tables, printfn)
    tables = set(inspect(engine).get_table_names())
    _ensure_token(engine, dialect, tables, printfn)


def _ensure_license(engine, dialect: str, tables: set[str], printfn) -> None:
    if 'ets_activation_license' in tables:
        if printfn:
            printfn('ets_activation_license: ya existe')
        return
    if dialect == 'postgresql':
        ddl = """
        CREATE TABLE IF NOT EXISTS ets_activation_license (
            id SERIAL PRIMARY KEY,
            organization_id INTEGER NOT NULL REFERENCES saas_organization(id) ON DELETE CASCADE,
            contract_id INTEGER,
            subscription_id INTEGER,
            product_code VARCHAR(64) NOT NULL DEFAULT 'eposone',
            modality VARCHAR(32) NOT NULL,
            implementation_strategy VARCHAR(32) NOT NULL,
            status VARCHAR(32) NOT NULL DEFAULT 'issued',
            starts_at TIMESTAMP WITHOUT TIME ZONE,
            ends_at TIMESTAMP WITHOUT TIME ZONE,
            metadata_json TEXT,
            created_by_user_id INTEGER,
            revoked_at TIMESTAMP WITHOUT TIME ZONE,
            revoke_reason VARCHAR(200),
            created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (NOW() AT TIME ZONE 'utc'),
            updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (NOW() AT TIME ZONE 'utc')
        );
        CREATE INDEX IF NOT EXISTS ix_ets_activation_license_org
            ON ets_activation_license (organization_id);
        CREATE INDEX IF NOT EXISTS ix_ets_activation_license_status
            ON ets_activation_license (status);
        CREATE INDEX IF NOT EXISTS ix_ets_activation_license_product
            ON ets_activation_license (product_code);
        """
    else:
        ddl = """
        CREATE TABLE IF NOT EXISTS ets_activation_license (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            organization_id INTEGER NOT NULL,
            contract_id INTEGER,
            subscription_id INTEGER,
            product_code VARCHAR(64) NOT NULL DEFAULT 'eposone',
            modality VARCHAR(32) NOT NULL,
            implementation_strategy VARCHAR(32) NOT NULL,
            status VARCHAR(32) NOT NULL DEFAULT 'issued',
            starts_at DATETIME,
            ends_at DATETIME,
            metadata_json TEXT,
            created_by_user_id INTEGER,
            revoked_at DATETIME,
            revoke_reason VARCHAR(200),
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
        printfn('ets_activation_license: tabla creada')


def _ensure_token(engine, dialect: str, tables: set[str], printfn) -> None:
    if 'ets_activation_token' in tables:
        if printfn:
            printfn('ets_activation_token: ya existe')
        return
    if dialect == 'postgresql':
        ddl = """
        CREATE TABLE IF NOT EXISTS ets_activation_token (
            id SERIAL PRIMARY KEY,
            license_id INTEGER NOT NULL REFERENCES ets_activation_license(id) ON DELETE CASCADE,
            organization_id INTEGER NOT NULL REFERENCES saas_organization(id) ON DELETE CASCADE,
            token VARCHAR(64) NOT NULL,
            status VARCHAR(32) NOT NULL DEFAULT 'active',
            expires_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
            max_uses INTEGER NOT NULL DEFAULT 1,
            uses_count INTEGER NOT NULL DEFAULT 0,
            register_ref VARCHAR(64),
            jti VARCHAR(64) NOT NULL,
            consumed_at TIMESTAMP WITHOUT TIME ZONE,
            consumed_device_uuid VARCHAR(128),
            revoked_at TIMESTAMP WITHOUT TIME ZONE,
            revoke_reason VARCHAR(200),
            created_by_user_id INTEGER,
            created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (NOW() AT TIME ZONE 'utc'),
            updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (NOW() AT TIME ZONE 'utc'),
            CONSTRAINT uq_ets_activation_token_token UNIQUE (token),
            CONSTRAINT uq_ets_activation_token_jti UNIQUE (jti)
        );
        CREATE INDEX IF NOT EXISTS ix_ets_activation_token_license
            ON ets_activation_token (license_id);
        CREATE INDEX IF NOT EXISTS ix_ets_activation_token_org
            ON ets_activation_token (organization_id);
        CREATE INDEX IF NOT EXISTS ix_ets_activation_token_status
            ON ets_activation_token (status);
        """
    else:
        ddl = """
        CREATE TABLE IF NOT EXISTS ets_activation_token (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            license_id INTEGER NOT NULL,
            organization_id INTEGER NOT NULL,
            token VARCHAR(64) NOT NULL UNIQUE,
            status VARCHAR(32) NOT NULL DEFAULT 'active',
            expires_at DATETIME NOT NULL,
            max_uses INTEGER NOT NULL DEFAULT 1,
            uses_count INTEGER NOT NULL DEFAULT 0,
            register_ref VARCHAR(64),
            jti VARCHAR(64) NOT NULL UNIQUE,
            consumed_at DATETIME,
            consumed_device_uuid VARCHAR(128),
            revoked_at DATETIME,
            revoke_reason VARCHAR(200),
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
        printfn('ets_activation_token: tabla creada')
