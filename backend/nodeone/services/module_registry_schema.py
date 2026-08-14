"""DDL — module_definition + organization_module (ADR-038 F1)."""

from __future__ import annotations

from sqlalchemy import inspect, text


def ensure_module_registry_schema(db, engine, printfn=None) -> None:
    insp = inspect(engine)
    tables = set(insp.get_table_names())
    dialect = engine.dialect.name
    created = False

    if 'module_definition' not in tables:
        if dialect == 'postgresql':
            ddl = """
            CREATE TABLE IF NOT EXISTS module_definition (
                id SERIAL PRIMARY KEY,
                module_key VARCHAR(64) NOT NULL,
                name VARCHAR(200) NOT NULL,
                description TEXT,
                version VARCHAR(32) NOT NULL DEFAULT '1',
                status VARCHAR(32) NOT NULL DEFAULT 'active',
                dependencies_json TEXT,
                configurable_per_org BOOLEAN NOT NULL DEFAULT TRUE,
                is_core BOOLEAN NOT NULL DEFAULT FALSE,
                saas_code VARCHAR(64),
                nav_metadata_json TEXT,
                created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (NOW() AT TIME ZONE 'utc'),
                updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (NOW() AT TIME ZONE 'utc'),
                CONSTRAINT uq_module_definition_key UNIQUE (module_key)
            );
            CREATE INDEX IF NOT EXISTS ix_module_definition_status ON module_definition (status);
            CREATE INDEX IF NOT EXISTS ix_module_definition_saas_code ON module_definition (saas_code);
            """
        else:
            ddl = """
            CREATE TABLE IF NOT EXISTS module_definition (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                module_key VARCHAR(64) NOT NULL UNIQUE,
                name VARCHAR(200) NOT NULL,
                description TEXT,
                version VARCHAR(32) NOT NULL DEFAULT '1',
                status VARCHAR(32) NOT NULL DEFAULT 'active',
                dependencies_json TEXT,
                configurable_per_org BOOLEAN NOT NULL DEFAULT 1,
                is_core BOOLEAN NOT NULL DEFAULT 0,
                saas_code VARCHAR(64),
                nav_metadata_json TEXT,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            """
        with engine.begin() as conn:
            for stmt in ddl.strip().split(';'):
                s = stmt.strip()
                if s:
                    conn.execute(text(s))
        created = True
        if printfn:
            printfn('module_definition: tabla creada')
    elif printfn:
        printfn('module_definition: ya existe')

    tables = set(inspect(engine).get_table_names())
    if 'organization_module' not in tables:
        if dialect == 'postgresql':
            ddl = """
            CREATE TABLE IF NOT EXISTS organization_module (
                id SERIAL PRIMARY KEY,
                organization_id INTEGER NOT NULL REFERENCES saas_organization(id) ON DELETE CASCADE,
                module_key VARCHAR(64) NOT NULL,
                enabled BOOLEAN NOT NULL DEFAULT FALSE,
                enabled_at TIMESTAMP WITHOUT TIME ZONE,
                disabled_at TIMESTAMP WITHOUT TIME ZONE,
                config_json TEXT,
                created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (NOW() AT TIME ZONE 'utc'),
                updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (NOW() AT TIME ZONE 'utc'),
                CONSTRAINT uq_organization_module_org_key UNIQUE (organization_id, module_key)
            );
            CREATE INDEX IF NOT EXISTS ix_organization_module_org ON organization_module (organization_id);
            CREATE INDEX IF NOT EXISTS ix_organization_module_key ON organization_module (module_key);
            CREATE INDEX IF NOT EXISTS ix_organization_module_org_enabled
                ON organization_module (organization_id, enabled);
            """
        else:
            ddl = """
            CREATE TABLE IF NOT EXISTS organization_module (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                organization_id INTEGER NOT NULL,
                module_key VARCHAR(64) NOT NULL,
                enabled BOOLEAN NOT NULL DEFAULT 0,
                enabled_at DATETIME,
                disabled_at DATETIME,
                config_json TEXT,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (organization_id, module_key)
            );
            """
        with engine.begin() as conn:
            for stmt in ddl.strip().split(';'):
                s = stmt.strip()
                if s:
                    conn.execute(text(s))
        created = True
        if printfn:
            printfn('organization_module: tabla creada')
    elif printfn:
        printfn('organization_module: ya existe')

    if created and printfn:
        printfn('module_registry schema: listo')
