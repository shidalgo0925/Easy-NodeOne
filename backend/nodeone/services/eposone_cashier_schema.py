"""DDL idempotente para credenciales de cajeros EPosOne."""

from __future__ import annotations

from sqlalchemy import inspect, text


def ensure_eposone_cashier_schema(db, engine, printfn=None) -> None:
    inspector = inspect(engine)
    if 'eposone_cashier_credential' not in inspector.get_table_names():
        ddl = """
        CREATE TABLE eposone_cashier_credential (
            id SERIAL PRIMARY KEY,
            organization_id INTEGER NOT NULL
                REFERENCES saas_organization(id) ON DELETE CASCADE,
            cashier_contact_id INTEGER NOT NULL
                REFERENCES en1_contact(id) ON DELETE CASCADE,
            pin_verifier VARCHAR(512) NOT NULL,
            pin_version INTEGER NOT NULL DEFAULT 1,
            pin_updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT uq_eposone_cashier_credential_contact
                UNIQUE (cashier_contact_id),
            CONSTRAINT uq_eposone_cashier_credential_org_contact
                UNIQUE (organization_id, cashier_contact_id)
        )
        """
        if engine.dialect.name != 'postgresql':
            ddl = ddl.replace('SERIAL PRIMARY KEY', 'INTEGER PRIMARY KEY AUTOINCREMENT')
        with engine.begin() as conn:
            conn.execute(text(ddl))
        if printfn:
            printfn('+ eposone_cashier_credential')

    with engine.begin() as conn:
        conn.execute(
            text(
                'CREATE INDEX IF NOT EXISTS ix_eposone_cashier_credential_org '
                'ON eposone_cashier_credential (organization_id)'
            )
        )
        conn.execute(
            text(
                'CREATE INDEX IF NOT EXISTS ix_eposone_cashier_credential_contact '
                'ON eposone_cashier_credential (cashier_contact_id)'
            )
        )
