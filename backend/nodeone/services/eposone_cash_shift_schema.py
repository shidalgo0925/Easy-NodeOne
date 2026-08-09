"""DDL idempotente: client_shift_id en core_cash_shift (idempotencia POS)."""

from __future__ import annotations

from sqlalchemy import inspect, text


def ensure_cash_shift_client_id_schema(db, engine, printfn=None) -> None:
    inspector = inspect(engine)
    if 'core_cash_shift' not in inspector.get_table_names():
        return
    cols = {c['name'] for c in inspector.get_columns('core_cash_shift')}
    if 'client_shift_id' not in cols:
        with engine.begin() as conn:
            conn.execute(
                text('ALTER TABLE core_cash_shift ADD COLUMN client_shift_id VARCHAR(64)')
            )
        if printfn:
            printfn('+ core_cash_shift.client_shift_id')

    with engine.begin() as conn:
        conn.execute(
            text(
                'CREATE INDEX IF NOT EXISTS ix_core_cash_shift_client_shift_id '
                'ON core_cash_shift (client_shift_id)'
            )
        )
        # Unique por org cuando hay client_shift_id (PostgreSQL partial index)
        if engine.dialect.name == 'postgresql':
            conn.execute(
                text(
                    'CREATE UNIQUE INDEX IF NOT EXISTS '
                    'uq_core_cash_shift_org_client_shift_id '
                    'ON core_cash_shift (organization_id, client_shift_id) '
                    'WHERE client_shift_id IS NOT NULL'
                )
            )


def ensure_cash_shift_correction_schema(db, engine, printfn=None) -> None:
    """DDL idempotente: correction_json en core_cash_shift (fix de cierre BO)."""
    inspector = inspect(engine)
    if 'core_cash_shift' not in inspector.get_table_names():
        return
    cols = {c['name'] for c in inspector.get_columns('core_cash_shift')}
    if 'correction_json' in cols:
        return
    with engine.begin() as conn:
        conn.execute(text('ALTER TABLE core_cash_shift ADD COLUMN correction_json TEXT'))
    if printfn:
        printfn('+ core_cash_shift.correction_json')
