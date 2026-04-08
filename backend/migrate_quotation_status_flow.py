#!/usr/bin/env python3
"""
Normaliza estado de cotizaciones (draft → … → paid) y legacy NULL.
Ejecutar desde backend/: python migrate_quotation_status_flow.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app
from nodeone.core.db import db
from sqlalchemy import text


def main():
    with app.app_context():
        eng = db.engine
        with eng.connect() as conn:
            try:
                conn.execute(text('SELECT status FROM quotations LIMIT 1'))
            except Exception as e:
                print('Tabla quotations no accesible:', e)
                return 1
            conn.execute(
                text(
                    """
                    UPDATE quotations
                    SET status = 'confirmed'
                    WHERE status IS NULL OR TRIM(status) = ''
                    """
                )
            )
            conn.commit()
        print('OK: cotizaciones sin status pasaron a confirmed (legacy).')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
