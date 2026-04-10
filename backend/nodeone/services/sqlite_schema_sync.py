"""
Sincroniza el esquema SQLite con los modelos SQLAlchemy: añade columnas que faltan en la BD.

Tras restaurar backups antiguos suele faltar `organization_id`, flags de marketing, etc.
El origen de verdad son las tablas en `db.metadata` (modelos en `models/`).

Uso programático (siempre dentro de `app.app_context()`):

    from nodeone.services.sqlite_schema_sync import run_sqlite_schema_sync
    report = run_sqlite_schema_sync(dry_run=False, backfill_org_ids=True)

CLI: `python3 sync_sqlite_columns_from_models.py` en `backend/`.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import inspect as sa_inspect, text
from sqlalchemy.dialects.sqlite import dialect as sqlite_dialect
from sqlalchemy.schema import CreateColumn


@dataclass
class SqliteSchemaSyncReport:
    """Resultado de `run_sqlite_schema_sync`."""

    dry_run: bool
    planned: list[tuple[str, str, str]] = field(default_factory=list)
    """(table_name, column_name, ddl_fragment)."""
    applied: int = 0
    applied_columns: list[tuple[str, str]] = field(default_factory=list)
    """(table_name, column_name) aplicados con éxito."""
    errors: list[tuple[str, str]] = field(default_factory=list)
    """(sql o identificador, mensaje)."""
    backfill_statements_run: int = 0


def collect_missing_sqlite_columns(db: Any) -> list[tuple[str, str, str]]:
    """
    Compara `db.metadata` con las tablas existentes en la BD actual.
    Devuelve filas (table_name, column_name, ddl_para_ADD_COLUMN).
    """
    dialect = sqlite_dialect()
    insp = sa_inspect(db.engine)
    out: list[tuple[str, str, str]] = []

    for table_name, table in db.metadata.tables.items():
        if table_name.startswith('sqlite_'):
            continue
        if not insp.has_table(table_name):
            continue
        existing = {c['name'] for c in insp.get_columns(table_name)}
        for col in table.columns:
            if col.name in existing:
                continue
            if col.primary_key:
                continue
            try:
                ddl = str(CreateColumn(col).compile(dialect=dialect))
            except Exception:
                continue
            upper = ddl.upper()
            if 'NOT NULL' in upper and 'DEFAULT' not in upper:
                ddl = re.sub(r'\s+NOT\s+NULL\s*$', '', ddl, flags=re.I).strip()
            out.append((table_name, col.name, ddl))

    return out


def apply_column_alters(
    db: Any, planned: list[tuple[str, str, str]]
) -> tuple[int, list[tuple[str, str]], list[tuple[str, str]]]:
    """ALTER por sentencia. Devuelve (n_aplicadas, columnas_ok (table,col), errores)."""
    errors: list[tuple[str, str]] = []
    ok_cols: list[tuple[str, str]] = []
    applied = 0
    for table_name, col_name, ddl in planned:
        sql = f'ALTER TABLE {table_name} ADD COLUMN {ddl}'
        try:
            db.session.execute(text(sql))
            db.session.commit()
            applied += 1
            ok_cols.append((table_name, col_name))
        except Exception as e:
            db.session.rollback()
            errors.append((sql, str(e)))
    return applied, ok_cols, errors


def backfill_null_organization_ids(db: Any) -> int:
    """
    Tras añadir `organization_id` en tablas legadas, asigna tenant 1 donde siga NULL.
    Ignora tablas/columnas que no existan.
    """
    insp = sa_inspect(db.engine)
    n = 0
    targets = ('email_config', 'appointment_type', 'payment_config')
    for table in targets:
        if not insp.has_table(table):
            continue
        cols = {c['name'] for c in insp.get_columns(table)}
        if 'organization_id' not in cols:
            continue
        try:
            r = db.session.execute(
                text(f'UPDATE {table} SET organization_id = 1 WHERE organization_id IS NULL')
            )
            n += getattr(r, 'rowcount', 0) or 0
        except Exception:
            db.session.rollback()
            continue
    db.session.commit()
    return n


def run_sqlite_schema_sync(
    db: Any,
    *,
    dry_run: bool = False,
    backfill_org_ids: bool = True,
) -> SqliteSchemaSyncReport:
    """
    Orquesta: detectar columnas faltantes, aplicar ALTER, opcional backfill de org 1.

    Requiere `app.app_context()` activo.
    """
    planned_tuples = collect_missing_sqlite_columns(db)
    report = SqliteSchemaSyncReport(dry_run=dry_run, planned=list(planned_tuples))

    if dry_run:
        return report

    applied, ok_cols, errors = apply_column_alters(db, planned_tuples)
    report.applied = applied
    report.applied_columns = ok_cols
    report.errors = errors

    if backfill_org_ids and not errors:
        report.backfill_statements_run = backfill_null_organization_ids(db)

    return report
