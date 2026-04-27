"""Servicios del motor contable ERP (Fase 1)."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from sqlalchemy import inspect, text

from nodeone.core.db import db
from models.accounting_adjustments import AccountingAdjustment
from models.accounting_core import Account, Journal, JournalEntry, JournalItem

ACCOUNT_TYPES = {'asset', 'liability', 'equity', 'income', 'expense'}
JOURNAL_TYPES = {'sale', 'purchase', 'bank', 'cash', 'general'}
ADJUSTMENT_TYPES = {'depreciation', 'provision', 'reclass', 'fx', 'inventory', 'closing'}


def ensure_accounting_core_schema() -> None:
    """Crea tablas núcleo si aún no existen (migración progresiva)."""
    Account.__table__.create(db.engine, checkfirst=True)
    Journal.__table__.create(db.engine, checkfirst=True)
    JournalEntry.__table__.create(db.engine, checkfirst=True)
    JournalItem.__table__.create(db.engine, checkfirst=True)
    AccountingAdjustment.__table__.create(db.engine, checkfirst=True)
    insp = inspect(db.engine)
    cols = {c['name'] for c in insp.get_columns('account')}
    if 'allow_reconcile' not in cols:
        db.session.execute(text("ALTER TABLE account ADD COLUMN allow_reconcile BOOLEAN NOT NULL DEFAULT FALSE"))
    if 'currency_code' not in cols:
        db.session.execute(text("ALTER TABLE account ADD COLUMN currency_code VARCHAR(16)"))
    db.session.commit()


def _to_decimal(raw) -> Decimal:
    try:
        val = Decimal(str(raw if raw is not None else 0)).quantize(Decimal('0.01'))
    except (InvalidOperation, ValueError, TypeError):
        val = Decimal('0.00')
    return val


def _validate_line_payload(line: dict) -> tuple[int, Decimal, Decimal]:
    account_id = int(line.get('account_id') or 0)
    if account_id < 1:
        raise ValueError('Cada línea requiere account_id válido.')
    debit = _to_decimal(line.get('debit'))
    credit = _to_decimal(line.get('credit'))
    if debit < 0 or credit < 0:
        raise ValueError('No se aceptan valores negativos en débito/crédito.')
    if debit > 0 and credit > 0:
        raise ValueError('Una línea no puede tener débito y crédito simultáneamente.')
    if debit == 0 and credit == 0:
        raise ValueError('Cada línea debe tener débito o crédito mayor que cero.')
    return account_id, debit, credit


def build_entry_totals(entry: JournalEntry) -> tuple[Decimal, Decimal]:
    debit_total = Decimal('0.00')
    credit_total = Decimal('0.00')
    for item in entry.items.order_by(JournalItem.id.asc()).all():
        debit_total += _to_decimal(item.debit)
        credit_total += _to_decimal(item.credit)
    return debit_total, credit_total


def create_account(organization_id: int, data: dict) -> Account:
    acc_type = (data.get('type') or '').strip().lower()
    if acc_type not in ACCOUNT_TYPES:
        raise ValueError('Tipo de cuenta no válido.')
    code = (data.get('code') or '').strip()
    name = (data.get('name') or '').strip()
    if not code or not name:
        raise ValueError('Cuenta requiere código y nombre.')
    row = Account(
        organization_id=int(organization_id),
        code=code,
        name=name,
        type=acc_type,
        allow_reconcile=bool(int(data.get('allow_reconcile') or 0)) if str(data.get('allow_reconcile', '')).isdigit() else bool(data.get('allow_reconcile', False)),
        currency_code=((data.get('currency_code') or '').strip()[:16] or None),
        is_active=bool(data.get('is_active', True)),
    )
    db.session.add(row)
    db.session.commit()
    return row


def create_journal(organization_id: int, data: dict) -> Journal:
    j_type = (data.get('type') or '').strip().lower()
    if j_type not in JOURNAL_TYPES:
        raise ValueError('Tipo de diario no válido.')
    code = (data.get('code') or '').strip()
    name = (data.get('name') or '').strip()
    if not code or not name:
        raise ValueError('Diario requiere código y nombre.')
    default_account_id = data.get('default_account_id')
    default_account_id = int(default_account_id) if default_account_id not in (None, '') else None
    if default_account_id:
        acc = Account.query.filter_by(id=default_account_id, organization_id=int(organization_id)).first()
        if acc is None:
            raise ValueError('Cuenta por defecto no existe en esta organización.')
    row = Journal(
        organization_id=int(organization_id),
        code=code,
        name=name,
        type=j_type,
        default_account_id=default_account_id,
        is_active=bool(data.get('is_active', True)),
    )
    db.session.add(row)
    db.session.commit()
    return row


def create_entry_draft(
    organization_id: int, journal_id: int, payload: dict, user_id: int | None = None, *, commit: bool = True
) -> JournalEntry:
    journal = Journal.query.filter_by(id=int(journal_id), organization_id=int(organization_id), is_active=True).first()
    if journal is None:
        raise ValueError('Diario no existe o está inactivo.')
    raw_date = payload.get('date')
    if raw_date:
        when = datetime.fromisoformat(str(raw_date)).date()
    else:
        when = date.today()
    entry = JournalEntry(
        organization_id=int(organization_id),
        journal_id=journal.id,
        date=when,
        reference=(payload.get('reference') or '').strip() or None,
        source_model=(payload.get('source_model') or '').strip() or None,
        source_id=int(payload.get('source_id')) if payload.get('source_id') not in (None, '') else None,
        state='draft',
        created_by=int(user_id) if user_id else None,
    )
    db.session.add(entry)
    db.session.flush()
    for line in payload.get('lines') or []:
        account_id, debit, credit = _validate_line_payload(line)
        account = Account.query.filter_by(id=account_id, organization_id=int(organization_id), is_active=True).first()
        if account is None:
            raise ValueError('Cuenta contable no encontrada o inactiva.')
        db.session.add(
            JournalItem(
                entry_id=entry.id,
                account_id=account_id,
                partner_id=int(line.get('partner_id')) if line.get('partner_id') not in (None, '') else None,
                debit=debit,
                credit=credit,
                description=(line.get('description') or '').strip() or None,
            )
        )
    if commit:
        db.session.commit()
    else:
        db.session.flush()
    return entry


def replace_entry_draft_lines(entry: JournalEntry, organization_id: int, lines: list[dict]) -> JournalEntry:
    if entry.state != 'draft':
        raise ValueError('Solo se puede editar un asiento en borrador.')
    JournalItem.query.filter_by(entry_id=entry.id).delete(synchronize_session=False)
    for line in lines:
        account_id, debit, credit = _validate_line_payload(line)
        account = Account.query.filter_by(id=account_id, organization_id=int(organization_id), is_active=True).first()
        if account is None:
            raise ValueError('Cuenta contable no encontrada o inactiva.')
        db.session.add(
            JournalItem(
                entry_id=entry.id,
                account_id=account_id,
                partner_id=int(line.get('partner_id')) if line.get('partner_id') not in (None, '') else None,
                debit=debit,
                credit=credit,
                description=(line.get('description') or '').strip() or None,
            )
        )
    db.session.commit()
    return entry


def validate_entry_for_post(entry: JournalEntry) -> tuple[Decimal, Decimal]:
    if entry.state != 'draft':
        raise ValueError('Solo se puede publicar un asiento en borrador.')
    lines = entry.items.order_by(JournalItem.id.asc()).all()
    if len(lines) < 2:
        raise ValueError('Un asiento requiere al menos dos líneas.')
    debit_total = Decimal('0.00')
    credit_total = Decimal('0.00')
    for ln in lines:
        debit = _to_decimal(ln.debit)
        credit = _to_decimal(ln.credit)
        if debit < 0 or credit < 0:
            raise ValueError('No se aceptan valores negativos.')
        if debit > 0 and credit > 0:
            raise ValueError('Una línea no puede tener ambos lados.')
        if debit == 0 and credit == 0:
            raise ValueError('Una línea no puede quedar vacía.')
        debit_total += debit
        credit_total += credit
    if debit_total != credit_total:
        raise ValueError(f'Asiento desbalanceado: debe={debit_total} haber={credit_total}.')
    return debit_total, credit_total


def post_entry(entry: JournalEntry, user_id: int | None, *, commit: bool = True) -> JournalEntry:
    validate_entry_for_post(entry)
    entry.state = 'posted'
    entry.posted_by = int(user_id) if user_id else None
    entry.posted_at = datetime.utcnow()
    db.session.add(entry)
    if commit:
        db.session.commit()
    else:
        db.session.flush()
    return entry


def reverse_entry(entry: JournalEntry, user_id: int | None, reverse_date: date | None = None) -> JournalEntry:
    if entry.state != 'posted':
        raise ValueError('Solo se puede reversar un asiento publicado.')
    rev = JournalEntry(
        organization_id=entry.organization_id,
        journal_id=entry.journal_id,
        date=reverse_date or date.today(),
        reference=f"REV-{entry.id}: {(entry.reference or '').strip()}".strip(),
        source_model='journal_entry_reverse',
        source_id=entry.id,
        state='draft',
        created_by=int(user_id) if user_id else None,
    )
    db.session.add(rev)
    db.session.flush()
    for ln in entry.items.order_by(JournalItem.id.asc()).all():
        db.session.add(
            JournalItem(
                entry_id=rev.id,
                account_id=ln.account_id,
                partner_id=ln.partner_id,
                debit=_to_decimal(ln.credit),
                credit=_to_decimal(ln.debit),
                description=(ln.description or '').strip() or f'Reverso de asiento #{entry.id}',
            )
        )
    db.session.flush()
    post_entry(rev, user_id=user_id, commit=True)
    entry.state = 'reversed'
    entry.reversed_by_entry_id = rev.id
    db.session.add(entry)
    db.session.commit()
    return rev


def create_adjustment(organization_id: int, data: dict, user_id: int | None = None) -> AccountingAdjustment:
    adj_type = (data.get('adjustment_type') or '').strip().lower()
    if adj_type not in ADJUSTMENT_TYPES:
        raise ValueError('Tipo de ajuste no válido.')
    name = (data.get('name') or '').strip()
    if not name:
        raise ValueError('El ajuste requiere nombre.')
    journal_id = int(data.get('journal_id') or 0)
    debit_account_id = int(data.get('debit_account_id') or 0)
    credit_account_id = int(data.get('credit_account_id') or 0)
    if journal_id < 1 or debit_account_id < 1 or credit_account_id < 1:
        raise ValueError('Diario y cuentas son obligatorios.')
    if debit_account_id == credit_account_id:
        raise ValueError('La cuenta débito y crédito deben ser distintas.')
    amount = _to_decimal(data.get('amount'))
    if amount <= 0:
        raise ValueError('El monto del ajuste debe ser mayor a cero.')

    journal = Journal.query.filter_by(id=journal_id, organization_id=int(organization_id), is_active=True).first()
    if journal is None:
        raise ValueError('Diario no existe o está inactivo en esta organización.')
    debit_account = Account.query.filter_by(
        id=debit_account_id, organization_id=int(organization_id), is_active=True
    ).first()
    credit_account = Account.query.filter_by(
        id=credit_account_id, organization_id=int(organization_id), is_active=True
    ).first()
    if debit_account is None or credit_account is None:
        raise ValueError('Cuenta débito/crédito inválida o inactiva.')

    raw_date = data.get('adjustment_date')
    when = datetime.fromisoformat(str(raw_date)).date() if raw_date else date.today()
    row = AccountingAdjustment(
        organization_id=int(organization_id),
        name=name,
        adjustment_type=adj_type,
        adjustment_date=when,
        journal_id=journal_id,
        debit_account_id=debit_account_id,
        credit_account_id=credit_account_id,
        amount=amount,
        description=(data.get('description') or '').strip() or None,
        state='draft',
        created_by=int(user_id) if user_id else None,
    )
    db.session.add(row)
    db.session.commit()
    return row


def apply_adjustment(adjustment: AccountingAdjustment, user_id: int | None = None) -> JournalEntry:
    if adjustment.state != 'draft':
        raise ValueError('Solo se puede aplicar un ajuste en borrador.')
    entry = create_entry_draft(
        adjustment.organization_id,
        adjustment.journal_id,
        {
            'date': adjustment.adjustment_date.isoformat(),
            'reference': f"AJ-{adjustment.id}: {adjustment.name}",
            'source_model': 'accounting_adjustment',
            'source_id': adjustment.id,
            'lines': [
                {
                    'account_id': adjustment.debit_account_id,
                    'debit': adjustment.amount,
                    'credit': 0,
                    'description': adjustment.description or adjustment.name,
                },
                {
                    'account_id': adjustment.credit_account_id,
                    'debit': 0,
                    'credit': adjustment.amount,
                    'description': adjustment.description or adjustment.name,
                },
            ],
        },
        user_id=user_id,
        commit=True,
    )
    post_entry(entry, user_id=user_id, commit=True)
    adjustment.state = 'applied'
    adjustment.applied_entry_id = entry.id
    adjustment.applied_at = datetime.utcnow()
    db.session.add(adjustment)
    db.session.commit()
    return entry
