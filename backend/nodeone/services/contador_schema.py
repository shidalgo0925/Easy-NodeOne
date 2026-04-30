"""DDL idempotente: cantidades de conteo en float/decimal (tabla + log)."""

from __future__ import annotations

from typing import Any, Callable

from sqlalchemy import text


def ensure_contador_qty_float_columns(
    db: Any, engine: Any, printfn: Callable[[str], None] | None = None
) -> None:
    """
    Migra counted_qty (y log) a tipo flotante para soportar decimales (p. ej. 0,25).
    Idempotente: no falla si ya es numérico real.
    """
    from sqlalchemy import inspect

    def _log(msg: str) -> None:
        if printfn:
            printfn(msg)

    insp = inspect(engine)
    if not insp.has_table('contador_count_line'):
        return
    dialect = engine.dialect.name
    if dialect == 'postgresql':
        for table, col in (
            ('contador_count_line', 'counted_qty'),
            ('contador_capture_log', 'old_qty'),
            ('contador_capture_log', 'new_qty'),
        ):
            try:
                row = db.session.execute(
                    text(
                        """
                        SELECT data_type FROM information_schema.columns
                        WHERE table_schema = 'public' AND table_name = :t AND column_name = :c
                        """
                    ),
                    {'t': table, 'c': col},
                ).fetchone()
                if not row:
                    continue
                dt = (row[0] or '').lower()
                if dt in ('double precision', 'real', 'numeric', 'decimal'):
                    continue
                if dt in ('integer', 'bigint', 'smallint'):
                    db.session.execute(
                        text(
                            f'ALTER TABLE {table} ALTER COLUMN {col} '
                            f'TYPE DOUBLE PRECISION USING {col}::double precision'
                        )
                    )
                    _log(f'contador_schema: {table}.{col} → double precision')
            except Exception as ex:
                db.session.rollback()
                _log(f'contador_schema: omitir {table}.{col}: {ex}')
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
    elif dialect == 'sqlite':
        # SQLite: INTEGER se usa como almacenamiento; Float en SQLAlchemy sigue funcionando
        # para valores nuevos; valores enteros existentes se leen bien.
        _log('contador_schema: sqlite — tipos float compatibles sin ALTER obligatorio')
