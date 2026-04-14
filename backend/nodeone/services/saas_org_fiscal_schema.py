"""DDL idempotente para datos fiscales en saas_organization."""

from __future__ import annotations

from sqlalchemy import inspect, text


def ensure_saas_organization_fiscal_columns(db, engine, printfn=None) -> None:
    insp = inspect(engine)
    if 'saas_organization' not in insp.get_table_names():
        return
    cols = {c['name'] for c in insp.get_columns('saas_organization')}

    defs = [
        ('legal_name', 'VARCHAR(200)'),
        ('tax_id', 'VARCHAR(80)'),
        ('tax_regime', 'VARCHAR(120)'),
        ('fiscal_address', 'VARCHAR(255)'),
        ('fiscal_city', 'VARCHAR(120)'),
        ('fiscal_state', 'VARCHAR(120)'),
        ('fiscal_country', 'VARCHAR(120)'),
        ('fiscal_phone', 'VARCHAR(60)'),
        ('fiscal_email', 'VARCHAR(200)'),
    ]

    for col, col_type in defs:
        if col in cols:
            continue
        try:
            db.session.execute(text(f'ALTER TABLE saas_organization ADD COLUMN {col} {col_type}'))
            db.session.commit()
            if printfn:
                printfn(f'+ saas_organization.{col}')
        except Exception:
            db.session.rollback()
            raise
