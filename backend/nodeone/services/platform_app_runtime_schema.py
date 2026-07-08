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


def seed_app_platform_runtime(
    db,
    app_id: str,
    organization_ids: list[int],
    *,
    runtime: str = 'plataforma',
    printfn=None,
) -> None:
    """Marca una app como integrada en plataforma para las orgs indicadas."""
    from models.platform_app import APP_RUNTIME_VALUES, PlatformOrgAppRuntime

    aid = (app_id or '').strip().lower()
    rt = (runtime or 'plataforma').strip().lower()
    if rt not in APP_RUNTIME_VALUES:
        rt = 'plataforma'

    for oid in organization_ids:
        row = PlatformOrgAppRuntime.query.filter_by(organization_id=int(oid), app_id=aid).first()
        if row is None:
            db.session.add(
                PlatformOrgAppRuntime(
                    organization_id=int(oid),
                    app_id=aid,
                    runtime=rt,
                )
            )
            if printfn:
                printfn(f'+ platform_org_app_runtime: org={oid} {aid} → {rt}')
        elif row.runtime != rt:
            row.runtime = rt
            if printfn:
                printfn(f'* platform_org_app_runtime: org={oid} {aid} → {rt}')
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise


def seed_emembership_platform_runtime(db, organization_ids: list[int], printfn=None) -> None:
    """Marca EMembership como plataforma para orgs indicadas (solo dev / cutover acordado)."""
    seed_app_platform_runtime(db, 'emembership', organization_ids, printfn=printfn)


def seed_ecrm_platform_runtime(db, organization_ids: list[int], printfn=None) -> None:
    """Marca ECRM como plataforma para orgs indicadas (solo dev / cutover acordado)."""
    seed_app_platform_runtime(db, 'ecrm', organization_ids, printfn=printfn)


def seed_eevents_platform_runtime(db, organization_ids: list[int], printfn=None) -> None:
    """Marca EEvents como plataforma para orgs indicadas (solo dev / cutover acordado)."""
    seed_app_platform_runtime(db, 'eevents', organization_ids, printfn=printfn)
