"""DDL idempotente: columnas Yappy / checkout en payment_config (PostgreSQL y SQLite)."""

from __future__ import annotations

from sqlalchemy import inspect, text

# (column_name, sqlite_ddl, postgresql_ddl)
_PAYMENT_CONFIG_BANCO_GENERAL_COLUMNS = (
    ('banco_general_beneficiary_name', 'VARCHAR(400)', 'VARCHAR(400)'),
    ('banco_general_bank_name', 'VARCHAR(200)', 'VARCHAR(200)'),
    ('banco_general_account_number', 'VARCHAR(80)', 'VARCHAR(80)'),
    ('banco_general_account_type', 'VARCHAR(80)', 'VARCHAR(80)'),
)

_PAYMENT_CONFIG_INTL_WIRE_COLUMNS = (
    ('intl_wire_enabled', 'INTEGER DEFAULT 1', 'BOOLEAN DEFAULT TRUE'),
    ('intl_wire_beneficiary_name', 'VARCHAR(400)', 'VARCHAR(400)'),
    ('intl_wire_bank_name', 'VARCHAR(200)', 'VARCHAR(200)'),
    ('intl_wire_swift', 'VARCHAR(32)', 'VARCHAR(32)'),
    ('intl_wire_account', 'VARCHAR(80)', 'VARCHAR(80)'),
    ('intl_wire_account_type', 'VARCHAR(80)', 'VARCHAR(80)'),
    ('intl_wire_country', 'VARCHAR(120)', 'VARCHAR(120)'),
    ('intl_wire_instructions', 'TEXT', 'TEXT'),
)

_PAYMENT_CONFIG_YAPPY_COLUMNS = (
    ('yappy_directory_name', 'VARCHAR(100)', 'VARCHAR(100)'),
    ('yappy_qr_image_path', 'VARCHAR(500)', 'VARCHAR(500)'),
    ('yappy_business_name', 'VARCHAR(200)', 'VARCHAR(200)'),
    ('yappy_manual_enabled', 'INTEGER NOT NULL DEFAULT 0', 'BOOLEAN DEFAULT FALSE'),
    ('yappy_manual_instructions', 'TEXT', 'TEXT'),
    ('yappy_manual_admin_emails', 'TEXT', 'TEXT'),
    ('yappy_display_name', 'VARCHAR(200)', 'VARCHAR(200)'),
    ('yappy_phone_or_identifier', 'VARCHAR(120)', 'VARCHAR(120)'),
    ('yappy_merchant_phone', 'VARCHAR(64)', 'VARCHAR(64)'),
    ('yappy_instructions', 'TEXT', 'TEXT'),
    ('yappy_requires_receipt', 'INTEGER NOT NULL DEFAULT 1', 'BOOLEAN NOT NULL DEFAULT TRUE'),
    ('yappy_admin_validation_required', 'INTEGER NOT NULL DEFAULT 1', 'BOOLEAN NOT NULL DEFAULT TRUE'),
)


def ensure_payment_config_yappy_columns(db, engine, printfn=None) -> None:
    """Alinea payment_config con models.payments.PaymentConfig (Yappy manual / checkout v3)."""
    insp = inspect(engine)
    if 'payment_config' not in insp.get_table_names():
        return
    cols = {c['name'] for c in insp.get_columns('payment_config')}
    dialect = engine.dialect.name
    use_pg = dialect == 'postgresql'

    for name, sqlite_ddl, pg_ddl in (
        *_PAYMENT_CONFIG_BANCO_GENERAL_COLUMNS,
        *_PAYMENT_CONFIG_INTL_WIRE_COLUMNS,
        *_PAYMENT_CONFIG_YAPPY_COLUMNS,
    ):
        if name in cols:
            continue
        ddl = pg_ddl if use_pg else sqlite_ddl
        try:
            if use_pg:
                db.session.execute(
                    text(f'ALTER TABLE payment_config ADD COLUMN IF NOT EXISTS {name} {ddl}')
                )
            else:
                db.session.execute(text(f'ALTER TABLE payment_config ADD COLUMN {name} {ddl}'))
            db.session.commit()
            cols.add(name)
            if printfn:
                printfn(f'+ payment_config.{name}')
        except Exception:
            db.session.rollback()
            raise
