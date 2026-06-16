"""DDL idempotente: columnas Yappy manual en ``payment`` (BDS legacy post-deploy)."""

from __future__ import annotations

from sqlalchemy import inspect, text


def _add_column(engine, table: str, name: str, ddl: str, printfn=None) -> None:
    try:
        with engine.begin() as conn:
            conn.execute(text(f'ALTER TABLE {table} ADD COLUMN {name} {ddl}'))
        if printfn:
            printfn(f'+ {table}.{name}')
    except Exception as ex:
        msg = str(ex).lower()
        if 'duplicate column' in msg or 'already exists' in msg:
            return
        if printfn:
            printfn(f'! {table}.{name}: {ex}')


def ensure_payment_yappy_manual_columns(db, engine, printfn=None) -> None:
    """
    Alinea ``payment`` con ``models.payments.Payment`` (Yappy manual / checkout v3).
    Usa conexión aparte (engine.begin) para no heredar transacciones abortadas.
    """
    insp = inspect(engine)
    if 'payment' not in insp.get_table_names():
        return
    cols = {c['name'] for c in insp.get_columns('payment')}
    dialect = engine.dialect.name
    ts = 'TIMESTAMP' if dialect == 'postgresql' else 'DATETIME'

    additions = [
        ('amount_received_cents', 'INTEGER'),
        ('validated_by_user_id', 'INTEGER'),
        ('validated_at', ts),
        ('validation_observations', 'TEXT'),
        ('yappy_manual_audit_json', 'TEXT'),
        ('organization_id', 'INTEGER'),
        ('payment_user_reference', 'VARCHAR(500)'),
        ('receipt_uploaded_at', ts),
        ('receipt_disk_path', 'VARCHAR(500)'),
        ('rejection_reason', 'TEXT'),
    ]

    for name, ddl in additions:
        if name not in cols:
            _add_column(engine, 'payment', name, ddl, printfn=printfn)

    if dialect == 'postgresql':
        try:
            with engine.begin() as conn:
                conn.execute(text('ALTER TABLE payment ALTER COLUMN status TYPE VARCHAR(32)'))
            if printfn:
                printfn('payment.status → VARCHAR(32)')
        except Exception as ex:
            if printfn:
                printfn(f'! payment.status widen: {ex}')
