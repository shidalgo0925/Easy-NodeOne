"""DDL idempotente: program_slug en service + tabla course_cohort."""

from __future__ import annotations

from sqlalchemy import inspect, text


def ensure_course_program_schema(db, engine, printfn=None) -> None:
    import app as app_module

    CourseCohort = app_module.CourseCohort

    insp = inspect(engine)
    tables = insp.get_table_names()

    if 'course_cohort' not in tables:
        try:
            CourseCohort.__table__.create(engine, checkfirst=True)
            if printfn:
                printfn('+ table course_cohort')
        except Exception:
            raise

    if 'service' in tables:
        cols = {c['name'] for c in insp.get_columns('service')}
        if 'program_slug' not in cols:
            try:
                db.session.execute(text('ALTER TABLE service ADD COLUMN program_slug VARCHAR(120)'))
                db.session.commit()
                if printfn:
                    printfn('+ service.program_slug')
            except Exception:
                db.session.rollback()
                raise
