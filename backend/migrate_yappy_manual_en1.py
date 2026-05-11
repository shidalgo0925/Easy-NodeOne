#!/usr/bin/env python3
"""
Yappy manual (EN1): columnas en payment y payment_config.
Ejecutar desde backend: python migrate_yappy_manual_en1.py
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

    # payment_config
    _add_column(
        "payment_config",
        "yappy_directory_name",
        "VARCHAR(100)",
        "VARCHAR(100)",
    )
    _add_column(
        "payment_config",
        "yappy_qr_image_path",
        "VARCHAR(500)",
        "VARCHAR(500)",
    )
    _add_column(
        "payment_config",
        "yappy_business_name",
        "VARCHAR(200)",
        "VARCHAR(200)",
    )
    _add_column(
        "payment_config",
        "yappy_manual_enabled",
        "INTEGER DEFAULT 0",
        "BOOLEAN DEFAULT FALSE",
    )
    _add_column(
        "payment_config",
        "yappy_manual_instructions",
        "TEXT",
        "TEXT",
    )
    _add_column(
        "payment_config",
        "yappy_manual_admin_emails",
        "TEXT",
        "TEXT",
    )

    # payment
    _add_column(
        "payment",
        "amount_received_cents",
        "INTEGER",
        "INTEGER",
    )
    _add_column(
        "payment",
        "validated_by_user_id",
        "INTEGER",
        "INTEGER",
    )
    _add_column(
        "payment",
        "validated_at",
        "TIMESTAMP",
        "TIMESTAMP",
    )
    _add_column(
        "payment",
        "validation_observations",
        "TEXT",
        "TEXT",
    )
    _add_column(
        "payment",
        "yappy_manual_audit_json",
        "TEXT",
        "TEXT",
    )

    dialect = db.engine.dialect.name
    if dialect == "postgresql":
        try:
            db.session.execute(
                text("ALTER TABLE payment ALTER COLUMN status TYPE VARCHAR(32)")
            )
            db.session.commit()
            print("  payment.status: ampliado a VARCHAR(32)")
        except Exception as e:
            db.session.rollback()
            print(f"  payment.status alter (opcional): {e}")

    print("Migración yappy_manual EN1 lista.")
