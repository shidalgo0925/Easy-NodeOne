#!/usr/bin/env python3
"""Añade is_dynamic y updated_at a marketing_segment."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app import app, db
from sqlalchemy import text

with app.app_context():
    uri = app.config.get("SQLALCHEMY_DATABASE_URI", "")
    print("DB:", uri.replace("sqlite:///", "") if uri.startswith("sqlite:///") else uri)
    for col, typ in [("is_dynamic", "INTEGER DEFAULT 1"), ("updated_at", "DATETIME")]:
        try:
            db.session.execute(text(f"ALTER TABLE marketing_segment ADD COLUMN {col} {typ}"))
            db.session.commit()
            print(f"OK added {col}")
        except Exception as e:
            if "duplicate column" in str(e).lower() or "already exists" in str(e).lower():
                print(f"skip {col} (exists)")
            else:
                print(f"{col}:", e)
            db.session.rollback()
