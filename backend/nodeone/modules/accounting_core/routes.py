"""Rutas admin del núcleo contable (Fase 1)."""

from __future__ import annotations

from datetime import datetime

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import func, or_

from app import admin_data_scope_organization_id, admin_required, default_organization_id, has_saas_module_enabled
from saas_features import enforce_saas_module_or_response
from models.accounting_adjustments import AccountingAdjustment
from models.accounting_core import Account, Journal, JournalEntry, JournalItem
from models.saas import SaasOrganization
from models.saas import SaasModule
from models.users import User
from nodeone.core.db import db
from nodeone.modules.accounting.models import Invoice
from nodeone.modules.accounting_core import service
from nodeone.services.user_organization import user_in_org_clause

accounting_core_bp = Blueprint('accounting_core', __name__, url_prefix='/admin/accounting-core')


@accounting_core_bp.before_request
def _ensure_schema():
    service.ensure_accounting_core_schema()


@accounting_core_bp.before_request
def _guard_saas_accounting_core():
    """Mismo criterio que el menú Contabilidad: accounting_core, o sales si aún no hay fila en catálogo."""
    if not current_user.is_authenticated:
        return None
    if getattr(current_user, 'is_admin', False):
        return None
    oid = _org_id()
    if _saas_chain_enabled(oid, 'accounting_core', 'sales'):
        return None
    for code in ('accounting_core', 'sales'):
        if SaasModule.query.filter_by(code=code).first() is not None:
            return enforce_saas_module_or_response(code)
    return enforce_saas_module_or_response('sales')


def _org_id() -> int:
    try:
        oid = int(admin_data_scope_organization_id())
    except Exception:
        oid = int(default_organization_id())
    # Sesión con organization_id inválido/huérfano: evita tablas vacías por scope roto.
    if SaasOrganization.query.get(int(oid)) is None:
        return int(default_organization_id())
    return int(oid)


def _entry_or_404(entry_id: int, organization_id: int) -> JournalEntry:
    return JournalEntry.query.filter_by(id=int(entry_id), organization_id=int(organization_id)).first_or_404()


def _adjustment_or_404(adjustment_id: int, organization_id: int) -> AccountingAdjustment:
    return AccountingAdjustment.query.filter_by(id=int(adjustment_id), organization_id=int(organization_id)).first_or_404()


def _saas_chain_enabled(organization_id: int, *codes: str) -> bool:
    """Misma regla que ``saas_module_enabled_chain`` en app (menú y guards alineados)."""
    seq = [str(c or '').strip() for c in codes if str(c or '').strip()]
    if not seq:
        return True
    for code in seq:
        if SaasModule.query.filter_by(code=code).first() is not None:
            return bool(has_saas_module_enabled(organization_id, code))
    return bool(has_saas_module_enabled(organization_id, seq[-1]))


def _ensure_accounting_core_enabled(organization_id: int) -> None:
    if not _saas_chain_enabled(organization_id, 'accounting_core', 'sales'):
        abort(404)


def _ensure_adjustments_enabled(organization_id: int) -> None:
    if not _saas_chain_enabled(organization_id, 'accounting_adjustments', 'accounting_core', 'sales'):
        abort(404)


@accounting_core_bp.route('/accounts')
@login_required
@admin_required
def accounts_list():
    oid = _org_id()
    _ensure_accounting_core_enabled(oid)
    q = Account.query.filter_by(organization_id=oid)
    search = (request.args.get('q') or '').strip()
    acc_type = (request.args.get('type') or '').strip().lower()
    active_raw = (request.args.get('active') or '').strip().lower()
    reconcile_raw = (request.args.get('reconcile') or '').strip().lower()
    if search:
        q = q.filter((Account.code.ilike(f'%{search}%')) | (Account.name.ilike(f'%{search}%')))
    if acc_type in service.ACCOUNT_TYPES:
        q = q.filter(Account.type == acc_type)
    if active_raw in {'1', '0'}:
        q = q.filter(Account.is_active == (active_raw == '1'))
    if reconcile_raw in {'1', '0'}:
        q = q.filter(Account.allow_reconcile == (reconcile_raw == '1'))
    page = max(int(request.args.get('page') or 1), 1)
    per_page = min(max(int(request.args.get('per_page') or 80), 20), 200)
    total = q.count()
    rows = (
        q.order_by(Account.code.asc(), Account.id.asc()).offset((page - 1) * per_page).limit(per_page).all()
    )
    return render_template(
        'accounting/accounts_list.html',
        accounts=rows,
        organization_id=oid,
        q=search,
        selected_type=acc_type,
        selected_active=active_raw,
        selected_reconcile=reconcile_raw,
        page=page,
        per_page=per_page,
        total=total,
    )


