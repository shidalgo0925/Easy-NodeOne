"""DDL idempotente: columnas del modelo CvApplication en BDs antiguas."""

from __future__ import annotations

from sqlalchemy import inspect, text


def ensure_cv_application_columns(db, engine, printfn=None) -> None:
    insp = inspect(engine)
    if 'cv_application' not in insp.get_table_names():
        return
    cols = {c['name'] for c in insp.get_columns('cv_application')}
    dialect = engine.dialect.name
    bool_sql = 'BOOLEAN DEFAULT FALSE' if dialect == 'postgresql' else 'BOOLEAN DEFAULT 0'

    specs = [
        ('desired_salary', 'VARCHAR(120)'),
        ('professional_status', 'VARCHAR(120)'),
        ('native_language', 'VARCHAR(80)'),
        ('photo_relative_path', 'VARCHAR(500)'),
        ('cv_document_relative_path', 'VARCHAR(500)'),
        ('legal_accepted', bool_sql),
    ]

    for col_name, col_type in specs:
        if col_name in cols:
            continue
        try:
            db.session.execute(text(f'ALTER TABLE cv_application ADD COLUMN {col_name} {col_type}'))
            db.session.commit()
            if printfn:
                printfn(f'+ cv_application.{col_name}')
        except Exception:
            db.session.rollback()
            raise
