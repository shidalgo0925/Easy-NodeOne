"""DDL idempotente: registration_policy en saas_organization."""

from __future__ import annotations

from sqlalchemy import inspect, text


def ensure_saas_organization_registration_policy_column(db, engine, printfn=None) -> None:
    insp = inspect(engine)
    if 'saas_organization' not in insp.get_table_names():
        return
    cols = {c['name'] for c in insp.get_columns('saas_organization')}
    if 'registration_policy' in cols:
        return
    try:
        db.session.execute(
            text(
                "ALTER TABLE saas_organization ADD COLUMN registration_policy VARCHAR(30) "
                "NOT NULL DEFAULT 'free_registration'"
            )
        )
        db.session.commit()
        if printfn:
            printfn('+ saas_organization.registration_policy')
    except Exception:
        db.session.rollback()
        raise
