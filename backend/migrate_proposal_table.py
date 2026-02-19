#!/usr/bin/env python3
"""Fase 6: Crear tabla proposal."""
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
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS proposal (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id INTEGER NOT NULL REFERENCES user(id),
                appointment_id INTEGER NOT NULL REFERENCES appointment(id),
                description TEXT,
                total_amount REAL DEFAULT 0.0,
                status VARCHAR(20) DEFAULT 'ENVIADA',
                created_at DATETIME,
                FOREIGN KEY (client_id) REFERENCES user(id),
                FOREIGN KEY (appointment_id) REFERENCES appointment(id)
            )
        """)
        conn.commit()
        print("Tabla proposal creada o ya existía.")
        return True
    except Exception as e:
        conn.rollback()
        print("Error:", e)
        return False
    finally:
        conn.close()


if __name__ == "__main__":
    run()
