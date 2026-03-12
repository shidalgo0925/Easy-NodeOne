#!/usr/bin/env python3
"""Crear tabla certificate_templates y columna template_id en certificate_events."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app import app, db
from sqlalchemy import text

with app.app_context():
    try:
        from app import CertificateTemplate
        CertificateTemplate.__table__.create(db.engine, checkfirst=True)
        print("OK certificate_templates table")
    except Exception as e:
        print("certificate_templates:", e)
        db.session.rollback()

    try:
        db.session.execute(text("ALTER TABLE certificate_events ADD COLUMN template_id INTEGER"))
        db.session.commit()
        print("OK added template_id to certificate_events")
    except Exception as e:
        if 'duplicate column' in str(e).lower() or 'already exists' in str(e).lower():
            print("skip template_id (exists)")
        else:
            print("template_id:", e)
        db.session.rollback()
