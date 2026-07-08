"""DDL idempotente — sync offline Etapa 13."""

from __future__ import annotations

from sqlalchemy import inspect, text


def _column_names(insp, table: str) -> set[str]:
    try:
        return {c['name'] for c in insp.get_columns(table)}
    except Exception:
        return set()


def ensure_platform_sync_schema(db, engine, printfn=None) -> None:
    insp = inspect(engine)
    dialect = engine.dialect.name

    if 'platform_sync_operation' not in insp.get_table_names():
        if dialect == 'postgresql':
            op_ddl = """
            CREATE TABLE IF NOT EXISTS platform_sync_operation (
                id SERIAL PRIMARY KEY,
                organization_id INTEGER NOT NULL REFERENCES saas_organization(id) ON DELETE CASCADE,
                client_id VARCHAR(128) NOT NULL DEFAULT 'default',
                idempotency_key VARCHAR(128) NOT NULL,
                operation_type VARCHAR(64) NOT NULL,
                entity_type VARCHAR(64),
                entity_ref VARCHAR(128),
                payload JSONB NOT NULL DEFAULT '{}',
                base_version INTEGER,
                status VARCHAR(32) NOT NULL DEFAULT 'pending',
                conflict_reason TEXT,
                retry_count INTEGER NOT NULL DEFAULT 0,
                next_retry_at TIMESTAMP WITHOUT TIME ZONE,
                error_message TEXT,
                created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (NOW() AT TIME ZONE 'utc'),
                applied_at TIMESTAMP WITHOUT TIME ZONE,
                CONSTRAINT uq_platform_sync_op_idempotency
                    UNIQUE (organization_id, client_id, idempotency_key)
            );
            CREATE INDEX IF NOT EXISTS ix_platform_sync_op_org_status
                ON platform_sync_operation (organization_id, status);
            """
        else:
            op_ddl = """
            CREATE TABLE IF NOT EXISTS platform_sync_operation (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                organization_id INTEGER NOT NULL,
                client_id VARCHAR(128) NOT NULL DEFAULT 'default',
                idempotency_key VARCHAR(128) NOT NULL,
                operation_type VARCHAR(64) NOT NULL,
                entity_type VARCHAR(64),
                entity_ref VARCHAR(128),
                payload JSON NOT NULL DEFAULT '{}',
                base_version INTEGER,
                status VARCHAR(32) NOT NULL DEFAULT 'pending',
                conflict_reason TEXT,
                retry_count INTEGER NOT NULL DEFAULT 0,
                next_retry_at DATETIME,
                error_message TEXT,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                applied_at DATETIME,
                UNIQUE (organization_id, client_id, idempotency_key)
            );
            CREATE INDEX IF NOT EXISTS ix_platform_sync_op_org_status
                ON platform_sync_operation (organization_id, status);
            """
        with engine.begin() as conn:
            for stmt in op_ddl.strip().split(';'):
                s = stmt.strip()
                if s:
                    conn.execute(text(s))
        if printfn:
            printfn('platform_sync_operation: tabla creada')

    if 'platform_sync_cursor' not in insp.get_table_names():
        if dialect == 'postgresql':
            cur_ddl = """
            CREATE TABLE IF NOT EXISTS platform_sync_cursor (
                id SERIAL PRIMARY KEY,
                organization_id INTEGER NOT NULL REFERENCES saas_organization(id) ON DELETE CASCADE,
                client_id VARCHAR(128) NOT NULL DEFAULT 'default',
                domain VARCHAR(64) NOT NULL,
                cursor_value VARCHAR(128) NOT NULL DEFAULT '0',
                updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (NOW() AT TIME ZONE 'utc'),
                CONSTRAINT uq_platform_sync_cursor_domain
                    UNIQUE (organization_id, client_id, domain)
            );
            """
        else:
            cur_ddl = """
            CREATE TABLE IF NOT EXISTS platform_sync_cursor (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                organization_id INTEGER NOT NULL,
                client_id VARCHAR(128) NOT NULL DEFAULT 'default',
                domain VARCHAR(64) NOT NULL,
                cursor_value VARCHAR(128) NOT NULL DEFAULT '0',
                updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (organization_id, client_id, domain)
            );
            """
        with engine.begin() as conn:
            for stmt in cur_ddl.strip().split(';'):
                s = stmt.strip()
                if s:
                    conn.execute(text(s))
        if printfn:
            printfn('platform_sync_cursor: tabla creada')

    if 'platform_domain_event' in insp.get_table_names():
        cols = _column_names(insp, 'platform_domain_event')
        alters: list[str] = []
        if 'retry_count' not in cols:
            alters.append('ALTER TABLE platform_domain_event ADD COLUMN retry_count INTEGER NOT NULL DEFAULT 0')
        if 'next_retry_at' not in cols:
            alters.append('ALTER TABLE platform_domain_event ADD COLUMN next_retry_at TIMESTAMP')
        if dialect != 'postgresql' and 'next_retry_at' not in cols:
            alters[-1] = 'ALTER TABLE platform_domain_event ADD COLUMN next_retry_at DATETIME'
        if alters:
            with engine.begin() as conn:
                for stmt in alters:
                    conn.execute(text(stmt))
            if printfn:
                printfn('platform_domain_event: columnas retry añadidas')
