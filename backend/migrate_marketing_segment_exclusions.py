#!/usr/bin/env python3
"""Añade columna exclusion_user_ids a marketing_segment (JSON array de user IDs a excluir).
Ejecutar desde el mismo directorio y entorno donde corres la app: cd backend && python3 migrate_marketing_segment_exclusions.py"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app import app, db
from sqlalchemy import text

with app.app_context():
    uri = app.config.get("SQLALCHEMY_DATABASE_URI", "")
    print("DB:", uri.replace("sqlite:///", "") if uri.startswith("sqlite:///") else uri)
    try:
        db.session.execute(text("ALTER TABLE marketing_segment ADD COLUMN exclusion_user_ids TEXT"))
        db.session.commit()
        print("OK added exclusion_user_ids to marketing_segment")
    except Exception as e:
        if 'duplicate column' in str(e).lower() or 'already exists' in str(e).lower():
            print("skip exclusion_user_ids (exists)")
        else:
            print("exclusion_user_ids:", e)
        db.session.rollback()