@accounting_core_bp.route('/accounts', methods=['POST'])
@login_required
@admin_required
def accounts_create():
    oid = _org_id()
    _ensure_accounting_core_enabled(oid)
    try:
        service.create_account(
            oid,
            {
                'code': request.form.get('code'),
                'name': request.form.get('name'),
                'type': request.form.get('type'),
                'allow_reconcile': request.form.get('allow_reconcile') == 'on',
                'currency_code': request.form.get('currency_code'),
                'is_active': request.form.get('is_active') == 'on',
            },
        )
        flash('Cuenta contable creada.', 'success')
    except Exception as e:
        flash(str(e), 'error')
    return redirect(url_for('accounting_core.accounts_list'))


@accounting_core_bp.route('/journals')
@login_required
@admin_required
def journals_list():
    oid = _org_id()
    _ensure_accounting_core_enabled(oid)
    rows = Journal.query.filter_by(organization_id=oid).order_by(Journal.code.asc(), Journal.id.asc()).all()
    accounts = Account.query.filter_by(organization_id=oid, is_active=True).order_by(Account.code.asc()).all()
    return render_template('accounting/journals_list.html', journals=rows, accounts=accounts, organization_id=oid)


@accounting_core_bp.route('/journals', methods=['POST'])
@login_required
@admin_required
def journals_create():
    oid = _org_id()
    _ensure_accounting_core_enabled(oid)
    try:
        service.create_journal(
            oid,
            {
                'code': request.form.get('code'),
                'name': request.form.get('name'),
                'type': request.form.get('type'),
                'default_account_id': request.form.get('default_account_id'),
                'is_active': request.form.get('is_active') == 'on',
            },
        )
        flash('Diario creado.', 'success')
    except Exception as e:
        flash(str(e), 'error')
    return redirect(url_for('accounting_core.journals_list'))


def _build_lines_from_form() -> list[dict]:
    account_ids = request.form.getlist('line_account_id')
    debits = request.form.getlist('line_debit')
    credits = request.form.getlist('line_credit')
    descs = request.form.getlist('line_description')
    lines: list[dict] = []
    n = max(len(account_ids), len(debits), len(credits), len(descs))
    for i in range(n):
        aid = (account_ids[i] if i < len(account_ids) else '').strip()
        debit = (debits[i] if i < len(debits) else '').strip()
        credit = (credits[i] if i < len(credits) else '').strip()
        desc = (descs[i] if i < len(descs) else '').strip()
        if not aid and not debit and not credit and not desc:
            continue
        lines.append(
            {
                'account_id': aid,
                'debit': debit or 0,
                'credit': credit or 0,
                'description': desc or '',
            }
        )
    return lines


@accounting_core_bp.route('/entries')
@login_required
@admin_required
def entries_list():
    oid = _org_id()
    _ensure_accounting_core_enabled(oid)
    q = JournalEntry.query.filter_by(organization_id=oid)
    state = (request.args.get('state') or '').strip().lower()
    if state in {'draft', 'posted', 'reversed'}:
        q = q.filter(JournalEntry.state == state)
    rows = q.order_by(JournalEntry.date.desc(), JournalEntry.id.desc()).limit(300).all()
    return render_template('accounting/entries_list.html', entries=rows, selected_state=state, organization_id=oid)


