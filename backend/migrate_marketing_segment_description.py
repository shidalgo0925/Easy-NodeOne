#!/usr/bin/env python3
"""Añade description a marketing_segment."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app import app, db
from sqlalchemy import text

with app.app_context():
    uri = app.config.get("SQLALCHEMY_DATABASE_URI", "")
    print("DB:", uri.replace("sqlite:///", "") if uri.startswith("sqlite:///") else uri)
    try:
        db.session.execute(text("ALTER TABLE marketing_segment ADD COLUMN description TEXT"))
        db.session.commit()
        print("OK added description")
    except Exception as e:
        if "duplicate column" in str(e).lower() or "already exists" in str(e).lower():
            print("skip description (exists)")
        else:
            print("description:", e)
        db.session.rollback()
