"""DDL idempotente: columnas del modelo Invoice ausentes en BDs antiguas (p. ej. sin módulo académico)."""

from __future__ import annotations

from sqlalchemy import inspect, text


def ensure_invoices_model_columns(db, engine, printfn=None) -> None:
    """
    Alinea `invoices` con `nodeone.modules.accounting.models.Invoice`.
    PostgreSQL histórico a veces no tiene enrollment_id (solo se añadía vía rutas académicas).
    """
    insp = inspect(engine)
    if 'invoices' not in insp.get_table_names():
        return
    cols = {c['name'] for c in insp.get_columns('invoices')}
    dialect = engine.dialect.name

    if 'enrollment_id' not in cols:
        try:
            db.session.execute(text('ALTER TABLE invoices ADD COLUMN enrollment_id INTEGER'))
            db.session.commit()
            if printfn:
                printfn('+ invoices.enrollment_id')
        except Exception:
            db.session.rollback()
            raise

    if 'due_date' not in cols:
        dd_type = 'TIMESTAMP' if dialect == 'postgresql' else 'DATETIME'
        try:
            db.session.execute(text(f'ALTER TABLE invoices ADD COLUMN due_date {dd_type}'))
            db.session.commit()
            if printfn:
                printfn('+ invoices.due_date')
        except Exception:
            db.session.rollback()
            raise
