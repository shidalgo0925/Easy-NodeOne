#!/usr/bin/env python3
"""Añade send_after, attempts, error_message a email_queue."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app import app, db
from sqlalchemy import text

with app.app_context():
    uri = app.config.get("SQLALCHEMY_DATABASE_URI", "")
    print("DB:", uri.replace("sqlite:///", "") if uri.startswith("sqlite:///") else uri)
    for col, typ in [
        ("send_after", "DATETIME"),
        ("attempts", "INTEGER DEFAULT 0"),
        ("error_message", "TEXT"),
    ]:
        try:
            db.session.execute(text(f"ALTER TABLE email_queue ADD COLUMN {col} {typ}"))
            db.session.commit()
            print(f"OK added {col}")
        except Exception as e:
            if "duplicate column" in str(e).lower() or "already exists" in str(e).lower():
                print(f"skip {col} (exists)")
            else:
                print(f"{col}:", e)
            db.session.rollback()
