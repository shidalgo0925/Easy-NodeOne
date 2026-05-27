"""DDL idempotente: academic_program + columnas nuevas."""

from __future__ import annotations

from sqlalchemy import inspect, text

# Columnas añadidas tras el modelo base (ALTER idempotente al arrancar).
_ACADEMIC_PROGRAM_ALTER_COLUMNS: tuple[tuple[str, str], ...] = (
    ("media_position", "VARCHAR(8) NOT NULL DEFAULT 'left'"),
    ("marketing_tag", "VARCHAR(120)"),
    ("key_focuses", "TEXT"),
    ("ideal_for", "TEXT"),
    ("cta_label", "VARCHAR(200)"),
    ("cta_action", "VARCHAR(32) NOT NULL DEFAULT 'scroll_pricing'"),
    ("catalog_sort_order", "INTEGER NOT NULL DEFAULT 0"),
    ("image_wp_landing", "VARCHAR(500)"),
    ("academic_program_pdf_url", "VARCHAR(500)"),
    ("academic_program_pdf_title", "VARCHAR(200)"),
    ("show_academic_program_pdf", "BOOLEAN NOT NULL DEFAULT 0"),
    ("academic_program_pdf_filename", "VARCHAR(255)"),
    ("academic_program_pdf_uploaded_at", "DATETIME"),
)


def ensure_academic_program_schema(db, engine, printfn=None) -> None:
    from models.academic_program import AcademicProgram, AcademicProgramPricingPlan

    AcademicProgram.__table__.create(engine, checkfirst=True)
    AcademicProgramPricingPlan.__table__.create(engine, checkfirst=True)

    insp = inspect(engine)
    if 'academic_program' not in insp.get_table_names():
        return
    cols = {c['name'] for c in insp.get_columns('academic_program')}
    for col_name, col_def in _ACADEMIC_PROGRAM_ALTER_COLUMNS:
        if col_name in cols:
            continue
        try:
            db.session.execute(text(f'ALTER TABLE academic_program ADD COLUMN {col_name} {col_def}'))
            db.session.commit()
            if printfn:
                printfn(f'+ academic_program.{col_name}')
        except Exception:
            db.session.rollback()
            raise
