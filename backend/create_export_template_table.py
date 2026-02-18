#!/usr/bin/env python3
"""Crea la tabla export_template y columna visibility si no existen."""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
from app import app, db
from sqlalchemy import text as sql_text
with app.app_context():
    db.create_all()
    try:
        db.session.execute(sql_text("ALTER TABLE export_template ADD COLUMN visibility VARCHAR(20) DEFAULT 'own'"))
        db.session.commit()
        print("Columna visibility añadida a export_template.")
    except Exception as e:
        db.session.rollback()
        if 'duplicate column' in str(e).lower() or 'already exists' in str(e).lower():
            print("Columna visibility ya existe.")
        else:
            print("Tablas creadas/actualizadas (export_template si faltaba).")
