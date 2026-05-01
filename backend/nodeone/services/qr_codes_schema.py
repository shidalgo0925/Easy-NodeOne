"""DDL idempotente para tabla qr_codes."""

from __future__ import annotations


def ensure_qr_codes_table(db, engine, printfn=None) -> None:
    from models.qr_codes import QrCodeRecord

    QrCodeRecord.__table__.create(engine, checkfirst=True)
    if printfn:
        printfn('ensure qr_codes')
