#!/usr/bin/env python3
"""Crea la tabla appointment_email_template si no existe (SQLite / SQLAlchemy)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db, AppointmentEmailTemplate  # noqa: E402


def main():
    with app.app_context():
        AppointmentEmailTemplate.__table__.create(bind=db.engine, checkfirst=True)
        print('✅ Tabla appointment_email_template verificada/creada')


if __name__ == '__main__':
    main()
