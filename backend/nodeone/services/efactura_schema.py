"""DDL idempotente: tablas módulo Facturación Electrónica."""

from __future__ import annotations

from models.efactura import (
    ElectronicInvoiceDocument,
    ElectronicInvoiceEventLog,
    ElectronicInvoiceProviderConfig,
)


def ensure_efactura_schema(db, engine, printfn=None) -> None:
    for model in (
        ElectronicInvoiceProviderConfig,
        ElectronicInvoiceDocument,
        ElectronicInvoiceEventLog,
    ):
        model.__table__.create(engine, checkfirst=True)
        if printfn:
            printfn(f'efactura: {model.__tablename__}')
