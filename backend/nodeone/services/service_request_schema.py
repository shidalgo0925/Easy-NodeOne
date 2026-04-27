"""DDL idempotente: tabla ``service_request`` (ORM ``create``)."""

from __future__ import annotations


def ensure_service_request_table(db, engine, printfn=None) -> None:
    """Crea ``service_request`` si no existe (requiere tablas referenciadas ya creadas)."""
    try:
        from models.service_request import ServiceRequest

        ServiceRequest.__table__.create(bind=engine, checkfirst=True)
        if printfn:
            printfn('ensure service_request table')
    except Exception:
        db.session.rollback()
        raise
