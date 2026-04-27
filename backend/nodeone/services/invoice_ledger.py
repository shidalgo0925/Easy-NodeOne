"""Factura → asiento contable (Fase 2) cuando el módulo accounting_core está activo."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import or_

from nodeone.core.db import db
from nodeone.modules.accounting.models import Invoice
from nodeone.modules.accounting_core import service as ac_service
from nodeone.services.org_scope import has_saas_module_enabled
from models.accounting_core import Account, Journal, JournalEntry

MONEY_EPS = Decimal('0.009')


def ensure_invoice_ledger_columns() -> None:
    """Añade columnas de enlace a asientos (migración ligera)."""
    from sqlalchemy import inspect, text

    insp = inspect(db.engine)
    if 'invoices' not in insp.get_table_names():
        return
    alters = (
        ('journal_entry_id', 'ALTER TABLE invoices ADD COLUMN journal_entry_id INTEGER'),
        ('payment_journal_entry_id', 'ALTER TABLE invoices ADD COLUMN payment_journal_entry_id INTEGER'),
        ('amount_paid', 'ALTER TABLE invoices ADD COLUMN amount_paid REAL NOT NULL DEFAULT 0'),
    )
    added_amount_paid = False
    for col_name, ddl in alters:
        cols = {c['name'] for c in insp.get_columns('invoices')}
        if col_name not in cols:
            db.session.execute(text(ddl))
            db.session.commit()
            if col_name == 'amount_paid':
                added_amount_paid = True
    if added_amount_paid:
        try:
            db.session.execute(
                text('UPDATE invoices SET amount_paid = grand_total WHERE status = :st'),
                {'st': 'paid'},
            )
            db.session.commit()
        except Exception:
            db.session.rollback()


def ensure_invoice_journal_entry_column() -> None:
    """Compat: migración columnas factura ↔ libro mayor."""
    ensure_invoice_ledger_columns()


def _dec(v) -> Decimal:
    try:
        return Decimal(str(v if v is not None else 0)).quantize(Decimal('0.01'))
    except Exception:
        return Decimal('0.00')


def invoice_amount_paid(inv: Invoice) -> Decimal:
    return _dec(getattr(inv, 'amount_paid', None))


def invoice_residual(inv: Invoice) -> Decimal:
    return max(_dec(inv.grand_total) - invoice_amount_paid(inv), Decimal('0.00'))


def _account_by_codes(organization_id: int, codes: tuple[str, ...]) -> Account | None:
    for code in codes:
        row = Account.query.filter_by(
            organization_id=int(organization_id), code=code, is_active=True
        ).first()
        if row:
            return row
    return None


def _first_income_like(organization_id: int) -> Account | None:
    return (
        Account.query.filter(
            Account.organization_id == int(organization_id),
            Account.type == 'income',
            Account.is_active.is_(True),
        )
        .order_by(Account.code.asc())
        .first()
    )


def _first_tax_payable(organization_id: int) -> Account | None:
    q = Account.query.filter(
        Account.organization_id == int(organization_id),
        Account.type == 'liability',
        Account.is_active.is_(True),
    )
    for row in q.order_by(Account.code.asc()).all():
        name = (row.name or '').lower()
        code = (row.code or '')
        if 'itbms' in name or code.startswith('231'):
            return row
    return None


def resolve_invoice_posting_accounts(organization_id: int) -> tuple[Account, Account, Account | None]:
    """Cuentas por defecto según plan importado (códigos típicos Panamá) o primeras por tipo."""
    oid = int(organization_id)
    ar = _account_by_codes(oid, ('1210000', '121.010', '1200', '1200000'))
    if ar is None:
        ar = (
            Account.query.filter(
                Account.organization_id == oid,
                Account.type == 'asset',
                Account.is_active.is_(True),
            )
            .filter(or_(Account.code == '1210000', Account.name.ilike('%deudores por ventas%')))
            .order_by(Account.code.asc())
            .first()
        )
    if ar is None:
        raise ValueError(
            'No se encontró cuenta de cuentas por cobrar (códigos 1210000 / 121.010 o similar). '
            'Importe el plan de cuentas o cree la cuenta en Contabilidad.'
        )
    rev = _account_by_codes(oid, ('411.010', '411010', '4100', '4100000'))
    if rev is None:
        rev = _first_income_like(oid)
    if rev is None:
        raise ValueError(
            'No se encontró cuenta de ingresos por ventas. Importe el plan de cuentas o cree una cuenta tipo ingreso.'
        )
    tax_acc = _account_by_codes(oid, ('2310000', '231000'))
    if tax_acc is None:
        tax_acc = _first_tax_payable(oid)
    return ar, rev, tax_acc


def posting_readiness_for_org(organization_id: int) -> dict:
    """
    Indica si al **validar** una factura se podrá generar asiento (Fase 2).
    Si ``accounting_core`` está apagado para la org, no aplica (``applicable=False``).
    """
    oid = int(organization_id)
    if not has_saas_module_enabled(oid, 'accounting_core'):
        return {'applicable': False, 'ok': True, 'message': None}
    try:
        resolve_invoice_posting_accounts(oid)
        return {'applicable': True, 'ok': True, 'message': None}
    except ValueError as e:
        return {'applicable': True, 'ok': False, 'message': str(e)}


def ensure_sale_journal(organization_id: int, default_account_id: int | None) -> Journal:
    oid = int(organization_id)
    j = (
        Journal.query.filter_by(organization_id=oid, type='sale', is_active=True)
        .order_by(Journal.id.asc())
        .first()
    )
    if j:
        return j
    j = Journal(
        organization_id=oid,
        code='INV',
        name='Facturas de venta',
        type='sale',
        default_account_id=default_account_id,
        is_active=True,
    )
    db.session.add(j)
    db.session.flush()
    return j


def create_and_post_invoice_entry(inv: Invoice, user_id: int | None) -> JournalEntry:
    """
    Crea y publica el asiento: Debe CxC = total factura; Haber ingreso = neto; Haber ITBMS si aplica.
    Usar dentro de una transacción junto con el cambio de estado de la factura (commit=False en draft/post).
    """
    ac_service.ensure_accounting_core_schema()
    oid = int(inv.organization_id)
    g = _dec(inv.grand_total)
    if g <= 0:
        raise ValueError('La factura no tiene importe mayor a cero; no se puede contabilizar.')
    ar, rev, tax_acc = resolve_invoice_posting_accounts(oid)
    tax_amt = _dec(inv.tax_total)
    if tax_amt > 0 and tax_acc is None:
        raise ValueError(
            'La factura tiene impuestos pero no hay cuenta de impuestos por pagar (p. ej. 2310000 ITBMS).'
        )
    revenue_amt = g - tax_amt
    if revenue_amt < 0:
        revenue_amt = Decimal('0.00')
    j = ensure_sale_journal(oid, ar.id)
    when = inv.date.date() if getattr(inv, 'date', None) else datetime.utcnow().date()
    ref = (inv.number or '').strip() or f'INV-{inv.id}'
    lines: list[dict] = [
        {
            'account_id': ar.id,
            'debit': float(g),
            'credit': 0,
            'partner_id': int(inv.customer_id),
            'description': f'Factura {ref}',
        },
        {
            'account_id': rev.id,
            'debit': 0,
            'credit': float(revenue_amt),
            'partner_id': int(inv.customer_id),
            'description': f'Ingreso factura {ref}',
        },
    ]
    if tax_amt > 0 and tax_acc is not None:
        lines.append(
            {
                'account_id': tax_acc.id,
                'debit': 0,
                'credit': float(tax_amt),
                'partner_id': int(inv.customer_id),
                'description': f'ITBMS factura {ref}',
            }
        )
    entry = ac_service.create_entry_draft(
        oid,
        j.id,
        {
            'date': when.isoformat(),
            'reference': ref,
            'source_model': 'accounting.invoice',
            'source_id': int(inv.id),
            'lines': lines,
        },
        user_id=user_id,
        commit=False,
    )
    ac_service.post_entry(entry, user_id=user_id, commit=False)
    return entry


def resolve_bank_liquid_account(organization_id: int) -> Account:
    """Cuenta de efectivo/banco donde se deposita el cobro (activo)."""
    oid = int(organization_id)
    for code in ('111.001', '111.002', '1110000', '114.001', '113.001', '1150000', '1160000'):
        a = _account_by_codes(oid, (code,))
        if a:
            return a
    for j in (
        Journal.query.filter_by(organization_id=oid, type='bank', is_active=True)
        .order_by(Journal.id.asc())
        .all()
    ):
        if j.default_account_id:
            a = Account.query.filter_by(id=j.default_account_id, organization_id=oid, is_active=True).first()
            if a is not None and a.type == 'asset':
                return a
    for j in (
        Journal.query.filter_by(organization_id=oid, type='cash', is_active=True)
        .order_by(Journal.id.asc())
        .all()
    ):
        if j.default_account_id:
            a = Account.query.filter_by(id=j.default_account_id, organization_id=oid, is_active=True).first()
            if a is not None and a.type == 'asset':
                return a
    raise ValueError(
        'No se encontró cuenta de banco/caja para el cobro (p. ej. 111.001). '
        'Configure un diario tipo Banco con cuenta por defecto o importe el plan de cuentas.'
    )


def pick_bank_journal_for_collections(organization_id: int, liquid_account_id: int) -> Journal:
    oid = int(organization_id)
    j = (
        Journal.query.filter_by(organization_id=oid, type='bank', is_active=True)
        .order_by(Journal.id.asc())
        .first()
    )
    if j:
        return j
    j = (
        Journal.query.filter_by(organization_id=oid, type='cash', is_active=True)
        .order_by(Journal.id.asc())
        .first()
    )
    if j:
        return j
    j = Journal(
        organization_id=oid,
        code='BNK-REC',
        name='Recaudaciones banco',
        type='bank',
        default_account_id=int(liquid_account_id),
        is_active=True,
    )
    db.session.add(j)
    db.session.flush()
    return j


def create_and_post_payment_entry(inv: Invoice, user_id: int | None, pay_amount: Decimal) -> JournalEntry:
    """Debe banco/caja; Haber CxC (misma cuenta que el reconocimiento de venta)."""
    ac_service.ensure_accounting_core_schema()
    oid = int(inv.organization_id)
    amt = _dec(pay_amount)
    if amt <= 0:
        raise ValueError('Importe de cobro no válido.')
    ar, _, _ = resolve_invoice_posting_accounts(oid)
    bank_acc = resolve_bank_liquid_account(oid)
    j = pick_bank_journal_for_collections(oid, bank_acc.id)
    ref = (inv.number or '').strip() or f'INV-{inv.id}'
    n = (
        JournalEntry.query.filter_by(
            organization_id=oid,
            source_model='accounting.invoice_payment',
            source_id=int(inv.id),
        ).count()
    )
    pay_ref = f'COBRO-{ref}-{(n + 1):02d}'
    when = datetime.utcnow().date()
    lines: list[dict] = [
        {
            'account_id': bank_acc.id,
            'debit': float(amt),
            'credit': 0,
            'partner_id': int(inv.customer_id),
            'description': f'Cobro factura {ref}',
        },
        {
            'account_id': ar.id,
            'debit': 0,
            'credit': float(amt),
            'partner_id': int(inv.customer_id),
            'description': f'Liquidación CxC factura {ref}',
        },
    ]
    entry = ac_service.create_entry_draft(
        oid,
        j.id,
        {
            'date': when.isoformat(),
            'reference': pay_ref,
            'source_model': 'accounting.invoice_payment',
            'source_id': int(inv.id),
            'lines': lines,
        },
        user_id=user_id,
        commit=False,
    )
    ac_service.post_entry(entry, user_id=user_id, commit=False)
    return entry


def attach_payment_ledger_if_accounting_core(
    inv: Invoice, user_id: int | None, pay_amount: Decimal | None = None
) -> None:
    """Si hay asiento de venta y accounting_core activo, registra cobro banco vs CxC (cada pago = un asiento)."""
    oid = int(inv.organization_id)
    if not has_saas_module_enabled(oid, 'accounting_core'):
        return
    if not getattr(inv, 'journal_entry_id', None):
        return
    res = invoice_residual(inv)
    amt = _dec(pay_amount) if pay_amount is not None else res
    if amt <= 0:
        raise ValueError('El importe del cobro debe ser mayor a cero.')
    if amt > res + MONEY_EPS:
        raise ValueError('El importe no puede superar el saldo pendiente de la factura.')
    entry = create_and_post_payment_entry(inv, user_id=user_id, pay_amount=amt)
    inv.payment_journal_entry_id = int(entry.id)


def attach_invoice_ledger_if_accounting_core(inv: Invoice, user_id: int | None) -> None:
    """Si accounting_core está activo para la org, exige asiento contable al validar la factura."""
    oid = int(inv.organization_id)
    if not has_saas_module_enabled(oid, 'accounting_core'):
        return
    entry = create_and_post_invoice_entry(inv, user_id=user_id)
    inv.journal_entry_id = int(entry.id)


def reverse_payment_ledger_entry_if_any(inv: Invoice, user_id: int | None) -> None:
    """Reversa todos los asientos de cobro vinculados a la factura (más reciente primero)."""
    oid = int(inv.organization_id)
    if not has_saas_module_enabled(oid, 'accounting_core'):
        return
    ac_service.ensure_accounting_core_schema()
    entries = (
        JournalEntry.query.filter(
            JournalEntry.organization_id == oid,
            JournalEntry.source_model == 'accounting.invoice_payment',
            JournalEntry.source_id == int(inv.id),
            JournalEntry.state == 'posted',
        )
        .order_by(JournalEntry.id.desc())
        .all()
    )
    if not entries and getattr(inv, 'payment_journal_entry_id', None):
        legacy = JournalEntry.query.filter_by(
            id=int(inv.payment_journal_entry_id), organization_id=oid
        ).first()
        if legacy and legacy.state == 'posted':
            entries = [legacy]
    for entry in entries:
        ac_service.reverse_entry(entry, user_id=user_id)


def reverse_invoice_ledger_entry_if_any(inv: Invoice, user_id: int | None) -> None:
    """Reversa el asiento de venta vinculado si existe y está publicado."""
    eid = getattr(inv, 'journal_entry_id', None)
    if not eid:
        return
    oid = int(inv.organization_id)
    if not has_saas_module_enabled(oid, 'accounting_core'):
        return
    ac_service.ensure_accounting_core_schema()
    entry = JournalEntry.query.filter_by(id=int(eid), organization_id=oid).first()
    if entry is None or entry.state != 'posted':
        return
    ac_service.reverse_entry(entry, user_id=user_id)
