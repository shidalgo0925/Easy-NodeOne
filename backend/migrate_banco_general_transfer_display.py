#!/usr/bin/env python3
"""Columnas PaymentConfig para transferencia nacional Banco General. Ejecutar desde backend."""
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
    _add("payment_config", "banco_general_beneficiary_name", "VARCHAR(400)", "VARCHAR(400)")
    _add("payment_config", "banco_general_bank_name", "VARCHAR(200)", "VARCHAR(200)")
    _add("payment_config", "banco_general_account_number", "VARCHAR(80)", "VARCHAR(80)")
    _add("payment_config", "banco_general_account_type", "VARCHAR(80)", "VARCHAR(80)")
    print("Migración banco_general transfer display lista.")
