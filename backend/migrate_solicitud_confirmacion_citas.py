#!/usr/bin/env python3
"""
Fase 1: Migración BD para flujo Solicitud → Confirmación por asesor.
Añade: is_initial_consult, advisor_response_notes, confirmed_at.
Citas existentes: is_initial_consult=False, status=CONFIRMADA (donde aplica).
"""
import os
import sqlite3

_basedir = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.dirname(_basedir)
DB_PATH = os.path.join(_project_root, 'instance', 'membership_legacy.db')


def column_exists(cursor, table, col):
    cursor.execute(f"PRAGMA table_info({table})")
    return any(c[1] == col for c in cursor.fetchall())


def run():
    if not os.path.exists(DB_PATH):
        print(f"DB no encontrada: {DB_PATH}")
        return False
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        # Añadir columnas
        if not column_exists(cursor, 'appointment', 'is_initial_consult'):
            cursor.execute("ALTER TABLE appointment ADD COLUMN is_initial_consult BOOLEAN DEFAULT 1")
            print("+ is_initial_consult")
        if not column_exists(cursor, 'appointment', 'advisor_response_notes'):
            cursor.execute("ALTER TABLE appointment ADD COLUMN advisor_response_notes TEXT")
            print("+ advisor_response_notes")
        if not column_exists(cursor, 'appointment', 'confirmed_at'):
            cursor.execute("ALTER TABLE appointment ADD COLUMN confirmed_at DATETIME")
            print("+ confirmed_at")

        # Citas existentes: is_initial_consult=False; status a CONFIRMADA donde estaba confirmed
        cursor.execute("UPDATE appointment SET is_initial_consult = 0")
        cursor.execute("UPDATE appointment SET status = 'CONFIRMADA' WHERE status = 'confirmed'")
        cursor.execute("UPDATE appointment SET confirmed_at = advisor_confirmed_at WHERE status = 'CONFIRMADA' AND advisor_confirmed_at IS NOT NULL AND confirmed_at IS NULL")
        conn.commit()
        print("Citas existentes actualizadas: is_initial_consult=0; status=CONFIRMADA donde correspondía.")
        return True
    except Exception as e:
        conn.rollback()
        print("Error:", e)
        return False
    finally:
        conn.close()


if __name__ == "__main__":
    run()
