"""DDL idempotente: importación XLS de ventas + columnas de origen en quotations."""

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


def ensure_sales_xls_import_schema(db, engine, printfn=None) -> None:
    from nodeone.modules.sales.models import Quotation, SalesXlsImport

    Quotation.__table__.create(engine, checkfirst=True)
    SalesXlsImport.__table__.create(engine, checkfirst=True)
    insp = inspect(engine)
    if 'quotations' in insp.get_table_names():
        cols = {c['name'] for c in insp.get_columns('quotations')}
        additions = [
            ('source', "VARCHAR(20) DEFAULT 'manual'"),
            ('import_profile', 'VARCHAR(64)'),
            ('import_profile_version', 'INTEGER'),
            ('import_filename', 'VARCHAR(255)'),
            ('import_file_hash', 'VARCHAR(64)'),
            ('import_external_ref', 'VARCHAR(80)'),
        ]
        for name, ddl in additions:
            if name not in cols:
                _add_column(engine, 'quotations', name, ddl, printfn=printfn)
    if 'service' in insp.get_table_names():
        scols = {c['name'] for c in insp.get_columns('service')}
        if 'sku' not in scols:
            _add_column(engine, 'service', 'sku', 'VARCHAR(32)', printfn=printfn)
    if printfn:
        printfn('sales_xls_import: tabla lista')
