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


def ensure_cash_shift_custody_schema(db, engine, printfn=None) -> None:
    """ADR-036: custodian columns + handover table."""
    inspector = inspect(engine)
    dialect = engine.dialect.name
    if 'core_cash_shift' not in inspector.get_table_names():
        return
    cols = {c['name'] for c in inspector.get_columns('core_cash_shift')}
    with engine.begin() as conn:
        if 'custodian_cashier_contact_id' not in cols:
            if dialect == 'postgresql':
                conn.execute(
                    text(
                        'ALTER TABLE core_cash_shift '
                        'ADD COLUMN IF NOT EXISTS custodian_cashier_contact_id INTEGER'
                    )
                )
            else:
                conn.execute(
                    text(
                        'ALTER TABLE core_cash_shift '
                        'ADD COLUMN custodian_cashier_contact_id INTEGER'
                    )
                )
            if printfn:
                printfn('+ core_cash_shift.custodian_cashier_contact_id')
        if 'custodian_cashier_name' not in cols:
            if dialect == 'postgresql':
                conn.execute(
                    text(
                        'ALTER TABLE core_cash_shift '
                        'ADD COLUMN IF NOT EXISTS custodian_cashier_name VARCHAR(120)'
                    )
                )
            else:
                conn.execute(
                    text(
                        'ALTER TABLE core_cash_shift '
                        'ADD COLUMN custodian_cashier_name VARCHAR(120)'
                    )
                )
            if printfn:
                printfn('+ core_cash_shift.custodian_cashier_name')
        # Backfill: custodio = cajero del turno cuando falta
        conn.execute(
            text(
                'UPDATE core_cash_shift SET custodian_cashier_contact_id = cashier_contact_id '
                'WHERE custodian_cashier_contact_id IS NULL AND cashier_contact_id IS NOT NULL'
            )
        )
        conn.execute(
            text(
                'UPDATE core_cash_shift SET custodian_cashier_name = cashier_name '
                'WHERE custodian_cashier_name IS NULL AND cashier_name IS NOT NULL'
            )
        )

    tables = inspector.get_table_names()
    if 'core_cash_custody_handover' in tables:
        return
    with engine.begin() as conn:
        if dialect == 'postgresql':
            conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS core_cash_custody_handover (
                        id SERIAL PRIMARY KEY,
                        organization_id INTEGER NOT NULL REFERENCES saas_organization(id) ON DELETE CASCADE,
                        shift_id INTEGER NOT NULL REFERENCES core_cash_shift(id) ON DELETE CASCADE,
                        from_cashier_contact_id INTEGER,
                        to_cashier_contact_id INTEGER,
                        status VARCHAR(32) NOT NULL DEFAULT 'pending',
                        notes VARCHAR(500),
                        offered_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (NOW() AT TIME ZONE 'utc'),
                        resolved_at TIMESTAMP WITHOUT TIME ZONE
                    )
                    """
                )
            )
            conn.execute(
                text(
                    'CREATE INDEX IF NOT EXISTS ix_cash_custody_hov_shift '
                    'ON core_cash_custody_handover (shift_id)'
                )
            )
            conn.execute(
                text(
                    'CREATE INDEX IF NOT EXISTS ix_cash_custody_hov_org '
                    'ON core_cash_custody_handover (organization_id)'
                )
            )
        else:
            conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS core_cash_custody_handover (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        organization_id INTEGER NOT NULL,
                        shift_id INTEGER NOT NULL,
                        from_cashier_contact_id INTEGER,
                        to_cashier_contact_id INTEGER,
                        status VARCHAR(32) NOT NULL DEFAULT 'pending',
                        notes VARCHAR(500),
                        offered_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        resolved_at DATETIME
                    )
                    """
                )
            )
    if printfn:
        printfn('+ core_cash_custody_handover')


def ensure_cash_operation_mode_settings_schema(db, engine, printfn=None) -> None:
    """ADR-036: eposone_settings.cash_operation_mode."""
    inspector = inspect(engine)
    if 'eposone_settings' not in inspector.get_table_names():
        return
    cols = {c['name'] for c in inspector.get_columns('eposone_settings')}
    if 'cash_operation_mode' in cols:
        return
    dialect = engine.dialect.name
    with engine.begin() as conn:
        if dialect == 'postgresql':
            conn.execute(
                text(
                    "ALTER TABLE eposone_settings "
                    "ADD COLUMN IF NOT EXISTS cash_operation_mode VARCHAR(32) NOT NULL DEFAULT 'SIMPLE'"
                )
            )
        else:
            conn.execute(
                text(
                    "ALTER TABLE eposone_settings "
                    "ADD COLUMN cash_operation_mode VARCHAR(32) NOT NULL DEFAULT 'SIMPLE'"
                )
            )
    if printfn:
        printfn('+ eposone_settings.cash_operation_mode')
