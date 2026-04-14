"""DDL idempotente: columnas comerciales en tenant_crm_contact y vendedor en quotations/invoices."""

from __future__ import annotations

from sqlalchemy import inspect, text


def ensure_crm_salesperson_and_quotation_columns(db, engine, printfn=None) -> None:
    insp = inspect(engine)
    dialect = engine.dialect.name
    tables = set(insp.get_table_names())

    if 'tenant_crm_contact' in tables:
        cols = {c['name'] for c in insp.get_columns('tenant_crm_contact')}
        if 'is_salesperson' not in cols:
            dfl = 'false' if dialect == 'postgresql' else '0'
            db.session.execute(
                text(f'ALTER TABLE tenant_crm_contact ADD COLUMN is_salesperson BOOLEAN NOT NULL DEFAULT {dfl}')
            )
            db.session.commit()
            if printfn:
                printfn('+ tenant_crm_contact.is_salesperson')
        if 'salesperson_code' not in cols:
            db.session.execute(text('ALTER TABLE tenant_crm_contact ADD COLUMN salesperson_code VARCHAR(64)'))
            db.session.commit()
            if printfn:
                printfn('+ tenant_crm_contact.salesperson_code')
        if 'sales_commission_rate' not in cols:
            t = 'DOUBLE PRECISION' if dialect == 'postgresql' else 'REAL'
            db.session.execute(text(f'ALTER TABLE tenant_crm_contact ADD COLUMN sales_commission_rate {t}'))
            db.session.commit()
            if printfn:
                printfn('+ tenant_crm_contact.sales_commission_rate')
        if 'linked_user_id' not in cols:
            db.session.execute(text('ALTER TABLE tenant_crm_contact ADD COLUMN linked_user_id INTEGER'))
            db.session.commit()
            if printfn:
                printfn('+ tenant_crm_contact.linked_user_id')
        if 'is_active' not in cols:
            dfl = 'true' if dialect == 'postgresql' else '1'
            db.session.execute(
                text(f'ALTER TABLE tenant_crm_contact ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT {dfl}')
            )
            db.session.commit()
            if printfn:
                printfn('+ tenant_crm_contact.is_active')

    if 'quotations' in tables:
        cols = {c['name'] for c in insp.get_columns('quotations')}
        if 'salesperson_contact_id' not in cols:
            db.session.execute(text('ALTER TABLE quotations ADD COLUMN salesperson_contact_id INTEGER'))
            db.session.commit()
            if printfn:
                printfn('+ quotations.salesperson_contact_id')
        if 'salesperson_user_id' not in cols:
            db.session.execute(text('ALTER TABLE quotations ADD COLUMN salesperson_user_id INTEGER'))
            db.session.commit()
            if printfn:
                printfn('+ quotations.salesperson_user_id')

    if 'invoices' in tables:
        cols = {c['name'] for c in insp.get_columns('invoices')}
        if 'salesperson_contact_id' not in cols:
            db.session.execute(text('ALTER TABLE invoices ADD COLUMN salesperson_contact_id INTEGER'))
            db.session.commit()
            if printfn:
                printfn('+ invoices.salesperson_contact_id')
        if 'salesperson_user_id' not in cols:
            db.session.execute(text('ALTER TABLE invoices ADD COLUMN salesperson_user_id INTEGER'))
            db.session.commit()
            if printfn:
                printfn('+ invoices.salesperson_user_id')

    if 'user' in tables:
        ucols = {c['name'] for c in insp.get_columns('user')}
        if 'is_salesperson' not in ucols:
            dfl = 'false' if dialect == 'postgresql' else '0'
            # PostgreSQL: "user" es palabra reservada.
            user_tbl = '"user"' if dialect == 'postgresql' else 'user'
            db.session.execute(
                text(f'ALTER TABLE {user_tbl} ADD COLUMN is_salesperson BOOLEAN NOT NULL DEFAULT {dfl}')
            )
            db.session.commit()
            if printfn:
                printfn('+ user.is_salesperson')

    # Migración puntual: contacto CRM con usuario vinculado → salesperson_user_id
    try:
        if 'quotations' in tables and 'tenant_crm_contact' in tables:
            qcols3 = {c['name'] for c in insp.get_columns('quotations')}
            if 'salesperson_user_id' in qcols3 and 'salesperson_contact_id' in qcols3:
                db.session.execute(
                    text(
                        """
                        UPDATE quotations SET salesperson_user_id = (
                            SELECT c.linked_user_id FROM tenant_crm_contact c
                            WHERE c.id = quotations.salesperson_contact_id
                        )
                        WHERE salesperson_contact_id IS NOT NULL
                          AND (salesperson_user_id IS NULL OR salesperson_user_id = 0)
                        """
                    )
                )
                db.session.commit()
    except Exception as ex:
        db.session.rollback()
        if printfn:
            printfn(f'! quotations.salesperson_user_id migrate: {ex}')

    try:
        if 'invoices' in tables and 'tenant_crm_contact' in tables:
            icols = {c['name'] for c in insp.get_columns('invoices')}
            if 'salesperson_user_id' in icols and 'salesperson_contact_id' in icols:
                db.session.execute(
                    text(
                        """
                        UPDATE invoices SET salesperson_user_id = (
                            SELECT c.linked_user_id FROM tenant_crm_contact c
                            WHERE c.id = invoices.salesperson_contact_id
                        )
                        WHERE salesperson_contact_id IS NOT NULL
                          AND (salesperson_user_id IS NULL OR salesperson_user_id = 0)
                        """
                    )
                )
                db.session.commit()
    except Exception as ex:
        db.session.rollback()
        if printfn:
            printfn(f'! invoices.salesperson_user_id migrate: {ex}')