@accounting_core_bp.route('/receivables')
@login_required
@admin_required
def receivables_list():
    """
    CxC operativo: facturas contabilizadas con saldo pendiente (posted / partial).
    """
    from nodeone.services.invoice_ledger import ensure_invoice_ledger_columns, invoice_residual

    oid = _org_id()
    _ensure_accounting_core_enabled(oid)
    ensure_invoice_ledger_columns()
    Invoice.__table__.create(db.engine, checkfirst=True)
    qstr = (request.args.get('q') or '').strip()
    cust_filter = request.args.get('customer_id', type=int)
    q = Invoice.query.filter(Invoice.organization_id == oid, Invoice.status.in_(('posted', 'partial')))
    if cust_filter and cust_filter > 0:
        q = q.filter(Invoice.customer_id == int(cust_filter))
    if qstr:
        like = f'%{qstr}%'
        match_uids = [
            r[0]
            for r in (
                db.session.query(User.id)
                .filter(
                    user_in_org_clause(User, oid),
                    or_(
                        User.email.ilike(like),
                        User.first_name.ilike(like),
                        User.last_name.ilike(like),
                    ),
                )
                .limit(500)
                .all()
            )
        ]
        if match_uids:
            q = q.filter(or_(Invoice.number.ilike(like), Invoice.customer_id.in_(match_uids)))
        else:
            q = q.filter(Invoice.number.ilike(like))
    rows = q.order_by(Invoice.due_date.asc(), Invoice.date.desc(), Invoice.id.desc()).limit(500).all()
    rows = [inv for inv in rows if float(invoice_residual(inv)) >= 0.005]
    cust_ids = {int(r.customer_id) for r in rows if getattr(r, 'customer_id', None)}
    users_by_id = {}
    if cust_ids:
        for u in User.query.filter(User.id.in_(list(cust_ids))).all():
            users_by_id[u.id] = u
    today = datetime.utcnow().date()
    enriched = []
    total_open = 0.0
    for inv in rows:
        total_open += float(invoice_residual(inv))
        u = users_by_id.get(int(inv.customer_id))
        if u:
            cust_label = f'{(u.first_name or "").strip()} {(u.last_name or "").strip()}'.strip() or u.email
            cust_email = (u.email or '').strip()
        else:
            cust_label = f'Usuario #{inv.customer_id}'
            cust_email = ''
        due_d = None
        if getattr(inv, 'due_date', None):
            due_d = inv.due_date.date() if hasattr(inv.due_date, 'date') else inv.due_date
        enriched.append(
            {
                'inv': inv,
                'customer_label': cust_label,
                'customer_email': cust_email,
                'due_date': due_d,
                'amount_due': float(invoice_residual(inv)),
            }
        )
    return render_template(
        'accounting/receivables_list.html',
        rows=enriched,
        total_open=total_open,
        q=qstr,
        filter_customer_id=cust_filter,
        organization_id=oid,
        today=today,
    )


@accounting_core_bp.route('/receivables/customers')
@login_required
@admin_required
def receivables_customers_list():
    """Saldo pendiente agregado por cliente (facturas posted / partial)."""
    from nodeone.services.invoice_ledger import ensure_invoice_ledger_columns

    oid = _org_id()
    _ensure_accounting_core_enabled(oid)
    ensure_invoice_ledger_columns()
    Invoice.__table__.create(db.engine, checkfirst=True)

    pending_expr = func.coalesce(
        func.sum(Invoice.grand_total - func.coalesce(Invoice.amount_paid, 0.0)), 0.0
    )
    groups = (
        db.session.query(Invoice.customer_id, func.count(Invoice.id), pending_expr)
        .filter(
            Invoice.organization_id == oid,
            Invoice.status.in_(('posted', 'partial')),
        )
        .group_by(Invoice.customer_id)
        .all()
    )
    rows_out = []
    total = 0.0
    for cid, cnt, pend in groups:
        p = float(pend or 0)
        if p < 0.005:
            continue
        total += p
        rows_out.append({'customer_id': int(cid), 'invoice_count': int(cnt or 0), 'pending': p})
    rows_out.sort(key=lambda r: r['pending'], reverse=True)
    cust_ids = [r['customer_id'] for r in rows_out]
    users_by_id = {}
    if cust_ids:
        for u in User.query.filter(User.id.in_(cust_ids)).all():
            users_by_id[u.id] = u
    for row in rows_out:
        u = users_by_id.get(row['customer_id'])
        if u:
            row['label'] = (
                f'{(u.first_name or "").strip()} {(u.last_name or "").strip()}'.strip() or (u.email or '')
            )
            row['email'] = (u.email or '').strip()
        else:
            row['label'] = f'Usuario #{row["customer_id"]}'
            row['email'] = ''
    return render_template(
        'accounting/receivables_customers.html',
        rows=rows_out,
        total_pending=total,
        organization_id=oid,
    )


