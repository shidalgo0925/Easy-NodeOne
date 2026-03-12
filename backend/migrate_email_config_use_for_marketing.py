#!/usr/bin/env python3
"""Añade use_for_marketing a email_config."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app import app, db
from sqlalchemy import text

with app.app_context():
    uri = app.config.get("SQLALCHEMY_DATABASE_URI", "")
    print("DB:", uri.replace("sqlite:///", "") if uri.startswith("sqlite:///") else uri)
    try:
        db.session.execute(text("ALTER TABLE email_config ADD COLUMN use_for_marketing BOOLEAN DEFAULT 0"))
        db.session.commit()
        print("OK added use_for_marketing")
    except Exception as e:
        if "duplicate column" in str(e).lower() or "already exists" in str(e).lower():
            print("skip use_for_marketing (exists)")
        else:
            print("use_for_marketing:", e)
        db.session.rollback()
