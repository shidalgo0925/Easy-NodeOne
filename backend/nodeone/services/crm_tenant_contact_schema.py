"""DDL idempotente: columnas comerciales en tenant_crm_contact, vendedor en quotations/invoices,
y Fase 1 del Plan Maestro (contacto maestro ↔ ventas ↔ CRM)."""

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

    try:
        ensure_master_commercial_unification_phase1(db, engine, printfn=printfn)
    except Exception as ex:
        db.session.rollback()
        if printfn:
            printfn(f'! ensure_master_commercial_unification_phase1: {ex}')


def ensure_master_commercial_unification_phase1(db, engine, printfn=None) -> None:
    """Plan Maestro Fase 1: columnas nuevas sin romper customer_id / user_id existentes."""
    insp = inspect(engine)
    dialect = engine.dialect.name
    tables = set(insp.get_table_names())
    user_tbl = '"user"' if dialect == 'postgresql' else 'user'

    if 'tenant_crm_contact' in tables:
        cols = {c['name'] for c in insp.get_columns('tenant_crm_contact')}
        if 'is_customer' not in cols:
            dfl = 'true' if dialect == 'postgresql' else '1'
            db.session.execute(
                text(f'ALTER TABLE tenant_crm_contact ADD COLUMN is_customer BOOLEAN NOT NULL DEFAULT {dfl}')
            )
            db.session.commit()
            if printfn:
                printfn('+ tenant_crm_contact.is_customer')
        if 'is_supplier' not in cols:
            dfl = 'false' if dialect == 'postgresql' else '0'
            db.session.execute(
                text(f'ALTER TABLE tenant_crm_contact ADD COLUMN is_supplier BOOLEAN NOT NULL DEFAULT {dfl}')
            )
            db.session.commit()
            if printfn:
                printfn('+ tenant_crm_contact.is_supplier')
        if 'external_id' not in cols:
            db.session.execute(text('ALTER TABLE tenant_crm_contact ADD COLUMN external_id VARCHAR(120)'))
            db.session.commit()
            if printfn:
                printfn('+ tenant_crm_contact.external_id')

    if 'user' in tables:
        ucols = {c['name'] for c in insp.get_columns('user')}
        if 'linked_contact_id' not in ucols:
            db.session.execute(text(f'ALTER TABLE {user_tbl} ADD COLUMN linked_contact_id INTEGER'))
            db.session.commit()
            if printfn:
                printfn('+ user.linked_contact_id')

    if 'quotations' in tables:
        qcols = {c['name'] for c in insp.get_columns('quotations')}
        if 'customer_contact_id' not in qcols:
            db.session.execute(text('ALTER TABLE quotations ADD COLUMN customer_contact_id INTEGER'))
            db.session.commit()
            if printfn:
                printfn('+ quotations.customer_contact_id')

    if 'invoices' in tables:
        icols = {c['name'] for c in insp.get_columns('invoices')}
        if 'customer_contact_id' not in icols:
            db.session.execute(text('ALTER TABLE invoices ADD COLUMN customer_contact_id INTEGER'))
            db.session.commit()
            if printfn:
                printfn('+ invoices.customer_contact_id')

    if 'crm_lead' in tables:
        lcols = {c['name'] for c in insp.get_columns('crm_lead')}
        if 'contact_id' not in lcols:
            db.session.execute(text('ALTER TABLE crm_lead ADD COLUMN contact_id INTEGER'))
            db.session.commit()
            if printfn:
                printfn('+ crm_lead.contact_id')

    # Índice único parcial: un contacto vinculado por usuario y organización.
    if 'tenant_crm_contact' in tables:
        try:
            idx_sql = (
                'CREATE UNIQUE INDEX IF NOT EXISTS uq_tenant_crm_contact_org_linked_user '
                'ON tenant_crm_contact (organization_id, linked_user_id) '
                'WHERE linked_user_id IS NOT NULL'
            )
            db.session.execute(text(idx_sql))
            db.session.commit()
            if printfn:
                printfn('+ index uq_tenant_crm_contact_org_linked_user')
        except Exception as ex:
            db.session.rollback()
            if printfn:
                printfn(f'! uq_tenant_crm_contact_org_linked_user: {ex}')

    # Vendedores puros: no marcarlos como clientes por defecto.
    try:
        if 'tenant_crm_contact' in tables:
            scols = {c['name'] for c in insp.get_columns('tenant_crm_contact')}
            if 'is_customer' in scols and 'is_salesperson' in scols:
                if dialect == 'postgresql':
                    db.session.execute(
                        text(
                            'UPDATE tenant_crm_contact SET is_customer = false '
                            'WHERE is_salesperson = true AND is_customer = true'
                        )
                    )
                else:
                    db.session.execute(
                        text(
                            "UPDATE tenant_crm_contact SET is_customer = 0 "
                            "WHERE is_salesperson = 1 AND is_customer = 1"
                        )
                    )
                db.session.commit()
    except Exception as ex:
        db.session.rollback()
        if printfn:
            printfn(f'! tenant_crm_contact is_customer backfill: {ex}')

    # Backfill: cotizaciones / facturas → contacto por usuario vinculado.
    try:
        if 'quotations' in tables and 'tenant_crm_contact' in tables:
            qcols2 = {c['name'] for c in insp.get_columns('quotations')}
            if 'customer_contact_id' in qcols2:
                db.session.execute(
                    text(
                        """
                        UPDATE quotations SET customer_contact_id = (
                            SELECT c.id FROM tenant_crm_contact c
                            WHERE c.organization_id = quotations.organization_id
                              AND c.linked_user_id = quotations.customer_id
                            ORDER BY c.id ASC LIMIT 1
                        )
                        WHERE customer_contact_id IS NULL AND customer_id IS NOT NULL
                        """
                    )
                )
                db.session.commit()
    except Exception as ex:
        db.session.rollback()
        if printfn:
            printfn(f'! quotations.customer_contact_id backfill: {ex}')

    try:
        if 'invoices' in tables and 'tenant_crm_contact' in tables:
            icols2 = {c['name'] for c in insp.get_columns('invoices')}
            if 'customer_contact_id' in icols2:
                db.session.execute(
                    text(
                        """
                        UPDATE invoices SET customer_contact_id = (
                            SELECT c.id FROM tenant_crm_contact c
                            WHERE c.organization_id = invoices.organization_id
                              AND c.linked_user_id = invoices.customer_id
                            ORDER BY c.id ASC LIMIT 1
                        )
                        WHERE customer_contact_id IS NULL AND customer_id IS NOT NULL
                        """
                    )
                )
                db.session.commit()
    except Exception as ex:
        db.session.rollback()
        if printfn:
            printfn(f'! invoices.customer_contact_id backfill: {ex}')

    # user.linked_contact_id espejo del contacto que ya apunta al usuario.
    try:
        if 'user' in tables and 'tenant_crm_contact' in tables:
            ucols2 = {c['name'] for c in insp.get_columns('user')}
            if 'linked_contact_id' in ucols2:
                db.session.execute(
                    text(
                        f"""
                        UPDATE {user_tbl} u SET linked_contact_id = (
                            SELECT c.id FROM tenant_crm_contact c
                            WHERE c.linked_user_id = u.id
                            ORDER BY c.id DESC LIMIT 1
                        )
                        WHERE u.linked_contact_id IS NULL
                          AND EXISTS (
                              SELECT 1 FROM tenant_crm_contact c2
                              WHERE c2.linked_user_id = u.id LIMIT 1
                          )
                        """
                    )
                )
                db.session.commit()
    except Exception as ex:
        db.session.rollback()
        if printfn:
            printfn(f'! user.linked_contact_id backfill: {ex}')

    # Leads → contacto por email normalizado (primer match por org).
    try:
        if 'crm_lead' in tables and 'tenant_crm_contact' in tables:
            lcols2 = {c['name'] for c in insp.get_columns('crm_lead')}
            if 'contact_id' in lcols2:
                db.session.execute(
                    text(
                        """
                        UPDATE crm_lead SET contact_id = (
                            SELECT c.id FROM tenant_crm_contact c
                            WHERE c.organization_id = crm_lead.organization_id
                              AND crm_lead.email IS NOT NULL AND length(trim(crm_lead.email)) > 0
                              AND c.email IS NOT NULL AND length(trim(c.email)) > 0
                              AND lower(trim(c.email)) = lower(trim(crm_lead.email))
                            ORDER BY c.id ASC LIMIT 1
                        )
                        WHERE contact_id IS NULL
                          AND email IS NOT NULL AND length(trim(email)) > 0
                        """
                    )
                )
                db.session.commit()
    except Exception as ex:
        db.session.rollback()
        if printfn:
            printfn(f'! crm_lead.contact_id backfill: {ex}')
