#!/usr/bin/env python3
"""Crear tabla ai_config y fila por defecto."""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db, AIConfig


with app.app_context():
    uri = app.config.get("SQLALCHEMY_DATABASE_URI", "")
    print("DB:", uri.replace("sqlite:///", "") if uri.startswith("sqlite:///") else uri)
    try:
        AIConfig.__table__.create(db.engine, checkfirst=True)
    except Exception as e:
        print("Error creating ai_config:", e)
        sys.exit(1)

    try:
        cfg = AIConfig.get_active_config()
        print(f"AI config ensured. enabled={cfg.enabled}, collection={cfg.collection}, api_url={cfg.api_url}")
    except Exception as e:
        print("Error ensuring default AI config:", e)
        sys.exit(1)
