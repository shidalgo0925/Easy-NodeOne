"""DDL idempotente: columnas nuevas en tabla ``event``."""
from __future__ import annotations

from sqlalchemy import inspect, text

_EVENT_ALTER_COLUMNS: tuple[tuple[str, str], ...] = (
    ('catalog_sort_order', 'INTEGER NOT NULL DEFAULT 0'),
)


def ensure_event_schema(db, engine, printfn=None) -> None:
    from models.events import Event

    Event.__table__.create(engine, checkfirst=True)
    insp = inspect(engine)
    if 'event' not in insp.get_table_names():
        return
    cols = {c['name'] for c in insp.get_columns('event')}
    for col_name, col_def in _EVENT_ALTER_COLUMNS:
        if col_name in cols:
            continue
        db.session.execute(text(f'ALTER TABLE event ADD COLUMN {col_name} {col_def}'))
        db.session.commit()
        if printfn:
            printfn(f'+ event.{col_name}')
