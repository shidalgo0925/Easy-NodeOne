"""DDL ADR-EN1-EP1 — money handoff, ops lifecycle, flags TEST."""

from __future__ import annotations

from sqlalchemy import inspect, text


def _add_column(engine, table: str, name: str, pg_type: str, sqlite_type: str, printfn=None) -> None:
    insp = inspect(engine)
    if table not in insp.get_table_names():
        return
    cols = {c['name'] for c in insp.get_columns(table)}
    if name in cols:
        return
    dialect = engine.dialect.name
    ddl_type = pg_type if dialect == 'postgresql' else sqlite_type
    with engine.begin() as conn:
        if dialect == 'postgresql':
            conn.execute(text(f'ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {name} {ddl_type}'))
        else:
            conn.execute(text(f'ALTER TABLE {table} ADD COLUMN {name} {ddl_type}'))
    if printfn:
        printfn(f'+ {table}.{name}')


def ensure_eposone_ops_closure_schema(db, engine, printfn=None) -> None:
    insp = inspect(engine)
    dialect = engine.dialect.name
    tables = set(insp.get_table_names())

    _add_column(
        engine, 'eposone_settings', 'money_handoff_mode',
        "VARCHAR(32) NOT NULL DEFAULT 'SIMPLE'",
        "VARCHAR(32) NOT NULL DEFAULT 'SIMPLE'",
        printfn,
    )
    _add_column(
        engine, 'eposone_settings', 'operational_lifecycle',
        "VARCHAR(32) NOT NULL DEFAULT 'TEST'",
        "VARCHAR(32) NOT NULL DEFAULT 'TEST'",
        printfn,
    )
    _add_column(
        engine, 'eposone_settings', 'test_session_id',
        'VARCHAR(80)',
        'VARCHAR(80)',
        printfn,
    )

    for table, cols in (
        ('eposone_order', (
            ('is_test', 'BOOLEAN NOT NULL DEFAULT FALSE', 'INTEGER NOT NULL DEFAULT 0'),
            ('test_session_id', 'VARCHAR(80)', 'VARCHAR(80)'),
            ('charged_by_user_ref', 'VARCHAR(64)', 'VARCHAR(64)'),
            ('charged_at', 'TIMESTAMP WITHOUT TIME ZONE', 'DATETIME'),
        )),
        ('core_commercial_order', (
            ('is_test', 'BOOLEAN NOT NULL DEFAULT FALSE', 'INTEGER NOT NULL DEFAULT 0'),
            ('test_session_id', 'VARCHAR(80)', 'VARCHAR(80)'),
            ('created_by_user_id', 'INTEGER', 'INTEGER'),
            ('charged_by_cashier_contact_id', 'INTEGER', 'INTEGER'),
            ('charged_at', 'TIMESTAMP WITHOUT TIME ZONE', 'DATETIME'),
            ('cash_shift_id', 'INTEGER', 'INTEGER'),
        )),
        ('core_cash_shift', (
            ('is_test', 'BOOLEAN NOT NULL DEFAULT FALSE', 'INTEGER NOT NULL DEFAULT 0'),
            ('test_session_id', 'VARCHAR(80)', 'VARCHAR(80)'),
        )),
        ('core_stock_movement', (
            ('is_test', 'BOOLEAN NOT NULL DEFAULT FALSE', 'INTEGER NOT NULL DEFAULT 0'),
            ('test_session_id', 'VARCHAR(80)', 'VARCHAR(80)'),
        )),
    ):
        for name, pg_t, lite_t in cols:
            _add_column(engine, table, name, pg_t, lite_t, printfn)

    tables = set(inspect(engine).get_table_names())
    if 'eposone_money_handoff' not in tables:
        if dialect == 'postgresql':
            ddl = """
            CREATE TABLE IF NOT EXISTS eposone_money_handoff (
                id SERIAL PRIMARY KEY,
                organization_id INTEGER NOT NULL REFERENCES saas_organization(id) ON DELETE CASCADE,
                client_handoff_id VARCHAR(80) NOT NULL,
                cashier_contact_id INTEGER,
                cashier_name VARCHAR(120),
                shift_id INTEGER,
                register_ref VARCHAR(64),
                expected_amount DOUBLE PRECISION NOT NULL DEFAULT 0,
                received_amount DOUBLE PRECISION,
                difference_amount DOUBLE PRECISION,
                other_tender_amount DOUBLE PRECISION NOT NULL DEFAULT 0,
                order_refs_json TEXT,
                status VARCHAR(40) NOT NULL DEFAULT 'PENDING_HANDOFF',
                received_by_user_id INTEGER,
                received_by_label VARCHAR(160),
                received_at TIMESTAMP WITHOUT TIME ZONE,
                reversed_by_user_id INTEGER,
                reversed_by_label VARCHAR(160),
                reversed_at TIMESTAMP WITHOUT TIME ZONE,
                reverse_reason VARCHAR(400),
                is_test BOOLEAN NOT NULL DEFAULT FALSE,
                test_session_id VARCHAR(80),
                created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (NOW() AT TIME ZONE 'utc'),
                updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (NOW() AT TIME ZONE 'utc'),
                CONSTRAINT uq_eposone_money_handoff_client UNIQUE (organization_id, client_handoff_id)
            );
            CREATE INDEX IF NOT EXISTS ix_eposone_money_handoff_org ON eposone_money_handoff (organization_id);
            CREATE INDEX IF NOT EXISTS ix_eposone_money_handoff_status ON eposone_money_handoff (status);
            """
        else:
            ddl = """
            CREATE TABLE IF NOT EXISTS eposone_money_handoff (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                organization_id INTEGER NOT NULL,
                client_handoff_id VARCHAR(80) NOT NULL,
                cashier_contact_id INTEGER,
                cashier_name VARCHAR(120),
                shift_id INTEGER,
                register_ref VARCHAR(64),
                expected_amount FLOAT NOT NULL DEFAULT 0,
                received_amount FLOAT,
                difference_amount FLOAT,
                other_tender_amount FLOAT NOT NULL DEFAULT 0,
                order_refs_json TEXT,
                status VARCHAR(40) NOT NULL DEFAULT 'PENDING_HANDOFF',
                received_by_user_id INTEGER,
                received_by_label VARCHAR(160),
                received_at DATETIME,
                reversed_by_user_id INTEGER,
                reversed_by_label VARCHAR(160),
                reversed_at DATETIME,
                reverse_reason VARCHAR(400),
                is_test INTEGER NOT NULL DEFAULT 0,
                test_session_id VARCHAR(80),
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (organization_id, client_handoff_id)
            );
            """
        with engine.begin() as conn:
            for stmt in ddl.strip().split(';'):
                s = stmt.strip()
                if s:
                    conn.execute(text(s))
        if printfn:
            printfn('eposone_money_handoff')

    tables = set(inspect(engine).get_table_names())
    if 'eposone_ops_audit_event' not in tables:
        if dialect == 'postgresql':
            ddl = """
            CREATE TABLE IF NOT EXISTS eposone_ops_audit_event (
                id SERIAL PRIMARY KEY,
                organization_id INTEGER NOT NULL REFERENCES saas_organization(id) ON DELETE CASCADE,
                event_type VARCHAR(64) NOT NULL,
                authorized_by_user_id INTEGER,
                authorized_by_label VARCHAR(160),
                payload_json TEXT,
                created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (NOW() AT TIME ZONE 'utc')
            );
            CREATE INDEX IF NOT EXISTS ix_eposone_ops_audit_org ON eposone_ops_audit_event (organization_id);
            """
        else:
            ddl = """
            CREATE TABLE IF NOT EXISTS eposone_ops_audit_event (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                organization_id INTEGER NOT NULL,
                event_type VARCHAR(64) NOT NULL,
                authorized_by_user_id INTEGER,
                authorized_by_label VARCHAR(160),
                payload_json TEXT,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            """
        with engine.begin() as conn:
            for stmt in ddl.strip().split(';'):
                s = stmt.strip()
                if s:
                    conn.execute(text(s))
        if printfn:
            printfn('eposone_ops_audit_event')
