"""DDL — Hito 3 Order Domain (eposone_order*)."""

from __future__ import annotations

from sqlalchemy import inspect, text


def _exec(engine, ddl: str) -> None:
    with engine.begin() as conn:
        for stmt in ddl.strip().split(';'):
            s = stmt.strip()
            if s:
                conn.execute(text(s))


def ensure_eposone_order_schema(db, engine, printfn=None) -> None:
    insp = inspect(engine)
    existing = set(insp.get_table_names())
    is_pg = engine.dialect.name == 'postgresql'

    def log(msg: str) -> None:
        if printfn:
            printfn(msg)

    if 'eposone_order' not in existing:
        if is_pg:
            _exec(
                engine,
                """
                CREATE TABLE IF NOT EXISTS eposone_order (
                    id SERIAL PRIMARY KEY,
                    organization_id INTEGER NOT NULL,
                    local_number VARCHAR(64),
                    en1_number VARCHAR(64) NOT NULL,
                    branch_ref VARCHAR(64),
                    pos_ref VARCHAR(64),
                    register_ref VARCHAR(64),
                    owner_device_uuid VARCHAR(64) NOT NULL,
                    owner_pos_ref VARCHAR(64),
                    user_ref VARCHAR(64),
                    customer_ref VARCHAR(64),
                    table_ref VARCHAR(64),
                    status VARCHAR(32) NOT NULL DEFAULT 'open',
                    payment_status VARCHAR(32) NOT NULL DEFAULT 'unpaid',
                    financially_closed BOOLEAN NOT NULL DEFAULT FALSE,
                    subtotal DOUBLE PRECISION NOT NULL DEFAULT 0,
                    tax DOUBLE PRECISION NOT NULL DEFAULT 0,
                    discount DOUBLE PRECISION NOT NULL DEFAULT 0,
                    tip DOUBLE PRECISION NOT NULL DEFAULT 0,
                    total DOUBLE PRECISION NOT NULL DEFAULT 0,
                    amount_paid DOUBLE PRECISION NOT NULL DEFAULT 0,
                    notes TEXT,
                    parent_order_id INTEGER REFERENCES eposone_order(id) ON DELETE SET NULL,
                    opened_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (NOW() AT TIME ZONE 'utc'),
                    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (NOW() AT TIME ZONE 'utc'),
                    CONSTRAINT uq_eposone_order_en1_number UNIQUE (organization_id, en1_number)
                );
                CREATE INDEX IF NOT EXISTS ix_eposone_order_org ON eposone_order (organization_id);
                CREATE INDEX IF NOT EXISTS ix_eposone_order_owner ON eposone_order (owner_device_uuid);
                CREATE INDEX IF NOT EXISTS ix_eposone_order_table ON eposone_order (table_ref);
                CREATE INDEX IF NOT EXISTS ix_eposone_order_en1 ON eposone_order (en1_number);
                """,
            )
        else:
            _exec(
                engine,
                """
                CREATE TABLE IF NOT EXISTS eposone_order (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    organization_id INTEGER NOT NULL,
                    local_number VARCHAR(64),
                    en1_number VARCHAR(64) NOT NULL,
                    branch_ref VARCHAR(64),
                    pos_ref VARCHAR(64),
                    register_ref VARCHAR(64),
                    owner_device_uuid VARCHAR(64) NOT NULL,
                    owner_pos_ref VARCHAR(64),
                    user_ref VARCHAR(64),
                    customer_ref VARCHAR(64),
                    table_ref VARCHAR(64),
                    status VARCHAR(32) NOT NULL DEFAULT 'open',
                    payment_status VARCHAR(32) NOT NULL DEFAULT 'unpaid',
                    financially_closed INTEGER NOT NULL DEFAULT 0,
                    subtotal FLOAT NOT NULL DEFAULT 0,
                    tax FLOAT NOT NULL DEFAULT 0,
                    discount FLOAT NOT NULL DEFAULT 0,
                    tip FLOAT NOT NULL DEFAULT 0,
                    total FLOAT NOT NULL DEFAULT 0,
                    amount_paid FLOAT NOT NULL DEFAULT 0,
                    notes TEXT,
                    parent_order_id INTEGER,
                    opened_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE (organization_id, en1_number)
                );
                """,
            )
        log('eposone_order: tabla creada')

    if 'eposone_order_item' not in set(inspect(engine).get_table_names()):
        if is_pg:
            _exec(
                engine,
                """
                CREATE TABLE IF NOT EXISTS eposone_order_item (
                    id SERIAL PRIMARY KEY,
                    order_id INTEGER NOT NULL REFERENCES eposone_order(id) ON DELETE CASCADE,
                    line_ref VARCHAR(64) NOT NULL,
                    product_ref VARCHAR(128) NOT NULL,
                    qty DOUBLE PRECISION NOT NULL DEFAULT 1,
                    unit_price DOUBLE PRECISION NOT NULL DEFAULT 0,
                    tax DOUBLE PRECISION NOT NULL DEFAULT 0,
                    discount DOUBLE PRECISION NOT NULL DEFAULT 0,
                    notes TEXT,
                    line_status VARCHAR(32) NOT NULL DEFAULT 'pending'
                );
                CREATE INDEX IF NOT EXISTS ix_eposone_order_item_order ON eposone_order_item (order_id);
                """,
            )
        else:
            _exec(
                engine,
                """
                CREATE TABLE IF NOT EXISTS eposone_order_item (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    order_id INTEGER NOT NULL,
                    line_ref VARCHAR(64) NOT NULL,
                    product_ref VARCHAR(128) NOT NULL,
                    qty FLOAT NOT NULL DEFAULT 1,
                    unit_price FLOAT NOT NULL DEFAULT 0,
                    tax FLOAT NOT NULL DEFAULT 0,
                    discount FLOAT NOT NULL DEFAULT 0,
                    notes TEXT,
                    line_status VARCHAR(32) NOT NULL DEFAULT 'pending'
                );
                """,
            )
        log('eposone_order_item: tabla creada')

    if 'eposone_order_payment' not in set(inspect(engine).get_table_names()):
        if is_pg:
            _exec(
                engine,
                """
                CREATE TABLE IF NOT EXISTS eposone_order_payment (
                    id SERIAL PRIMARY KEY,
                    order_id INTEGER NOT NULL REFERENCES eposone_order(id) ON DELETE CASCADE,
                    payment_ref VARCHAR(64) NOT NULL,
                    amount DOUBLE PRECISION NOT NULL DEFAULT 0,
                    method VARCHAR(32) NOT NULL DEFAULT 'cash',
                    kind VARCHAR(32) NOT NULL DEFAULT 'payment',
                    currency VARCHAR(8) NOT NULL DEFAULT 'USD',
                    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (NOW() AT TIME ZONE 'utc')
                );
                CREATE INDEX IF NOT EXISTS ix_eposone_order_payment_order ON eposone_order_payment (order_id);
                """,
            )
        else:
            _exec(
                engine,
                """
                CREATE TABLE IF NOT EXISTS eposone_order_payment (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    order_id INTEGER NOT NULL,
                    payment_ref VARCHAR(64) NOT NULL,
                    amount FLOAT NOT NULL DEFAULT 0,
                    method VARCHAR(32) NOT NULL DEFAULT 'cash',
                    kind VARCHAR(32) NOT NULL DEFAULT 'payment',
                    currency VARCHAR(8) NOT NULL DEFAULT 'USD',
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                """,
            )
        log('eposone_order_payment: tabla creada')

    if 'eposone_order_event' not in set(inspect(engine).get_table_names()):
        if is_pg:
            _exec(
                engine,
                """
                CREATE TABLE IF NOT EXISTS eposone_order_event (
                    id SERIAL PRIMARY KEY,
                    order_id INTEGER NOT NULL REFERENCES eposone_order(id) ON DELETE CASCADE,
                    organization_id INTEGER NOT NULL,
                    event_id VARCHAR(64) NOT NULL,
                    type VARCHAR(64) NOT NULL,
                    sequence INTEGER NOT NULL DEFAULT 1,
                    occurred_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (NOW() AT TIME ZONE 'utc'),
                    actor_user_ref VARCHAR(64),
                    actor_device_uuid VARCHAR(64),
                    payload_json TEXT,
                    CONSTRAINT uq_eposone_order_event_id UNIQUE (organization_id, event_id)
                );
                CREATE INDEX IF NOT EXISTS ix_eposone_order_event_order ON eposone_order_event (order_id);
                CREATE INDEX IF NOT EXISTS ix_eposone_order_event_org ON eposone_order_event (organization_id);
                """,
            )
        else:
            _exec(
                engine,
                """
                CREATE TABLE IF NOT EXISTS eposone_order_event (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    order_id INTEGER NOT NULL,
                    organization_id INTEGER NOT NULL,
                    event_id VARCHAR(64) NOT NULL,
                    type VARCHAR(64) NOT NULL,
                    sequence INTEGER NOT NULL DEFAULT 1,
                    occurred_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    actor_user_ref VARCHAR(64),
                    actor_device_uuid VARCHAR(64),
                    payload_json TEXT,
                    UNIQUE (organization_id, event_id)
                );
                """,
            )
        log('eposone_order_event: tabla creada')

    if 'eposone_order_cancellation' not in set(inspect(engine).get_table_names()):
        if is_pg:
            _exec(
                engine,
                """
                CREATE TABLE IF NOT EXISTS eposone_order_cancellation (
                    id SERIAL PRIMARY KEY,
                    order_id INTEGER NOT NULL REFERENCES eposone_order(id) ON DELETE CASCADE,
                    reason TEXT NOT NULL,
                    user_ref VARCHAR(64),
                    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (NOW() AT TIME ZONE 'utc')
                );
                CREATE INDEX IF NOT EXISTS ix_eposone_order_cancel_order ON eposone_order_cancellation (order_id);
                """,
            )
        else:
            _exec(
                engine,
                """
                CREATE TABLE IF NOT EXISTS eposone_order_cancellation (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    order_id INTEGER NOT NULL,
                    reason TEXT NOT NULL,
                    user_ref VARCHAR(64),
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                """,
            )
        log('eposone_order_cancellation: tabla creada')

    if 'eposone_order_return' not in set(inspect(engine).get_table_names()):
        if is_pg:
            _exec(
                engine,
                """
                CREATE TABLE IF NOT EXISTS eposone_order_return (
                    id SERIAL PRIMARY KEY,
                    order_id INTEGER NOT NULL REFERENCES eposone_order(id) ON DELETE CASCADE,
                    reason TEXT NOT NULL,
                    user_ref VARCHAR(64),
                    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (NOW() AT TIME ZONE 'utc')
                );
                CREATE INDEX IF NOT EXISTS ix_eposone_order_return_order ON eposone_order_return (order_id);
                """,
            )
        else:
            _exec(
                engine,
                """
                CREATE TABLE IF NOT EXISTS eposone_order_return (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    order_id INTEGER NOT NULL,
                    reason TEXT NOT NULL,
                    user_ref VARCHAR(64),
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                """,
            )
        log('eposone_order_return: tabla creada')
