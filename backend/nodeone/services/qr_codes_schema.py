"""DDL idempotente para tabla qr_codes."""

from __future__ import annotations


def ensure_qr_codes_table(db, engine, printfn=None) -> None:
    from sqlalchemy import inspect, text

    from models.qr_codes import QrCodeRecord

    QrCodeRecord.__table__.create(engine, checkfirst=True)
    insp = inspect(engine)
    if 'qr_codes' in insp.get_table_names():
        cols = {c['name'] for c in insp.get_columns('qr_codes')}
        if 'style_json' not in cols:
            db.session.execute(text('ALTER TABLE qr_codes ADD COLUMN style_json TEXT'))
            db.session.commit()
    if printfn:
        printfn('ensure qr_codes')
