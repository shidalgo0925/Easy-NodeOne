"""DDL idempotente: timezone IANA en saas_organization."""

from __future__ import annotations

from sqlalchemy import inspect, text

DEFAULT_TIMEZONE = 'America/Panama'


def ensure_saas_organization_timezone_column(db, engine, printfn=None) -> None:
    insp = inspect(engine)
    if 'saas_organization' not in insp.get_table_names():
        return
    cols = {c['name'] for c in insp.get_columns('saas_organization')}
    if 'timezone' in cols:
        return
    try:
        db.session.execute(
            text(
                "ALTER TABLE saas_organization ADD COLUMN timezone VARCHAR(64) "
                f"NOT NULL DEFAULT '{DEFAULT_TIMEZONE}'"
            )
        )
        db.session.commit()
        if printfn:
            printfn('+ saas_organization.timezone')
    except Exception as e:
        db.session.rollback()
        # En Dev PG el rol de app a veces no es owner: aplicar como superuser:
        # ALTER TABLE saas_organization ADD COLUMN IF NOT EXISTS timezone VARCHAR(64)
        #   NOT NULL DEFAULT 'America/Panama';
        if printfn:
            printfn(f'! saas_organization.timezone (DDL falló: {e})')
        raise
