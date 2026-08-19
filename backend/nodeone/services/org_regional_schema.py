"""DDL idempotente: organization_regional_settings."""

from __future__ import annotations

from sqlalchemy import inspect, text


def ensure_organization_regional_settings_schema(db, engine, printfn=None) -> None:
    from models.org_regional import OrganizationRegionalSettings

    try:
        OrganizationRegionalSettings.__table__.create(engine, checkfirst=True)
    except Exception as ex:
        db.session.rollback()
        if printfn:
            printfn(f'! organization_regional_settings create: {ex}')
        return
    insp = inspect(engine)
    if 'organization_regional_settings' not in insp.get_table_names():
        if printfn:
            printfn('! organization_regional_settings ausente (¿owner DDL?)')
        return
    if printfn:
        printfn('organization_regional_settings: tabla lista')
    _ = text  # keep import for future ALTERs
