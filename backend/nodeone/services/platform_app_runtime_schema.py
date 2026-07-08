"""DDL idempotente — platform_org_app_runtime."""

from __future__ import annotations

from sqlalchemy import inspect, text


def ensure_platform_app_runtime_schema(db, engine, printfn=None) -> None:
    insp = inspect(engine)
    if 'platform_org_app_runtime' in insp.get_table_names():
        return

    dialect = engine.dialect.name
    if dialect == 'postgresql':
        ddl = """
        CREATE TABLE IF NOT EXISTS platform_org_app_runtime (
            id SERIAL PRIMARY KEY,
            organization_id INTEGER NOT NULL REFERENCES saas_organization(id) ON DELETE CASCADE,
            app_id VARCHAR(64) NOT NULL,
            runtime VARCHAR(32) NOT NULL DEFAULT 'legacy',
            updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT (NOW() AT TIME ZONE 'utc'),
            CONSTRAINT uq_platform_org_app_runtime UNIQUE (organization_id, app_id)
        );
        CREATE INDEX IF NOT EXISTS ix_platform_org_app_runtime_org
            ON platform_org_app_runtime (organization_id);
        """
    else:
        ddl = """
        CREATE TABLE IF NOT EXISTS platform_org_app_runtime (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            organization_id INTEGER NOT NULL,
            app_id VARCHAR(64) NOT NULL,
            runtime VARCHAR(32) NOT NULL DEFAULT 'legacy',
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (organization_id, app_id)
        );
        """

    with engine.begin() as conn:
        for stmt in ddl.strip().split(';'):
            s = stmt.strip()
            if s:
                conn.execute(text(s))
    if printfn:
        printfn('platform_org_app_runtime: tabla creada')


def seed_emembership_platform_runtime(db, organization_ids: list[int], printfn=None) -> None:
    """Marca EMembership como plataforma para orgs indicadas (solo dev / cutover acordado)."""
    from models.platform_app import (
        APP_RUNTIME_PLATFORM,
        PlatformOrgAppRuntime,
    )

    for oid in organization_ids:
        row = PlatformOrgAppRuntime.query.filter_by(organization_id=int(oid), app_id='emembership').first()
        if row is None:
            db.session.add(
                PlatformOrgAppRuntime(
                    organization_id=int(oid),
                    app_id='emembership',
                    runtime=APP_RUNTIME_PLATFORM,
                )
            )
            if printfn:
                printfn(f'+ platform_org_app_runtime: org={oid} emembership → plataforma')
        elif row.runtime != APP_RUNTIME_PLATFORM:
            row.runtime = APP_RUNTIME_PLATFORM
            if printfn:
                printfn(f'* platform_org_app_runtime: org={oid} emembership → plataforma')
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
