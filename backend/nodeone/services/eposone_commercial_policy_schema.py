"""DDL idempotente — Motor de Políticas Comerciales EPosOne (infra V6)."""

from __future__ import annotations

from sqlalchemy import inspect, text


def ensure_eposone_commercial_policy_schema(db, engine, printfn=None) -> None:
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    is_pg = engine.dialect.name == 'postgresql'

    def _exec(ddl: str) -> None:
        with engine.begin() as conn:
            conn.execute(text(ddl))

    if 'eposone_commercial_policy' not in tables:
        ddl = """
        CREATE TABLE eposone_commercial_policy (
            id SERIAL PRIMARY KEY,
            organization_id INTEGER NOT NULL
                REFERENCES saas_organization(id) ON DELETE CASCADE,
            policy_type VARCHAR(32) NOT NULL,
            code VARCHAR(64) NOT NULL,
            name VARCHAR(255) NOT NULL,
            active BOOLEAN NOT NULL DEFAULT TRUE,
            valid_from TIMESTAMP NULL,
            valid_to TIMESTAMP NULL,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT uq_eposone_commercial_policy_org_type_code
                UNIQUE (organization_id, policy_type, code)
        )
        """
        if not is_pg:
            ddl = ddl.replace('SERIAL PRIMARY KEY', 'INTEGER PRIMARY KEY AUTOINCREMENT')
            ddl = ddl.replace('BOOLEAN', 'INTEGER')
        _exec(ddl)
        if printfn:
            printfn('+ eposone_commercial_policy')

    if 'eposone_commercial_policy_version' not in tables:
        ddl = """
        CREATE TABLE eposone_commercial_policy_version (
            id SERIAL PRIMARY KEY,
            organization_id INTEGER NOT NULL
                REFERENCES saas_organization(id) ON DELETE CASCADE,
            policy_id INTEGER NOT NULL
                REFERENCES eposone_commercial_policy(id) ON DELETE CASCADE,
            version_number INTEGER NOT NULL,
            payload_json TEXT NOT NULL DEFAULT '{}',
            publication_status VARCHAR(16) NOT NULL DEFAULT 'draft',
            is_current BOOLEAN NOT NULL DEFAULT FALSE,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            created_by_user_id INTEGER NULL,
            published_at TIMESTAMP NULL,
            CONSTRAINT uq_eposone_commercial_policy_version
                UNIQUE (policy_id, version_number)
        )
        """
        if not is_pg:
            ddl = ddl.replace('SERIAL PRIMARY KEY', 'INTEGER PRIMARY KEY AUTOINCREMENT')
            ddl = ddl.replace('BOOLEAN', 'INTEGER')
        _exec(ddl)
        if printfn:
            printfn('+ eposone_commercial_policy_version')
    else:
        cols = {c['name'] for c in inspector.get_columns('eposone_commercial_policy_version')}
        if 'publication_status' not in cols:
            _exec(
                "ALTER TABLE eposone_commercial_policy_version "
                "ADD COLUMN publication_status VARCHAR(16) NOT NULL DEFAULT 'draft'"
            )
            # Backfill: is_current → active; resto draft
            _exec(
                "UPDATE eposone_commercial_policy_version "
                "SET publication_status = CASE WHEN is_current THEN 'active' ELSE 'draft' END"
            )
            if printfn:
                printfn('+ eposone_commercial_policy_version.publication_status')
        if 'published_at' not in cols:
            _exec(
                'ALTER TABLE eposone_commercial_policy_version '
                'ADD COLUMN published_at TIMESTAMP NULL'
            )
            if printfn:
                printfn('+ eposone_commercial_policy_version.published_at')

    if 'eposone_commercial_policy_assignment' not in tables:
        ddl = """
        CREATE TABLE eposone_commercial_policy_assignment (
            id SERIAL PRIMARY KEY,
            organization_id INTEGER NOT NULL
                REFERENCES saas_organization(id) ON DELETE CASCADE,
            policy_type VARCHAR(32) NOT NULL,
            policy_id INTEGER NOT NULL
                REFERENCES eposone_commercial_policy(id) ON DELETE CASCADE,
            policy_version_id INTEGER NULL
                REFERENCES eposone_commercial_policy_version(id) ON DELETE SET NULL,
            scope_type VARCHAR(32) NOT NULL,
            scope_ref VARCHAR(128) NOT NULL,
            active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT uq_eposone_commercial_policy_assignment_scope
                UNIQUE (organization_id, policy_type, scope_type, scope_ref)
        )
        """
        if not is_pg:
            ddl = ddl.replace('SERIAL PRIMARY KEY', 'INTEGER PRIMARY KEY AUTOINCREMENT')
            ddl = ddl.replace('BOOLEAN', 'INTEGER')
        _exec(ddl)
        if printfn:
            printfn('+ eposone_commercial_policy_assignment')

    if 'eposone_commercial_policies_sync_state' not in tables:
        ddl = """
        CREATE TABLE eposone_commercial_policies_sync_state (
            organization_id INTEGER PRIMARY KEY
                REFERENCES saas_organization(id) ON DELETE CASCADE,
            policies_version BIGINT NOT NULL DEFAULT 0,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
        if not is_pg:
            ddl = ddl.replace('BIGINT', 'INTEGER')
        _exec(ddl)
        if printfn:
            printfn('+ eposone_commercial_policies_sync_state')

    with engine.begin() as conn:
        conn.execute(
            text(
                'CREATE INDEX IF NOT EXISTS ix_eposone_cpol_org_type '
                'ON eposone_commercial_policy (organization_id, policy_type)'
            )
        )
        conn.execute(
            text(
                'CREATE INDEX IF NOT EXISTS ix_eposone_cpol_ver_policy '
                'ON eposone_commercial_policy_version (policy_id, is_current)'
            )
        )
        conn.execute(
            text(
                'CREATE INDEX IF NOT EXISTS ix_eposone_cpol_ver_status '
                'ON eposone_commercial_policy_version (policy_id, publication_status)'
            )
        )
        conn.execute(
            text(
                'CREATE INDEX IF NOT EXISTS ix_eposone_cpol_asg_org '
                'ON eposone_commercial_policy_assignment (organization_id, scope_type)'
            )
        )
