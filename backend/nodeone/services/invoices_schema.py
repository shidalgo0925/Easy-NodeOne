"""DDL idempotente: columnas del modelo Invoice ausentes en BDs antiguas."""

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


def ensure_invoices_model_columns(db, engine, printfn=None) -> None:
    """
    Alinea `invoices` con `nodeone.modules.accounting.models.Invoice`.
    Usa conexión aparte (engine.begin) para no heredar transacciones abortadas.
    """
    insp = inspect(engine)
    if 'invoices' not in insp.get_table_names():
        return
    cols = {c['name'] for c in insp.get_columns('invoices')}
    dialect = engine.dialect.name
    ts = 'TIMESTAMP' if dialect == 'postgresql' else 'DATETIME'

    additions = [
        ('enrollment_id', 'INTEGER'),
        ('due_date', ts),
        ('contact_id', 'INTEGER'),
        ('customer_contact_id', 'INTEGER'),
        ('billing_contact_id', 'INTEGER'),
        ('salesperson_contact_id', 'INTEGER'),
        ('salesperson_user_id', 'INTEGER'),
        ('currency', "VARCHAR(8) DEFAULT 'USD'"),
        ('notes', 'TEXT'),
        ('amount_paid', 'DOUBLE PRECISION DEFAULT 0'),
        ('journal_entry_id', 'INTEGER'),
        ('payment_journal_entry_id', 'INTEGER'),
    ]
    if dialect != 'postgresql':
        additions = [
            (n, d.replace('DOUBLE PRECISION', 'FLOAT')) for n, d in additions
        ]

    for name, ddl in additions:
        if name not in cols:
            _add_column(engine, 'invoices', name, ddl, printfn=printfn)
