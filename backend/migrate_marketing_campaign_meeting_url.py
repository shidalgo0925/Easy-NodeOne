#!/usr/bin/env python3
"""Añade meeting_url a marketing_campaigns (URL reunión / Meet para plantillas)."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app import app, db
from sqlalchemy import text

with app.app_context():
    uri = app.config.get("SQLALCHEMY_DATABASE_URI", "")
    print("DB:", uri.replace("sqlite:///", "") if uri.startswith("sqlite:///") else uri)
    try:
        db.session.execute(text("ALTER TABLE marketing_campaigns ADD COLUMN meeting_url VARCHAR(500)"))
        db.session.commit()
        print("OK added meeting_url")
    except Exception as e:
        if "duplicate column" in str(e).lower() or "already exists" in str(e).lower():
            print("skip meeting_url (exists)")
        else:
            print("meeting_url:", e)
        db.session.rollback()
