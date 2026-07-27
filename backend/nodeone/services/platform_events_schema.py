"""DDL idempotente — platform_domain_event (outbox Etapa 8)."""

from __future__ import annotations

from sqlalchemy import inspect, text


def ensure_platform_events_schema(db, engine, printfn=None) -> None:
    insp = inspect(engine)
    if 'platform_domain_event' in insp.get_table_names():
        return

    dialect = engine.dialect.name
    if dialect == 'postgresql':
        ddl = """
        CREATE TABLE IF NOT EXISTS platform_domain_event (
            id SERIAL PRIMARY KEY,
            organization_id INTEGER NOT NULL REFERENCES saas_organization(id) ON DELETE CASCADE,
            event_type VARCHAR(128) NOT NULL,
            source_app_id VARCHAR(64) NOT NULL DEFAULT 'core',
            payload JSONB NOT NULL DEFAULT '{}',
            status VARCHAR(32) NOT NULL DEFAULT 'pending',
            error_message TEXT,
            created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (NOW() AT TIME ZONE 'utc'),
            dispatched_at TIMESTAMP WITHOUT TIME ZONE
        );
        CREATE INDEX IF NOT EXISTS ix_platform_domain_event_org_status
            ON platform_domain_event (organization_id, status);
        CREATE INDEX IF NOT EXISTS ix_platform_domain_event_type
            ON platform_domain_event (event_type);
        """
    else:
        ddl = """
        CREATE TABLE IF NOT EXISTS platform_domain_event (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            organization_id INTEGER NOT NULL,
            event_type VARCHAR(128) NOT NULL,
            source_app_id VARCHAR(64) NOT NULL DEFAULT 'core',
            payload JSON NOT NULL DEFAULT '{}',
            status VARCHAR(32) NOT NULL DEFAULT 'pending',
            error_message TEXT,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            dispatched_at DATETIME
        );
        CREATE INDEX IF NOT EXISTS ix_platform_domain_event_org_status
            ON platform_domain_event (organization_id, status);
        CREATE INDEX IF NOT EXISTS ix_platform_domain_event_type
            ON platform_domain_event (event_type);
        """

    with engine.begin() as conn:
        for stmt in ddl.strip().split(';'):
            s = stmt.strip()
            if s:
                conn.execute(text(s))
    if printfn:
        printfn('platform_domain_event: tabla creada')
