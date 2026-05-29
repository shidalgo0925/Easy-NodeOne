"""DDL idempotente: tabla maestro en1_contact."""

from __future__ import annotations

from sqlalchemy import inspect, text


def ensure_contacts_schema(db, engine, printfn=None) -> None:
    from models.contact import Contact

    Contact.__table__.create(engine, checkfirst=True)
    if printfn:
        printfn('en1_contact: tabla lista')

    insp = inspect(engine)
    if 'en1_contact' not in insp.get_table_names():
        return
    dialect = engine.dialect.name
    # Índice único fiscal parcial (no aplica a consumidor final sin RUC)
    idx_name = 'uq_en1_contact_org_fiscal'
    idx_sql = (
        f"""
        CREATE UNIQUE INDEX IF NOT EXISTS {idx_name}
        ON en1_contact (organization_id, identification_type, tax_id, COALESCE(dv, ''))
        WHERE tax_id IS NOT NULL AND {"TRIM(tax_id) <> ''" if dialect == 'postgresql' else "tax_id <> ''"}
          AND identification_type <> 'consumer_final'
        """
    )
    try:
        # DDL en conexión aparte: no heredar transacción abortada del request.
        with engine.begin() as conn:
            conn.execute(text(idx_sql))
        if printfn:
            printfn(f'+ index {idx_name}')
    except Exception as ex:
        if printfn:
            printfn(f'! {idx_name}: {ex}')

    if 'invoices' in insp.get_table_names():
        icols = {c['name'] for c in insp.get_columns('invoices')}
        if 'contact_id' not in icols:
            try:
                with engine.begin() as conn:
                    conn.execute(text('ALTER TABLE invoices ADD COLUMN contact_id INTEGER'))
                if printfn:
                    printfn('+ invoices.contact_id')
            except Exception as ex:
                if printfn:
                    printfn(f'! invoices.contact_id: {ex}')

    if 'quotations' in insp.get_table_names():
        qcols = {c['name'] for c in insp.get_columns('quotations')}
        if 'contact_id' not in qcols:
            try:
                with engine.begin() as conn:
                    conn.execute(text('ALTER TABLE quotations ADD COLUMN contact_id INTEGER'))
                if printfn:
                    printfn('+ quotations.contact_id')
            except Exception as ex:
                if printfn:
                    printfn(f'! quotations.contact_id: {ex}')
