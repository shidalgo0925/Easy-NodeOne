#!/usr/bin/env python3
"""Añade quotations.payment_terms (SQLite / columnas nuevas). Ejecutar desde backend/: python3 migrate_quotation_payment_terms.py"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import text

from app import app
from nodeone.core.db import db


def main() -> None:
    with app.app_context():
        uri = app.config.get('SQLALCHEMY_DATABASE_URI') or ''
        print('DB:', uri.replace('sqlite:///', '') if uri.startswith('sqlite:///') else uri)
        try:
            db.session.execute(text('ALTER TABLE quotations ADD COLUMN payment_terms VARCHAR(200)'))
            db.session.commit()
            print('Columna payment_terms añadida.')
        except Exception as e:
            db.session.rollback()
            msg = str(e).lower()
            if 'duplicate column' in msg or 'already exists' in msg:
                print('Columna payment_terms ya existía.')
            else:
                raise


if __name__ == '__main__':
    main()
