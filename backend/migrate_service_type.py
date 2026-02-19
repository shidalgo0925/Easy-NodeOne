#!/usr/bin/env python3
"""Fase 1: Añadir service_type a Service. Valores: CONSULTIVO | AGENDABLE. Existentes → AGENDABLE."""
import os
import sqlite3

_basedir = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.dirname(_basedir)
DB_PATH = os.path.join(_project_root, 'instance', 'relaticpanama.db')


def run():
    if not os.path.exists(DB_PATH):
        print(f"DB no encontrada: {DB_PATH}")
        return False
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("PRAGMA table_info(service)")
        cols = [c[1] for c in cursor.fetchall()]
        if 'service_type' not in cols:
            cursor.execute("ALTER TABLE service ADD COLUMN service_type VARCHAR(20) NOT NULL DEFAULT 'AGENDABLE'")
            print("+ service_type")
        cursor.execute("UPDATE service SET service_type = 'AGENDABLE' WHERE service_type IS NULL OR service_type = ''")
        conn.commit()
        print("Servicios existentes con service_type = AGENDABLE. Revisar en admin y cambiar a CONSULTIVO los que correspondan.")
        return True
    except Exception as e:
        conn.rollback()
        print("Error:", e)
        return False
    finally:
        conn.close()


if __name__ == "__main__":
    run()
