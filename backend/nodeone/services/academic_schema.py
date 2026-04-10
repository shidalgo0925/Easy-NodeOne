"""DDL idempotente: tablas académicas + columnas extra en invoices."""

from sqlalchemy import inspect, text


def ensure_academic_schema(db, engine, printfn=None) -> None:
    from models.academic import AcademicCourse, Enrollment, MoodleConfig, Student

    Student.__table__.create(engine, checkfirst=True)
    AcademicCourse.__table__.create(engine, checkfirst=True)
    Enrollment.__table__.create(engine, checkfirst=True)
    MoodleConfig.__table__.create(engine, checkfirst=True)

    insp = inspect(engine)
    if 'students' in insp.get_table_names():
        st_cols = {c['name'] for c in insp.get_columns('students')}
        for col_sql in (
            "ALTER TABLE students ADD COLUMN program_name VARCHAR(200)",
            "ALTER TABLE students ADD COLUMN faculty VARCHAR(200)",
            "ALTER TABLE students ADD COLUMN campus VARCHAR(120)",
            "ALTER TABLE students ADD COLUMN cohort_year INTEGER",
            "ALTER TABLE students ADD COLUMN institutional_email VARCHAR(255)",
        ):
            col = col_sql.split('ADD COLUMN ')[1].split()[0]
            if col not in st_cols:
                try:
                    db.session.execute(text(col_sql))
                    db.session.commit()
                    if printfn:
                        printfn('+ students.' + col)
                except Exception:
                    db.session.rollback()
                    raise
        insp = inspect(engine)

    if 'invoices' not in insp.get_table_names():
        return
    cols = {c['name'] for c in insp.get_columns('invoices')}
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
        try:
            db.session.execute(text('ALTER TABLE invoices ADD COLUMN due_date DATETIME'))
            db.session.commit()
            if printfn:
                printfn('+ invoices.due_date')
        except Exception:
            db.session.rollback()
            raise
