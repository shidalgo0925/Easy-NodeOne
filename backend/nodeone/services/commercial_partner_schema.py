"""DDL idempotente: campos fiscales PA en tenant_crm_contact y vínculos factura/FE/académico."""

from __future__ import annotations

from sqlalchemy import inspect, text


def ensure_commercial_partner_schema(db, engine, printfn=None) -> None:
    insp = inspect(engine)
    dialect = engine.dialect.name
    tables = set(insp.get_table_names())
    user_tbl = '"user"' if dialect == 'postgresql' else 'user'

    if 'tenant_crm_contact' in tables:
        try:
            cols = {c['name'] for c in insp.get_columns('tenant_crm_contact')}
        except Exception as ex:
            db.session.rollback()
            if printfn:
                printfn(f'! tenant_crm_contact inspect: {ex}')
            cols = set()
        additions = (
            ('legal_name', 'VARCHAR(300)'),
            ('trade_name', 'VARCHAR(300)'),
            ('person_type', "VARCHAR(30) NOT NULL DEFAULT 'natural'"),
            ('id_type', 'VARCHAR(30)'),
            ('tax_id', 'VARCHAR(80)'),
            ('tax_dv', 'VARCHAR(10)'),
            ('id_number', 'VARCHAR(80)'),
            ('fiscal_email', 'VARCHAR(255)'),
            ('fiscal_phone', 'VARCHAR(50)'),
            ('fiscal_address', 'TEXT'),
            ('country_code', "VARCHAR(8) NOT NULL DEFAULT 'PA'"),
            ('province', 'VARCHAR(120)'),
            ('district', 'VARCHAR(120)'),
            ('corregimiento', 'VARCHAR(120)'),
            ('itbms_exempt', 'BOOLEAN NOT NULL DEFAULT false' if dialect == 'postgresql' else 'BOOLEAN NOT NULL DEFAULT 0'),
        )
        for col, typedef in additions:
            if col not in cols:
                try:
                    with engine.begin() as conn:
                        conn.execute(text(f'ALTER TABLE tenant_crm_contact ADD COLUMN {col} {typedef}'))
                    if printfn:
                        printfn(f'+ tenant_crm_contact.{col}')
                except Exception as ex:
                    db.session.rollback()
                    if printfn:
                        printfn(f'! tenant_crm_contact.{col}: {ex}')
                    break

    if 'invoices' in tables:
        icols = {c['name'] for c in insp.get_columns('invoices')}
        if 'billing_contact_id' not in icols:
            db.session.execute(text('ALTER TABLE invoices ADD COLUMN billing_contact_id INTEGER'))
            db.session.commit()
            if printfn:
                printfn('+ invoices.billing_contact_id')
        if 'currency' not in icols:
            db.session.execute(text("ALTER TABLE invoices ADD COLUMN currency VARCHAR(8) NOT NULL DEFAULT 'USD'"))
            db.session.commit()
            if printfn:
                printfn('+ invoices.currency')
        if 'notes' not in icols:
            db.session.execute(text('ALTER TABLE invoices ADD COLUMN notes TEXT'))
            db.session.commit()
            if printfn:
                printfn('+ invoices.notes')

    if 'electronic_invoice_document' in tables:
        ecols = {c['name'] for c in insp.get_columns('electronic_invoice_document')}
        if 'invoice_id' not in ecols:
            db.session.execute(text('ALTER TABLE electronic_invoice_document ADD COLUMN invoice_id INTEGER'))
            db.session.commit()
            if printfn:
                printfn('+ electronic_invoice_document.invoice_id')

    if 'electronic_invoice_provider_config' in tables:
        pcols = {c['name'] for c in insp.get_columns('electronic_invoice_provider_config')}
        for col, typedef in (
            ('emission_mode', "VARCHAR(20) NOT NULL DEFAULT 'manual'"),
            ('emit_on_invoice_confirm', 'BOOLEAN NOT NULL DEFAULT false' if dialect == 'postgresql' else 'BOOLEAN NOT NULL DEFAULT 0'),
            ('emit_on_payment_confirmed', 'BOOLEAN NOT NULL DEFAULT false' if dialect == 'postgresql' else 'BOOLEAN NOT NULL DEFAULT 0'),
        ):
            if col not in pcols:
                db.session.execute(
                    text(f'ALTER TABLE electronic_invoice_provider_config ADD COLUMN {col} {typedef}')
                )
                db.session.commit()
                if printfn:
                    printfn(f'+ electronic_invoice_provider_config.{col}')

    if 'enrollments' in tables:
        encols = {c['name'] for c in insp.get_columns('enrollments')}
        if 'contact_id' not in encols:
            db.session.execute(text('ALTER TABLE enrollments ADD COLUMN contact_id INTEGER'))
            db.session.commit()
            if printfn:
                printfn('+ enrollments.contact_id')
        if 'billing_contact_id' not in encols:
            db.session.execute(text('ALTER TABLE enrollments ADD COLUMN billing_contact_id INTEGER'))
            db.session.commit()
            if printfn:
                printfn('+ enrollments.billing_contact_id')

    if 'students' in tables:
        scols = {c['name'] for c in insp.get_columns('students')}
        if 'contact_id' not in scols:
            db.session.execute(text('ALTER TABLE students ADD COLUMN contact_id INTEGER'))
            db.session.commit()
            if printfn:
                printfn('+ students.contact_id')

    if 'user' in tables:
        ucols = {c['name'] for c in insp.get_columns('user')}
        if 'linked_contact_id' not in ucols:
            db.session.execute(text(f'ALTER TABLE {user_tbl} ADD COLUMN linked_contact_id INTEGER'))
            db.session.commit()
            if printfn:
                printfn('+ user.linked_contact_id')

    try:
        from nodeone.services.crm_tenant_contact_schema import ensure_master_commercial_unification_phase1

        ensure_master_commercial_unification_phase1(db, engine, printfn=printfn)
    except Exception as ex:
        db.session.rollback()
        if printfn:
            printfn(f'! ensure_master_commercial_unification_phase1: {ex}')