@accounting_core_bp.route('/entries/new')
@login_required
@admin_required
def entries_new():
    oid = _org_id()
    _ensure_accounting_core_enabled(oid)
    journals = Journal.query.filter_by(organization_id=oid, is_active=True).order_by(Journal.code.asc()).all()
    accounts = Account.query.filter_by(organization_id=oid, is_active=True).order_by(Account.code.asc()).all()
    return render_template(
        'accounting/entry_form.html',
        entry=None,
        journals=journals,
        accounts=accounts,
        items=[],
        organization_id=oid,
    )


@accounting_core_bp.route('/entries', methods=['POST'])
@login_required
@admin_required
def entries_create():
    oid = _org_id()
    _ensure_accounting_core_enabled(oid)
    try:
        entry = service.create_entry_draft(
            oid,
            int(request.form.get('journal_id') or 0),
            {
                'date': request.form.get('date') or datetime.utcnow().date().isoformat(),
                'reference': request.form.get('reference') or '',
                'lines': _build_lines_from_form(),
            },
            user_id=getattr(current_user, 'id', None),
        )
        flash('Asiento borrador creado.', 'success')
        return redirect(url_for('accounting_core.entry_detail', entry_id=entry.id))
    except Exception as e:
        flash(str(e), 'error')
        return redirect(url_for('accounting_core.entries_new'))


@accounting_core_bp.route('/entries/<int:entry_id>')
@login_required
@admin_required
def entry_detail(entry_id: int):
    oid = _org_id()
    _ensure_accounting_core_enabled(oid)
    entry = _entry_or_404(entry_id, oid)
    journals = Journal.query.filter_by(organization_id=oid, is_active=True).order_by(Journal.code.asc()).all()
    accounts = Account.query.filter_by(organization_id=oid, is_active=True).order_by(Account.code.asc()).all()
    items = entry.items.order_by(JournalItem.id.asc()).all()
    debit_total, credit_total = service.build_entry_totals(entry)
    linked_invoice = None
    source_link_kind = None
    sm = (entry.source_model or '').strip()
    sid = entry.source_id
    if sid and sm in ('accounting.invoice', 'accounting.invoice_payment'):
        inv_row = Invoice.query.filter_by(id=int(sid), organization_id=oid).first()
        if inv_row:
            linked_invoice = inv_row
            source_link_kind = 'venta' if sm == 'accounting.invoice' else 'cobro'
    return render_template(
        'accounting/entry_detail.html',
        entry=entry,
        journals=journals,
        accounts=accounts,
        items=items,
        debit_total=debit_total,
        credit_total=credit_total,
        organization_id=oid,
        linked_invoice=linked_invoice,
        source_link_kind=source_link_kind,
    )


@accounting_core_bp.route('/entries/<int:entry_id>/save-draft', methods=['POST'])
@login_required
@admin_required
def entry_save_draft(entry_id: int):
    oid = _org_id()
    _ensure_accounting_core_enabled(oid)
    entry = _entry_or_404(entry_id, oid)
    if entry.state != 'draft':
        flash('Solo se puede guardar un asiento en borrador.', 'error')
        return redirect(url_for('accounting_core.entry_detail', entry_id=entry.id))
    try:
        journal_id = int(request.form.get('journal_id') or 0)
        journal = Journal.query.filter_by(id=journal_id, organization_id=oid, is_active=True).first()
        if journal is None:
            raise ValueError('Diario no válido para esta organización.')
        entry.journal_id = journal.id
        entry.reference = (request.form.get('reference') or '').strip() or None
        raw_date = request.form.get('date')
        if raw_date:
            entry.date = datetime.fromisoformat(raw_date).date()
        service.replace_entry_draft_lines(entry, oid, _build_lines_from_form())
        flash('Borrador actualizado.', 'success')
    except Exception as e:
        flash(str(e), 'error')
    return redirect(url_for('accounting_core.entry_detail', entry_id=entry.id))


@accounting_core_bp.route('/entries/<int:entry_id>/post', methods=['POST'])
@login_required
@admin_required
def entry_post(entry_id: int):
    oid = _org_id()
    _ensure_accounting_core_enabled(oid)
    entry = _entry_or_404(entry_id, oid)
    try:
        service.post_entry(entry, user_id=getattr(current_user, 'id', None))
        flash('Asiento publicado.', 'success')
    except Exception as e:
        flash(str(e), 'error')
    return redirect(url_for('accounting_core.entry_detail', entry_id=entry.id))


