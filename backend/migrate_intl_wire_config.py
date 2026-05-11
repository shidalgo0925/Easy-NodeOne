#!/usr/bin/env python3
"""Columnas PaymentConfig para transferencia internacional (SWIFT). Ejecutar desde backend."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import inspect, text

from app import app, db


def _add(table, name, sqlite_ddl, pg_ddl):
    cols = [c["name"] for c in inspect(db.engine).get_columns(table)]
    if name in cols:
        print(f"  {table}.{name}: ya existe")
        return
    ddl = pg_ddl if db.engine.dialect.name == "postgresql" else sqlite_ddl
    db.session.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}"))
    db.session.commit()
    print(f"  {table}.{name}: añadida")


with app.app_context():
    _add("payment_config", "intl_wire_enabled", "INTEGER DEFAULT 1", "BOOLEAN DEFAULT TRUE")
    _add("payment_config", "intl_wire_beneficiary_name", "VARCHAR(400)", "VARCHAR(400)")
    _add("payment_config", "intl_wire_bank_name", "VARCHAR(200)", "VARCHAR(200)")
    _add("payment_config", "intl_wire_swift", "VARCHAR(32)", "VARCHAR(32)")
    _add("payment_config", "intl_wire_account", "VARCHAR(80)", "VARCHAR(80)")
    _add("payment_config", "intl_wire_account_type", "VARCHAR(80)", "VARCHAR(80)")
    _add("payment_config", "intl_wire_country", "VARCHAR(120)", "VARCHAR(120)")
    _add("payment_config", "intl_wire_instructions", "TEXT", "TEXT")
    print("Migración intl_wire lista.")
