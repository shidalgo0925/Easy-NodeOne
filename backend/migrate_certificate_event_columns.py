#!/usr/bin/env python3
"""Añade partner_organization, logo_left_url, logo_right_url, seal_url a certificate_events si no existen."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app import app, db
from sqlalchemy import text

with app.app_context():
    for col in ('partner_organization', 'logo_left_url', 'logo_right_url', 'seal_url'):
        try:
            db.session.execute(text(f"ALTER TABLE certificate_events ADD COLUMN {col} VARCHAR(500)"))
            db.session.commit()
            print(f"OK added {col}")
        except Exception as e:
            if 'duplicate column' in str(e).lower() or 'already exists' in str(e).lower():
                print(f"skip {col} (exists)")
            else:
                print(f" {col}: {e}")
            db.session.rollback()