@accounting_core_bp.route('/entries/<int:entry_id>/reverse', methods=['POST'])
@login_required
@admin_required
def entry_reverse(entry_id: int):
    oid = _org_id()
    _ensure_accounting_core_enabled(oid)
    entry = _entry_or_404(entry_id, oid)
    try:
        rev = service.reverse_entry(entry, user_id=getattr(current_user, 'id', None))
        flash(f'Asiento reversado. Nuevo asiento #{rev.id}.', 'success')
        return redirect(url_for('accounting_core.entry_detail', entry_id=rev.id))
    except Exception as e:
        flash(str(e), 'error')
        return redirect(url_for('accounting_core.entry_detail', entry_id=entry.id))


@accounting_core_bp.route('/adjustments')
@login_required
@admin_required
def adjustments_list():
    oid = _org_id()
    _ensure_adjustments_enabled(oid)
    state = (request.args.get('state') or '').strip().lower()
    q = AccountingAdjustment.query.filter_by(organization_id=oid)
    if state in {'draft', 'applied', 'cancelled'}:
        q = q.filter(AccountingAdjustment.state == state)
    rows = q.order_by(AccountingAdjustment.adjustment_date.desc(), AccountingAdjustment.id.desc()).limit(300).all()
    journals = Journal.query.filter_by(organization_id=oid, is_active=True).order_by(Journal.code.asc()).all()
    accounts = Account.query.filter_by(organization_id=oid, is_active=True).order_by(Account.code.asc()).all()
    return render_template(
        'accounting/adjustments_list.html',
        adjustments=rows,
        journals=journals,
        accounts=accounts,
        selected_state=state,
        adjustment_types=sorted(service.ADJUSTMENT_TYPES),
        organization_id=oid,
    )


@accounting_core_bp.route('/adjustments', methods=['POST'])
@login_required
@admin_required
def adjustments_create():
    oid = _org_id()
    _ensure_adjustments_enabled(oid)
    try:
        service.create_adjustment(
            oid,
            {
                'name': request.form.get('name'),
                'adjustment_type': request.form.get('adjustment_type'),
                'adjustment_date': request.form.get('adjustment_date'),
                'journal_id': request.form.get('journal_id'),
                'debit_account_id': request.form.get('debit_account_id'),
                'credit_account_id': request.form.get('credit_account_id'),
                'amount': request.form.get('amount'),
                'description': request.form.get('description'),
            },
            user_id=getattr(current_user, 'id', None),
        )
        flash('Ajuste creado en borrador.', 'success')
    except Exception as e:
        flash(str(e), 'error')
    return redirect(url_for('accounting_core.adjustments_list'))


@accounting_core_bp.route('/adjustments/<int:adjustment_id>/apply', methods=['POST'])
@login_required
@admin_required
def adjustment_apply(adjustment_id: int):
    oid = _org_id()
    _ensure_adjustments_enabled(oid)
    adjustment = _adjustment_or_404(adjustment_id, oid)
    try:
        entry = service.apply_adjustment(adjustment, user_id=getattr(current_user, 'id', None))
        flash(f'Ajuste aplicado. Se generó el asiento #{entry.id}.', 'success')
        return redirect(url_for('accounting_core.entry_detail', entry_id=entry.id))
    except Exception as e:
        flash(str(e), 'error')
        return redirect(url_for('accounting_core.adjustments_list'))


@accounting_core_bp.route('/adjustments/<int:adjustment_id>/cancel', methods=['POST'])
@login_required
@admin_required
def adjustment_cancel(adjustment_id: int):
    oid = _org_id()
    _ensure_adjustments_enabled(oid)
    adjustment = _adjustment_or_404(adjustment_id, oid)
    if adjustment.state != 'draft':
        flash('Solo se puede cancelar un ajuste en borrador.', 'error')
        return redirect(url_for('accounting_core.adjustments_list'))
    adjustment.state = 'cancelled'
    from nodeone.core.db import db

    db.session.add(adjustment)
    db.session.commit()
    flash('Ajuste cancelado.', 'success')
    return redirect(url_for('accounting_core.adjustments_list'))
