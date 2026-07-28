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


def _ensure_saas_module_for_orgs(
    db,
    module_code: str,
    organization_ids: list[int],
    *,
    printfn=None,
) -> None:
    """Activa módulo SaaS opt-in para orgs indicadas (dev / cutover)."""
    from app import SaasModule, SaasOrgModule

    mod = SaasModule.query.filter_by(code=(module_code or '').strip()).first()
    if mod is None:
        return
    mid = int(mod.id)
    for oid in organization_ids:
        row = SaasOrgModule.query.filter_by(organization_id=int(oid), module_id=mid).first()
        if row is None:
            db.session.add(SaasOrgModule(organization_id=int(oid), module_id=mid, enabled=True))
            if printfn:
                printfn(f'+ saas_org_module: org={oid} {module_code} enabled=True')
        elif not row.enabled:
            row.enabled = True
            if printfn:
                printfn(f'* saas_org_module: org={oid} {module_code} enabled=True')
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


def seed_ecertificates_platform_runtime(db, organization_ids: list[int], printfn=None) -> None:
    """Marca ECertificates como plataforma (requiere EEvents + EMembership integrados)."""
    seed_app_platform_runtime(db, 'ecertificates', organization_ids, printfn=printfn)


def seed_eappointments_platform_runtime(db, organization_ids: list[int], printfn=None) -> None:
    """Marca EAppointments como plataforma para orgs indicadas (solo dev / cutover acordado)."""
    seed_app_platform_runtime(db, 'eappointments', organization_ids, printfn=printfn)


def seed_eposone_platform_runtime(db, organization_ids: list[int], printfn=None) -> None:
    """Marca EPosOne como plataforma y habilita módulo SaaS eposone (opt-in)."""
    seed_app_platform_runtime(db, 'eposone', organization_ids, printfn=printfn)
    _ensure_saas_module_for_orgs(db, 'eposone', organization_ids, printfn=printfn)


def seed_epayroll_platform_runtime(db, organization_ids: list[int], printfn=None) -> None:
    """Marca ePlanilla como plataforma, habilita SaaS y suscripción trial (Portal)."""
    from datetime import datetime, timedelta

    seed_app_platform_runtime(db, 'epayroll', organization_ids, printfn=printfn)
    _ensure_saas_module_for_orgs(db, 'epayroll', organization_ids, printfn=printfn)

    if not organization_ids:
        return

    try:
        from nodeone.core.platform.entitlement_service import EntitlementService
        from nodeone.core.platform.subscription_registry import SubscriptionError, SubscriptionRegistry
    except Exception as e:
        if printfn:
            printfn(f'! epayroll trial seed skipped (imports): {e}')
        return

    trial_ends = datetime.utcnow() + timedelta(days=90)
    for oid in organization_ids:
        try:
            SubscriptionRegistry.create_trial(
                int(oid),
                'epayroll',
                trial_ends,
                metadata={'seed': 'platform_trial', 'product': 'eplanilla'},
            )
            if printfn:
                printfn(f'+ ets subscription trial: org={oid} epayroll')
        except SubscriptionError as e:
            if getattr(e, 'code', '') == 'duplicate_active':
                if printfn:
                    printfn(f'= ets subscription already entitled: org={oid} epayroll')
            else:
                if printfn:
                    printfn(f'! ets subscription org={oid} epayroll: {e}')
        except Exception as e:
            if printfn:
                printfn(f'! ets subscription org={oid} epayroll: {e}')
        try:
            EntitlementService.ensure_for_subscription(int(oid), 'epayroll')
            if printfn:
                printfn(f'+ entitlement: org={oid} epayroll')
        except Exception as e:
            if printfn:
                printfn(f'! entitlement org={oid} epayroll: {e}')
