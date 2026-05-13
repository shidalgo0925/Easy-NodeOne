#!/usr/bin/env python3
"""
Yappy manual checkout v3: campos en payment_config y payment (instrucciones, comprobantes privados, org).

Ejecutar desde backend: python migrate_yappy_manual_checkout_v3.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import inspect, text

from app import app, db


def _add_column(table: str, name: str, ddl_sqlite: str, ddl_pg: str):
    insp = inspect(db.engine)
    cols = [c["name"] for c in insp.get_columns(table)]
    if name in cols:
        print(f"  {table}.{name}: ya existe")
        return
    dialect = db.engine.dialect.name
    ddl = ddl_pg if dialect == "postgresql" else ddl_sqlite
    try:
        db.session.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}"))
        db.session.commit()
        print(f"  {table}.{name}: añadida")
    except Exception as e:
        db.session.rollback()
        print(f"  ERROR {table}.{name}: {e}")
        raise


with app.app_context():
    uri = app.config.get("SQLALCHEMY_DATABASE_URI") or ""
    print("DB:", uri[:80] + ("..." if len(uri) > 80 else ""))

    _add_column("payment_config", "yappy_display_name", "VARCHAR(200)", "VARCHAR(200)")
    _add_column("payment_config", "yappy_phone_or_identifier", "VARCHAR(120)", "VARCHAR(120)")
    _add_column("payment_config", "yappy_merchant_phone", "VARCHAR(64)", "VARCHAR(64)")
    _add_column("payment_config", "yappy_instructions", "TEXT", "TEXT")
    _add_column(
        "payment_config",
        "yappy_requires_receipt",
        "INTEGER NOT NULL DEFAULT 1",
        "BOOLEAN NOT NULL DEFAULT TRUE",
    )
    _add_column(
        "payment_config",
        "yappy_admin_validation_required",
        "INTEGER NOT NULL DEFAULT 1",
        "BOOLEAN NOT NULL DEFAULT TRUE",
    )

    _add_column("payment", "organization_id", "INTEGER", "INTEGER")
    _add_column("payment", "payment_user_reference", "VARCHAR(500)", "VARCHAR(500)")
    _add_column("payment", "receipt_uploaded_at", "TIMESTAMP", "TIMESTAMP")
    _add_column("payment", "receipt_disk_path", "VARCHAR(500)", "VARCHAR(500)")
    _add_column("payment", "rejection_reason", "TEXT", "TEXT")

    print("Migración yappy_manual_checkout_v3 lista.")
