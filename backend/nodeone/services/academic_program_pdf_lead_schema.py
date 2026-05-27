"""DDL idempotente: academic_program_pdf_lead (confirmación por correo)."""

from __future__ import annotations

from sqlalchemy import inspect, text


_ALTER_COLUMNS: tuple[tuple[str, str], ...] = (
    ('crm_lead_id', 'INTEGER'),
    ('confirmation_token', 'VARCHAR(120)'),
    ('confirmation_token_expires', 'DATETIME'),
    ('confirmation_sent_at', 'DATETIME'),
    ('email_confirmed_at', 'DATETIME'),
    ('resource_id', 'INTEGER'),
)


def ensure_academic_program_pdf_lead_schema(db, engine, printfn=None) -> None:
    from models.academic_program_pdf_lead import AcademicProgramPdfLead

    AcademicProgramPdfLead.__table__.create(engine, checkfirst=True)

    insp = inspect(engine)
    if 'academic_program_pdf_lead' not in insp.get_table_names():
        return
    cols = {c['name'] for c in insp.get_columns('academic_program_pdf_lead')}
    for col_name, col_def in _ALTER_COLUMNS:
        if col_name in cols:
            continue
        try:
            db.session.execute(
                text(f'ALTER TABLE academic_program_pdf_lead ADD COLUMN {col_name} {col_def}')
            )
            db.session.commit()
            if printfn:
                printfn(f'+ academic_program_pdf_lead.{col_name}')
        except Exception:
            db.session.rollback()
            raise
