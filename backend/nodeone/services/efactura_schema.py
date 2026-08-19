"""DDL idempotente: tablas módulo Facturación Electrónica."""

from __future__ import annotations

from sqlalchemy import inspect, text

from models.efactura import (
    ElectronicInvoiceDocument,
    ElectronicInvoiceEventLog,
    ElectronicInvoiceProviderConfig,
)


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


def ensure_efactura_schema(db, engine, printfn=None) -> None:
    for model in (
        ElectronicInvoiceProviderConfig,
        ElectronicInvoiceDocument,
        ElectronicInvoiceEventLog,
    ):
        model.__table__.create(engine, checkfirst=True)
        if printfn:
            printfn(f'efactura: {model.__tablename__}')
    insp = inspect(engine)
    if 'electronic_invoice_document' not in insp.get_table_names():
        return
    cols = {c['name'] for c in insp.get_columns('electronic_invoice_document')}
    dialect = engine.dialect.name
    ts = 'TIMESTAMP' if dialect == 'postgresql' else 'DATETIME'
    additions = [
        ('qr_content', 'TEXT'),
        ('qr_image_base64', 'TEXT'),
        ('xml_content', 'TEXT'),
        ('pdf_content', 'TEXT'),
        ('consultation_url', 'VARCHAR(500)'),
        ('qr_source', 'VARCHAR(40)'),
        ('pac_document_id', 'VARCHAR(80)'),
        ('authorized_at', ts),
        ('pdf_url', 'VARCHAR(500)'),
        ('xml_url', 'VARCHAR(500)'),
        ('qr_url', 'VARCHAR(500)'),
    ]
    for name, ddl in additions:
        if name not in cols:
            _add_column(engine, 'electronic_invoice_document', name, ddl, printfn=printfn)
