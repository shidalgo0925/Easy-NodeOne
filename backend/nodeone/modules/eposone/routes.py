"""Rutas HTML de EPosOne (Etapa 6–7)."""

from __future__ import annotations

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from nodeone.core.template_context_gates import user_can_see_tenant_admin_menu
from nodeone.modules.eposone.sections import EPOSONE_SECTIONS, EPOSONE_SECTION_SLUGS

eposone_bp = Blueprint('eposone', __name__, url_prefix='/admin/eposone')


def _require_eposone_admin():
    if not user_can_see_tenant_admin_menu(current_user):
        return redirect(url_for('dashboard'))
    return None


def _order_detail_context(organization_id: int, order_id: int) -> dict | None:
    from models.commercial_core import CoreCashShift
    from nodeone.core.commerce.constants import (
        CASH_SHIFT_OPEN,
        ORDER_FISCAL_STATUS_PENDING,
        ORDER_PAYMENT_STATUS_PAID,
        ORDER_STATUS_CANCELLED,
        ORDER_STATUS_REFUNDED,
        ORDER_STATUS_TRANSITIONS,
        PAYMENT_STATUS_CAPTURED,
        PAYMENT_STATUS_PARTIAL_REFUND,
    )
    from nodeone.core.commerce.order import OrderService
    from nodeone.core.commerce.payment import PaymentService
    from nodeone.core.commerce.pos import PosTerminalService

    oid = int(organization_id)
    order = OrderService.get(oid, int(order_id))
    if order is None:
        return None

    next_statuses = sorted(ORDER_STATUS_TRANSITIONS.get(str(order.status or ''), frozenset()))
    payments = PaymentService.list_for_order(oid, int(order_id))
    terminals = PosTerminalService.list_terminals(oid, limit=50)
    open_shifts = (
        CoreCashShift.query.filter_by(organization_id=oid, status=CASH_SHIFT_OPEN)
        .order_by(CoreCashShift.register_ref.asc())
        .all()
    )
    amount_due = round(max(0.0, float(order.grand_total or 0) - float(order.amount_paid or 0)), 2)
    can_capture = str(order.payment_status) != ORDER_PAYMENT_STATUS_PAID and amount_due > 0
    can_transfer = (
        str(order.payment_status) == 'unpaid'
        and str(order.status) not in {ORDER_STATUS_CANCELLED, ORDER_STATUS_REFUNDED}
    )
    can_emit_fiscal = str(order.fiscal_status or '') == ORDER_FISCAL_STATUS_PENDING
    can_apply_promotion = (
        str(order.payment_status) == ORDER_PAYMENT_STATUS_UNPAID
        and str(order.status) not in {ORDER_STATUS_CANCELLED, ORDER_STATUS_REFUNDED}
    )
    active_promotions: list = []
    if can_apply_promotion:
        try:
            from nodeone.modules.eposone.promotion_service import PromotionService

            active_promotions = [p for p in PromotionService.list_promotions(oid) if p.active]
        except Exception:
            active_promotions = []

    refundable_payments: list[dict] = []
    for pay in payments:
        if str(pay.status or '') not in {PAYMENT_STATUS_CAPTURED, PAYMENT_STATUS_PARTIAL_REFUND}:
            continue
        remaining = round(float(pay.amount or 0) - float(pay.refunded_amount or 0), 2)
        if remaining > 0:
            refundable_payments.append({'payment': pay, 'remaining': remaining})

    from nodeone.core.commerce.authorization import CommerceAuthorizationService

    supervisor_ok = CommerceAuthorizationService.user_is_supervisor(current_user, oid)
    try:
        from nodeone.modules.eposone.settings_service import EposoneSettingsService

        if not EposoneSettingsService.runtime_for(oid).supervisor_approval_required:
            supervisor_ok = True
    except Exception:
        pass

    return {
        'order': order,
        'next_statuses': next_statuses,
        'payments': payments,
        'terminals': terminals,
        'open_shifts': open_shifts,
        'amount_due': amount_due,
        'can_capture': can_capture,
        'can_transfer': can_transfer,
        'can_emit_fiscal': can_emit_fiscal,
        'can_apply_promotion': can_apply_promotion,
        'active_promotions': active_promotions,
        'refundable_payments': refundable_payments,
        'supervisor_ok': supervisor_ok,
    }


def _redirect_order_detail(order_id: int):
    return redirect(url_for('eposone.eposone_order_detail', order_id=int(order_id)))


def _redirect_registers():
    return redirect(url_for('eposone.eposone_section', slug='registers'))


def _redirect_shifts():
    return redirect(url_for('eposone.eposone_section', slug='shifts'))


def _redirect_kds():
    return redirect(url_for('eposone.eposone_section', slug='kds'))


def _redirect_delivery():
    return redirect(url_for('eposone.eposone_section', slug='delivery'))


def _redirect_digital_menu():
    return redirect(url_for('eposone.eposone_section', slug='digital-menu'))


def _redirect_promotions():
    return redirect(url_for('eposone.eposone_section', slug='promotions'))


def _redirect_settings():
    return redirect(url_for('eposone.eposone_section', slug='settings'))


def _parse_digital_menu_items_from_form() -> list[dict]:
    names = request.form.getlist('item_name')
    prices = request.form.getlist('item_price')
    categories = request.form.getlist('item_category')
    items: list[dict] = []
    for idx, raw_name in enumerate(names):
        name = (raw_name or '').strip()
        if not name:
            continue
        try:
            price = float(prices[idx] if idx < len(prices) else 0)
        except (TypeError, ValueError):
            price = 0.0
        category = (categories[idx] if idx < len(categories) else '').strip() or None
        items.append({'name': name, 'price': price, 'category': category, 'sort_order': len(items)})
    return items


def _kds_page_context(organization_id: int) -> dict:
    from nodeone.modules.eposone.kds_service import (
        KDS_TICKET_CANCELLED,
        KDS_TICKET_SERVED,
        KDS_TICKET_TRANSITIONS,
        KdsService,
    )

    tickets = KdsService.list_tickets(int(organization_id), limit=50)
    rows: list[dict] = []
    for ticket in tickets:
        if str(ticket.status or '') in {KDS_TICKET_SERVED, KDS_TICKET_CANCELLED}:
            continue
        rows.append(
            {
                'ticket': ticket,
                'next_statuses': sorted(KDS_TICKET_TRANSITIONS.get(str(ticket.status or ''), frozenset())),
            }
        )
    return {'ticket_rows': rows, 'tickets_total': len(rows)}


def _delivery_page_context(organization_id: int) -> dict:
    from models.eposone_delivery import DELIVERY_STATUS_PENDING, DELIVERY_TRANSITIONS, EposoneDelivery
    from nodeone.modules.eposone.delivery_service import EposoneDeliveryService

    rows_db = (
        EposoneDelivery.query.filter_by(organization_id=int(organization_id))
        .order_by(EposoneDelivery.id.desc())
        .limit(50)
        .all()
    )
    rows: list[dict] = []
    for row in rows_db:
        detail = EposoneDeliveryService.to_detail_dict(row)
        status = str(detail.get('status') or '')
        rows.append(
            {
                **detail,
                'next_statuses': sorted(DELIVERY_TRANSITIONS.get(status, frozenset())),
                'can_assign': status == DELIVERY_STATUS_PENDING,
            }
        )
    return {'delivery_rows': rows, 'deliveries_total': len(rows)}


def _shift_operational_row(
    organization_id: int,
    shift_row,
    *,
    registers_by_ref: dict,
) -> dict:
    from models.commercial_core import CoreCashMovement
    from nodeone.core.commerce.cash import CashRegisterService
    from nodeone.core.commerce.constants import CASH_SHIFT_CLOSED, CASH_SHIFT_OPEN, CASH_SHIFT_RECONCILING
    from nodeone.core.commerce.persistence import cash_shift_to_dto

    status = str(shift_row.status or '')
    shift_dto = cash_shift_to_dto(
        shift_row,
        include_variance=(status in (CASH_SHIFT_RECONCILING, CASH_SHIFT_CLOSED)),
    )
    expected_balance = None
    can_reconcile = False
    can_close = False
    can_move = False
    if status == CASH_SHIFT_OPEN:
        expected_balance = CashRegisterService.compute_expected_balance(int(shift_row.id))
        can_reconcile = True
        can_move = True
    elif status == CASH_SHIFT_RECONCILING:
        can_close = True

    reg = registers_by_ref.get(str(shift_row.register_ref))
    movement_count = CoreCashMovement.query.filter_by(
        organization_id=int(organization_id),
        shift_id=int(shift_row.id),
    ).count()
    return {
        'shift': shift_dto,
        'register_ref': str(shift_row.register_ref),
        'register_name': str(getattr(reg, 'name', None) or shift_row.register_ref),
        'expected_balance': expected_balance,
        'movement_count': int(movement_count),
        'can_reconcile': can_reconcile,
        'can_close': can_close,
        'can_move': can_move,
    }


def _registers_page_context(organization_id: int) -> dict:
    from models.commercial_core import CoreCashShift
    from nodeone.core.commerce.cash import CashRegisterService
    from nodeone.core.commerce.constants import CASH_SHIFT_CLOSED, CASH_SHIFT_OPEN, CASH_SHIFT_RECONCILING
    from nodeone.core.commerce.persistence import cash_shift_to_dto
    from nodeone.core.master.constants import ORG_UNIT_TYPE_REGISTER
    from nodeone.core.services.org_unit import OrgUnitService

    oid = int(organization_id)
    registers = OrgUnitService.list_units(oid, unit_type=ORG_UNIT_TYPE_REGISTER)
    active_shifts = (
        CoreCashShift.query.filter(
            CoreCashShift.organization_id == oid,
            CoreCashShift.status.in_((CASH_SHIFT_OPEN, CASH_SHIFT_RECONCILING)),
        )
        .order_by(CoreCashShift.register_ref.asc())
        .all()
    )
    shift_by_register = {str(row.register_ref): row for row in active_shifts}

    register_rows: list[dict] = []
    for reg in registers:
        ref = str(reg.unit_ref)
        shift_row = shift_by_register.get(ref)
        shift_dto = None
        expected_balance = None
        can_open = shift_row is None
        can_reconcile = False
        can_close = False
        if shift_row is not None:
            status = str(shift_row.status or '')
            shift_dto = cash_shift_to_dto(
                shift_row,
                include_variance=(status == CASH_SHIFT_RECONCILING),
            )
            if status == CASH_SHIFT_OPEN:
                expected_balance = CashRegisterService.compute_expected_balance(int(shift_row.id))
                can_reconcile = True
            elif status == CASH_SHIFT_RECONCILING:
                can_close = True
        register_rows.append(
            {
                'register': reg,
                'shift': shift_dto,
                'expected_balance': expected_balance,
                'can_open': can_open,
                'can_reconcile': can_reconcile,
                'can_close': can_close,
            }
        )

    recent_closed = (
        CoreCashShift.query.filter_by(organization_id=oid, status=CASH_SHIFT_CLOSED)
        .order_by(CoreCashShift.closed_at.desc())
        .limit(10)
        .all()
    )
    return {
        'register_rows': register_rows,
        'registers_total': len(registers),
        'open_shifts_total': len(active_shifts),
        'recent_closed': [cash_shift_to_dto(row, include_variance=True) for row in recent_closed],
    }


def _shifts_page_context(organization_id: int) -> dict:
    from models.commercial_core import CoreCashShift
    from nodeone.core.commerce.authorization import CommerceAuthorizationService
    from nodeone.core.commerce.constants import CASH_SHIFT_CLOSED, CASH_SHIFT_OPEN, CASH_SHIFT_RECONCILING
    from nodeone.core.master.constants import ORG_UNIT_TYPE_REGISTER
    from nodeone.core.services.org_unit import OrgUnitService

    oid = int(organization_id)
    registers = OrgUnitService.list_units(oid, unit_type=ORG_UNIT_TYPE_REGISTER)
    registers_by_ref = {str(reg.unit_ref): reg for reg in registers}

    active_rows_db = (
        CoreCashShift.query.filter(
            CoreCashShift.organization_id == oid,
            CoreCashShift.status.in_((CASH_SHIFT_OPEN, CASH_SHIFT_RECONCILING)),
        )
        .order_by(CoreCashShift.opened_at.desc())
        .all()
    )
    closed_rows_db = (
        CoreCashShift.query.filter_by(organization_id=oid, status=CASH_SHIFT_CLOSED)
        .order_by(CoreCashShift.closed_at.desc())
        .limit(30)
        .all()
    )
    active_shifts = [
        _shift_operational_row(oid, row, registers_by_ref=registers_by_ref) for row in active_rows_db
    ]
    closed_shifts = [
        _shift_operational_row(oid, row, registers_by_ref=registers_by_ref) for row in closed_rows_db
    ]
    supervisor_ok = CommerceAuthorizationService.user_is_supervisor(current_user, oid)
    try:
        from nodeone.modules.eposone.settings_service import EposoneSettingsService

        if not EposoneSettingsService.runtime_for(oid).supervisor_approval_required:
            supervisor_ok = True
    except Exception:
        pass
    return {
        'active_shifts': active_shifts,
        'closed_shifts': closed_shifts,
        'active_total': len(active_shifts),
        'closed_total': len(closed_shifts),
        'supervisor_ok': CommerceAuthorizationService.user_is_supervisor(current_user, oid),
    }


@eposone_bp.route('/')
@eposone_bp.route('/dashboard')
@login_required
def eposone_home():
    denied = _require_eposone_admin()
    if denied is not None:
        return denied
    from nodeone.core.commerce.dashboard import CommerceDashboardService
    from nodeone.core.platform.runtime import resolve_organization_id

    kpis = None
    recent_orders: list = []
    oid = resolve_organization_id()
    if oid is not None:
        kpis = CommerceDashboardService.get_snapshot(int(oid))
        recent_orders = CommerceDashboardService.list_recent_domain_orders(int(oid), limit=12)
    return render_template(
        'eposone/dashboard.html',
        compose_links=_compose_links(),
        kpis=kpis,
        recent_orders=recent_orders,
        dashboard_refresh_seconds=30,
    )


@eposone_bp.route('/devices/rotate-provisioning-code', methods=['POST'])
@login_required
def eposone_rotate_provisioning_code():
    """Legacy EN1-01: rota código a nivel org (no usar para tablets nuevas)."""
    denied = _require_eposone_admin()
    if denied is not None:
        return denied
    from flask import flash, redirect, url_for

    from nodeone.core.platform.runtime import resolve_organization_id
    from nodeone.modules.eposone.device_provisioning import DeviceProvisioningService

    oid = resolve_organization_id()
    if oid is None:
        flash('Organización no resuelta.', 'warning')
        return redirect(url_for('eposone.eposone_section', slug='terminals'))
    DeviceProvisioningService.rotate_provisioning_code(int(oid))
    flash('Código legacy (org) rotado. Preferí códigos por Caja (EN1-02).', 'success')
    return redirect(url_for('eposone.eposone_section', slug='terminals'))


@eposone_bp.route('/devices/issue-provisioning-code', methods=['POST'])
@login_required
def eposone_issue_provisioning_code():
    """EN1-02: genera código de destino para una Caja (register_ref)."""
    denied = _require_eposone_admin()
    if denied is not None:
        return denied
    from flask import flash, redirect, request, url_for

    from nodeone.core.platform.runtime import resolve_organization_id
    from nodeone.modules.eposone.device_provisioning import (
        DeviceProvisioningError,
        DeviceProvisioningService,
    )

    oid = resolve_organization_id()
    register_ref = (request.form.get('register_ref') or '').strip()
    if oid is None or not register_ref:
        flash('Falta register_ref (caja).', 'warning')
        return redirect(url_for('eposone.eposone_section', slug='terminals'))
    try:
        row = DeviceProvisioningService.issue_code_for_register(int(oid), register_ref=register_ref)
        flash(f'Código generado para {register_ref}: {row.code}', 'success')
    except DeviceProvisioningError as exc:
        flash(f'No se pudo generar código: {exc.code}', 'danger')
    return redirect(url_for('eposone.eposone_section', slug='terminals'))


@eposone_bp.route('/analytics')
@login_required
def eposone_analytics():
    """Analítica operativa del POS (UX-T4). Vive en EPosOne, no en /admin/analytics?source=."""
    denied = _require_eposone_admin()
    if denied is not None:
        return denied
    from nodeone.core.commerce.dashboard import CommerceDashboardService
    from nodeone.core.platform.runtime import resolve_organization_id

    kpis = None
    recent_reports: list = []
    oid = resolve_organization_id()
    if oid is not None:
        kpis = CommerceDashboardService.get_snapshot(int(oid))
        recent_reports = CommerceDashboardService.list_recent_report_events(int(oid), limit=20)
    return render_template(
        'eposone/analytics.html',
        kpis=kpis,
        recent_reports=recent_reports,
    )


@eposone_bp.route('/orders/<int:order_id>')
@login_required
def eposone_order_detail(order_id: int):
    denied = _require_eposone_admin()
    if denied is not None:
        return denied
    from nodeone.core.platform.runtime import resolve_organization_id

    oid = resolve_organization_id()
    if oid is None:
        abort(400)
    ctx = _order_detail_context(int(oid), int(order_id))
    if ctx is None:
        abort(404)
    return render_template('eposone/order_detail.html', **ctx)


@eposone_bp.route('/orders/domain/<int:order_id>')
@login_required
def eposone_order_domain_detail(order_id: int):
    """Detalle read-only Order Domain Hito 3 (eposone_order)."""
    denied = _require_eposone_admin()
    if denied is not None:
        return denied
    from models.eposone_order import EposoneOrder, EposoneOrderEvent
    from nodeone.core.platform.runtime import resolve_organization_id

    oid = resolve_organization_id()
    if oid is None:
        abort(400)
    order = EposoneOrder.query.filter_by(id=int(order_id), organization_id=int(oid)).first()
    if order is None:
        abort(404)
    events = (
        EposoneOrderEvent.query.filter_by(order_id=int(order.id))
        .order_by(EposoneOrderEvent.sequence.asc())
        .all()
    )
    return render_template(
        'eposone/order_domain_detail.html',
        order=order,
        events=events,
    )


@eposone_bp.route('/orders/<int:order_id>/status', methods=['POST'])
@login_required
def eposone_order_status(order_id: int):
    denied = _require_eposone_admin()
    if denied is not None:
        return denied
    from nodeone.core.commerce.order import OrderService, OrderValidationError
    from nodeone.core.platform.runtime import resolve_organization_id

    oid = resolve_organization_id()
    if oid is None:
        abort(400)
    target = (request.form.get('status') or '').strip().lower()
    if not target:
        flash('Seleccioná un estado.', 'warning')
        return _redirect_order_detail(order_id)
    try:
        dto = OrderService.transition_status(int(oid), int(order_id), target, source_app_id='eposone')
    except OrderValidationError as exc:
        flash(str(exc).replace('_', ' '), 'danger')
        return _redirect_order_detail(order_id)
    flash(f'Estado actualizado a {dto.status}.', 'success')
    return _redirect_order_detail(order_id)


@eposone_bp.route('/orders/<int:order_id>/capture-payment', methods=['POST'])
@login_required
def eposone_order_capture_payment(order_id: int):
    denied = _require_eposone_admin()
    if denied is not None:
        return denied
    from nodeone.core.commerce.order import OrderValidationError
    from nodeone.core.commerce.payment import PaymentService
    from nodeone.core.platform.runtime import resolve_organization_id

    oid = resolve_organization_id()
    if oid is None:
        abort(400)
    try:
        amount = float(request.form.get('amount') or 0)
    except ValueError:
        flash('Monto no válido.', 'danger')
        return _redirect_order_detail(order_id)
    body = {
        'order_id': int(order_id),
        'amount': amount,
        'payment_type': (request.form.get('payment_type') or 'card').strip().lower(),
    }
    register_ref = (request.form.get('register_ref') or '').strip()
    if register_ref:
        body['register_ref'] = register_ref
    try:
        dto = PaymentService.capture(int(oid), body, source_app_id='eposone')
    except OrderValidationError as exc:
        flash(str(exc).replace('_', ' '), 'danger')
        return _redirect_order_detail(order_id)
    flash(f'Pago {dto.payment_ref} capturado ({dto.amount:.2f}).', 'success')
    return _redirect_order_detail(order_id)


@eposone_bp.route('/orders/<int:order_id>/transfer', methods=['POST'])
@login_required
def eposone_order_transfer(order_id: int):
    denied = _require_eposone_admin()
    if denied is not None:
        return denied
    from nodeone.core.commerce.order import OrderService, OrderValidationError
    from nodeone.core.platform.runtime import resolve_organization_id

    oid = resolve_organization_id()
    if oid is None:
        abort(400)
    terminal_id = (request.form.get('terminal_id') or '').strip()
    terminal_ref = (request.form.get('terminal_ref') or '').strip()
    payload: dict = {}
    if terminal_id:
        payload['terminal_id'] = int(terminal_id)
    elif terminal_ref:
        payload['terminal_ref'] = terminal_ref
    else:
        flash('Seleccioná una terminal.', 'warning')
        return _redirect_order_detail(order_id)
    try:
        dto = OrderService.transfer_to_terminal(int(oid), int(order_id), payload, source_app_id='eposone')
    except (OrderValidationError, ValueError) as exc:
        flash(str(exc).replace('_', ' '), 'danger')
        return _redirect_order_detail(order_id)
    flash(f'Pedido transferido a terminal {dto.pos_terminal_id}.', 'success')
    return _redirect_order_detail(order_id)


@eposone_bp.route('/orders/<int:order_id>/emit-fiscal', methods=['POST'])
@login_required
def eposone_order_emit_fiscal(order_id: int):
    denied = _require_eposone_admin()
    if denied is not None:
        return denied
    from nodeone.core.commerce.fiscal import CommerceFiscalService
    from nodeone.core.commerce.order import OrderValidationError
    from nodeone.core.platform.runtime import resolve_organization_id

    oid = resolve_organization_id()
    if oid is None:
        abort(400)
    try:
        result = CommerceFiscalService.process_pending_order(
            int(oid), int(order_id), source_app_id='eposone', force_emit=True
        )
    except OrderValidationError as exc:
        flash(str(exc).replace('_', ' '), 'danger')
        return _redirect_order_detail(order_id)
    status = str(result.get('status') or '')
    if status == 'issued':
        flash(f'Factura emitida para {result.get("order_ref", order_id)}.', 'success')
    elif status == 'skipped':
        flash(f'Emisión fiscal omitida: {result.get("reason", "—")}.', 'warning')
    else:
        flash(f'Emisión fiscal en cola: {result.get("reason", status)}.', 'info')
    return _redirect_order_detail(order_id)


@eposone_bp.route('/orders/<int:order_id>/refund-payment', methods=['POST'])
@login_required
def eposone_order_refund_payment(order_id: int):
    denied = _require_eposone_admin()
    if denied is not None:
        return denied
    from nodeone.core.commerce.order import OrderValidationError
    from nodeone.core.commerce.payment import PaymentService
    from nodeone.core.platform.runtime import resolve_organization_id

    oid = resolve_organization_id()
    if oid is None:
        abort(400)
    payment_id = (request.form.get('payment_id') or '').strip()
    if not payment_id:
        flash('Seleccioná un pago.', 'warning')
        return _redirect_order_detail(order_id)
    supervisor_raw = (request.form.get('supervisor_user_id') or '').strip()
    if not supervisor_raw and getattr(current_user, 'id', None):
        supervisor_raw = str(int(current_user.id))
    approval = {
        'supervisor_user_id': supervisor_raw,
        'reason': (request.form.get('reason') or '').strip(),
    }
    amount_raw = (request.form.get('amount') or '').strip()
    amount = float(amount_raw) if amount_raw else None
    try:
        dto = PaymentService.refund(
            int(oid),
            int(payment_id),
            amount=amount,
            approval=approval,
            source_app_id='eposone',
        )
    except (OrderValidationError, ValueError) as exc:
        flash(str(exc).replace('_', ' '), 'danger')
        return _redirect_order_detail(order_id)
    flash(f'Reembolso registrado en {dto.payment_ref}.', 'success')
    return _redirect_order_detail(order_id)


@eposone_bp.route('/orders/<int:order_id>/apply-promotion', methods=['POST'])
@login_required
def eposone_order_apply_promotion(order_id: int):
    denied = _require_eposone_admin()
    if denied is not None:
        return denied
    from nodeone.core.commerce.order import OrderService, OrderValidationError
    from nodeone.core.platform.runtime import resolve_organization_id

    oid = resolve_organization_id()
    if oid is None:
        abort(400)
    code = (request.form.get('code') or '').strip()
    promotion_raw = (request.form.get('promotion_id') or '').strip()
    promotion_id = int(promotion_raw) if promotion_raw.isdigit() else None
    try:
        if promotion_id is not None:
            OrderService.apply_promotion(int(oid), int(order_id), promotion_id=promotion_id)
        else:
            OrderService.apply_promotion(int(oid), int(order_id), code=code)
    except OrderValidationError as exc:
        flash(str(exc).replace('_', ' '), 'danger')
        return _redirect_order_detail(order_id)
    flash('Promoción aplicada al pedido.', 'success')
    return _redirect_order_detail(order_id)


@eposone_bp.route('/registers/open', methods=['POST'])
@login_required
def eposone_register_open_shift():
    denied = _require_eposone_admin()
    if denied is not None:
        return denied
    from nodeone.core.commerce.cash import CashRegisterService
    from nodeone.core.commerce.order import OrderValidationError
    from nodeone.core.platform.runtime import resolve_organization_id

    oid = resolve_organization_id()
    if oid is None:
        abort(400)
    register_ref = (request.form.get('register_ref') or '').strip()
    if not register_ref:
        flash('Seleccioná una caja.', 'warning')
        return _redirect_registers()
    try:
        opening_balance = float(request.form.get('opening_balance') or 0)
    except ValueError:
        flash('Saldo inicial no válido.', 'danger')
        return _redirect_registers()
    try:
        dto = CashRegisterService.open_shift(
            int(oid),
            register_ref=register_ref,
            opening_balance=opening_balance,
            source_app_id='eposone',
        )
    except OrderValidationError as exc:
        flash(str(exc).replace('_', ' '), 'danger')
        return _redirect_registers()
    flash(f'Turno abierto en {dto.register_ref} (saldo inicial {dto.opening_balance:.2f}).', 'success')
    return _redirect_registers()


@eposone_bp.route('/registers/<int:shift_id>/reconcile', methods=['POST'])
@login_required
def eposone_register_reconcile_shift(shift_id: int):
    denied = _require_eposone_admin()
    if denied is not None:
        return denied
    from nodeone.core.commerce.cash import CashRegisterService
    from nodeone.core.commerce.order import OrderValidationError
    from nodeone.core.platform.runtime import resolve_organization_id

    oid = resolve_organization_id()
    if oid is None:
        abort(400)
    try:
        counted_amount = float(request.form.get('counted_amount') or 0)
    except ValueError:
        flash('Monto contado no válido.', 'danger')
        return _redirect_registers()
    try:
        dto = CashRegisterService.begin_reconcile(
            int(oid),
            int(shift_id),
            counted_amount=counted_amount,
            source_app_id='eposone',
        )
    except OrderValidationError as exc:
        flash(str(exc).replace('_', ' '), 'danger')
        return _redirect_registers()
    flash(
        f'Arqueo iniciado en {dto.register_ref}. Revisá la diferencia y cerrá el turno.',
        'info',
    )
    return _redirect_registers()


@eposone_bp.route('/registers/<int:shift_id>/close', methods=['POST'])
@login_required
def eposone_register_close_shift(shift_id: int):
    denied = _require_eposone_admin()
    if denied is not None:
        return denied
    from nodeone.core.commerce.cash import CashRegisterService
    from nodeone.core.commerce.order import OrderValidationError
    from nodeone.core.platform.runtime import resolve_organization_id

    oid = resolve_organization_id()
    if oid is None:
        abort(400)
    try:
        dto = CashRegisterService.close_shift(int(oid), int(shift_id), source_app_id='eposone')
    except OrderValidationError as exc:
        flash(str(exc).replace('_', ' '), 'danger')
        return _redirect_registers()
    variance = dto.cash_variance
    if variance is not None and abs(variance) > 0.009:
        flash(
            f'Turno cerrado en {dto.register_ref} con diferencia de {variance:.2f}.',
            'warning',
        )
    else:
        flash(f'Turno cerrado en {dto.register_ref}.', 'success')
    return _redirect_registers()


@eposone_bp.route('/shifts/<int:shift_id>/movement', methods=['POST'])
@login_required
def eposone_shift_movement(shift_id: int):
    denied = _require_eposone_admin()
    if denied is not None:
        return denied
    from nodeone.core.commerce.cash import CashRegisterService
    from nodeone.core.commerce.order import OrderValidationError
    from nodeone.core.platform.runtime import resolve_organization_id

    oid = resolve_organization_id()
    if oid is None:
        abort(400)
    movement_type = (request.form.get('movement_type') or '').strip().lower()
    if movement_type not in {'cash_in', 'cash_out'}:
        flash('Tipo de movimiento no válido.', 'warning')
        return _redirect_shifts()
    try:
        amount = float(request.form.get('amount') or 0)
    except ValueError:
        flash('Monto no válido.', 'danger')
        return _redirect_shifts()
    supervisor_raw = (request.form.get('supervisor_user_id') or '').strip()
    if not supervisor_raw and getattr(current_user, 'id', None):
        supervisor_raw = str(int(current_user.id))
    approval = {
        'supervisor_user_id': supervisor_raw,
        'reason': (request.form.get('reason') or '').strip(),
    }
    try:
        CashRegisterService.record_manual_movement(
            int(oid),
            int(shift_id),
            movement_type,
            amount,
            notes=(request.form.get('notes') or '').strip() or None,
            approval=approval,
            source_app_id='eposone',
        )
    except OrderValidationError as exc:
        flash(str(exc).replace('_', ' '), 'danger')
        return _redirect_shifts()
    label = 'Ingreso' if movement_type == 'cash_in' else 'Egreso'
    flash(f'{label} de {amount:.2f} registrado en el turno.', 'success')
    return _redirect_shifts()


@eposone_bp.route('/kds/<int:ticket_id>/status', methods=['POST'])
@login_required
def eposone_kds_ticket_status(ticket_id: int):
    denied = _require_eposone_admin()
    if denied is not None:
        return denied
    from nodeone.core.commerce.order import OrderValidationError
    from nodeone.core.platform.runtime import resolve_organization_id
    from nodeone.modules.eposone.kds_service import KdsService

    oid = resolve_organization_id()
    if oid is None:
        abort(400)
    target = (request.form.get('status') or '').strip().lower()
    if not target:
        flash('Seleccioná un estado.', 'warning')
        return _redirect_kds()
    try:
        dto = KdsService.transition_ticket(int(oid), int(ticket_id), target)
    except OrderValidationError as exc:
        flash(str(exc).replace('_', ' '), 'danger')
        return _redirect_kds()
    flash(f'Ticket {dto.order_ref} → {dto.status}.', 'success')
    return _redirect_kds()


@eposone_bp.route('/delivery/<int:delivery_id>/assign', methods=['POST'])
@login_required
def eposone_delivery_assign(delivery_id: int):
    denied = _require_eposone_admin()
    if denied is not None:
        return denied
    from nodeone.core.commerce.order import OrderValidationError
    from nodeone.core.platform.runtime import resolve_organization_id
    from nodeone.modules.eposone.delivery_service import EposoneDeliveryService

    oid = resolve_organization_id()
    if oid is None:
        abort(400)
    driver_name = (request.form.get('driver_name') or '').strip()
    if not driver_name:
        flash('Indicá el nombre del repartidor.', 'warning')
        return _redirect_delivery()
    try:
        dto = EposoneDeliveryService.assign_driver(int(oid), int(delivery_id), driver_name=driver_name)
    except OrderValidationError as exc:
        flash(str(exc).replace('_', ' '), 'danger')
        return _redirect_delivery()
    flash(f'Entrega {dto.order_ref} asignada a {driver_name}.', 'success')
    return _redirect_delivery()


@eposone_bp.route('/delivery/<int:delivery_id>/status', methods=['POST'])
@login_required
def eposone_delivery_status(delivery_id: int):
    denied = _require_eposone_admin()
    if denied is not None:
        return denied
    from nodeone.core.commerce.order import OrderValidationError
    from nodeone.core.platform.runtime import resolve_organization_id
    from nodeone.modules.eposone.delivery_service import EposoneDeliveryService

    oid = resolve_organization_id()
    if oid is None:
        abort(400)
    target = (request.form.get('status') or '').strip().lower()
    if not target:
        flash('Seleccioná un estado.', 'warning')
        return _redirect_delivery()
    try:
        dto = EposoneDeliveryService.transition_status(int(oid), int(delivery_id), target)
    except OrderValidationError as exc:
        flash(str(exc).replace('_', ' '), 'danger')
        return _redirect_delivery()
    flash(f'Entrega {dto.order_ref} → {dto.status}.', 'success')
    return _redirect_delivery()


@eposone_bp.route('/digital-menus/create', methods=['POST'])
@login_required
def eposone_digital_menu_create():
    denied = _require_eposone_admin()
    if denied is not None:
        return denied
    from nodeone.core.commerce.order import OrderValidationError
    from nodeone.core.platform.runtime import resolve_organization_id
    from nodeone.modules.eposone.digital_menu_service import DigitalMenuService

    oid = resolve_organization_id()
    if oid is None:
        abort(400)
    name = (request.form.get('name') or '').strip()
    items = _parse_digital_menu_items_from_form()
    if not items:
        flash('Agregá al menos un ítem con nombre.', 'warning')
        return _redirect_digital_menu()
    try:
        dto = DigitalMenuService.create_menu(int(oid), name=name, items=items)
    except OrderValidationError as exc:
        flash(str(exc).replace('_', ' '), 'danger')
        return _redirect_digital_menu()
    flash(f'Menú {dto.menu_ref} creado ({len(dto.items)} ítem(s)).', 'success')
    return _redirect_digital_menu()


@eposone_bp.route('/digital-menus/<int:menu_id>/active', methods=['POST'])
@login_required
def eposone_digital_menu_set_active(menu_id: int):
    denied = _require_eposone_admin()
    if denied is not None:
        return denied
    from nodeone.core.commerce.order import OrderValidationError
    from nodeone.core.platform.runtime import resolve_organization_id
    from nodeone.modules.eposone.digital_menu_service import DigitalMenuService

    oid = resolve_organization_id()
    if oid is None:
        abort(400)
    active_raw = (request.form.get('active') or '').strip().lower()
    active = active_raw in {'1', 'true', 'yes', 'on'}
    try:
        dto = DigitalMenuService.set_active(int(oid), int(menu_id), active=active)
    except OrderValidationError as exc:
        flash(str(exc).replace('_', ' '), 'danger')
        return _redirect_digital_menu()
    label = 'activado' if dto.active else 'desactivado'
    flash(f'Menú {dto.menu_ref} {label}.', 'success')
    return _redirect_digital_menu()


@eposone_bp.route('/promotions/create', methods=['POST'])
@login_required
def eposone_promotion_create():
    denied = _require_eposone_admin()
    if denied is not None:
        return denied
    from nodeone.core.commerce.order import OrderValidationError
    from nodeone.core.platform.runtime import resolve_organization_id
    from nodeone.modules.eposone.promotion_service import PromotionService

    oid = resolve_organization_id()
    if oid is None:
        abort(400)
    name = (request.form.get('name') or '').strip()
    promo_type = (request.form.get('promo_type') or 'percent').strip().lower()
    code = (request.form.get('code') or '').strip() or None
    try:
        value = float(request.form.get('value') or 0)
    except ValueError:
        flash('Valor de descuento no válido.', 'danger')
        return _redirect_promotions()
    try:
        dto = PromotionService.create_promotion(
            int(oid),
            name=name,
            promo_type=promo_type,
            value=value,
            code=code,
        )
    except OrderValidationError as exc:
        flash(str(exc).replace('_', ' '), 'danger')
        return _redirect_promotions()
    flash(f'Promoción {dto.promo_ref} creada.', 'success')
    return _redirect_promotions()


@eposone_bp.route('/promotions/<int:promotion_id>/active', methods=['POST'])
@login_required
def eposone_promotion_set_active(promotion_id: int):
    denied = _require_eposone_admin()
    if denied is not None:
        return denied
    from nodeone.core.commerce.order import OrderValidationError
    from nodeone.core.platform.runtime import resolve_organization_id
    from nodeone.modules.eposone.promotion_service import PromotionService

    oid = resolve_organization_id()
    if oid is None:
        abort(400)
    active_raw = (request.form.get('active') or '').strip().lower()
    active = active_raw in {'1', 'true', 'yes', 'on'}
    try:
        dto = PromotionService.set_active(int(oid), int(promotion_id), active=active)
    except OrderValidationError as exc:
        flash(str(exc).replace('_', ' '), 'danger')
        return _redirect_promotions()
    label = 'activada' if dto.active else 'desactivada'
    flash(f'Promoción {dto.promo_ref} {label}.', 'success')
    return _redirect_promotions()


@eposone_bp.route('/settings/save', methods=['POST'])
@login_required
def eposone_settings_save():
    denied = _require_eposone_admin()
    if denied is not None:
        return denied
    from nodeone.core.commerce.order import OrderValidationError
    from nodeone.core.platform.runtime import resolve_organization_id
    from nodeone.modules.eposone.settings_service import EposoneSettingsService

    oid = resolve_organization_id()
    if oid is None:
        abort(400)
    try:
        dto = EposoneSettingsService.update_settings(
            int(oid),
            default_currency=(request.form.get('default_currency') or 'USD').strip(),
            kds_auto_enqueue=request.form.get('kds_auto_enqueue') == '1',
            delivery_auto_create=request.form.get('delivery_auto_create') == '1',
            fiscal_on_payment=request.form.get('fiscal_on_payment') == '1',
            supervisor_approval_required=request.form.get('supervisor_approval_required') == '1',
        )
    except OrderValidationError as exc:
        flash(str(exc).replace('_', ' '), 'danger')
        return _redirect_settings()
    flash(f'Configuración guardada (moneda {dto.default_currency}).', 'success')
    return _redirect_settings()


@eposone_bp.route('/products/create', methods=['POST'])
@login_required
def eposone_product_create():
    denied = _require_eposone_admin()
    if denied is not None:
        return denied
    from nodeone.core.master.constants import MasterDataError
    from nodeone.core.platform.runtime import resolve_organization_id
    from nodeone.core.services.product import ProductService
    from nodeone.services.product_image_storage import resolve_product_image_url

    oid = resolve_organization_id()
    if oid is None:
        abort(400)
    image_url, img_err = resolve_product_image_url(
        organization_id=int(oid),
        file_storage=request.files.get('image_file'),
        image_url_form=(request.form.get('image_url') or '').strip() or None,
        clear_image=request.form.get('clear_image') == '1',
    )
    if img_err:
        flash(img_err, 'danger')
        return redirect(url_for('eposone.eposone_section', slug='products'))
    payload = {
        'product_ref': (request.form.get('product_ref') or '').strip(),
        'name': (request.form.get('name') or '').strip(),
        'product_type': (request.form.get('product_type') or 'good').strip().lower(),
        'unit_price': request.form.get('unit_price') or 0,
        'currency': (request.form.get('currency') or 'USD').strip().upper() or 'USD',
        'description': (request.form.get('description') or '').strip() or None,
        'tracks_inventory': request.form.get('tracks_inventory') == '1',
        'barcode': (request.form.get('barcode') or '').strip() or None,
        'cost_price': request.form.get('cost_price'),
        'min_stock': request.form.get('min_stock'),
        'max_stock': request.form.get('max_stock'),
        'category': (request.form.get('category') or '').strip() or None,
        'image_url': image_url,
        'uom': (request.form.get('uom') or 'und').strip() or 'und',
        'purchase_uom': (request.form.get('purchase_uom') or '').strip() or None,
        'pack_factor': request.form.get('pack_factor') or 1,
        'source_app_id': 'eposone',
    }
    try:
        dto = ProductService.create(int(oid), payload)
    except MasterDataError as exc:
        flash(str(exc).replace('_', ' '), 'danger')
        return redirect(url_for('eposone.eposone_section', slug='products'))
    flash(f'Producto {dto.name} ({dto.product_ref}) creado.', 'success')
    return redirect(url_for('eposone.eposone_section', slug='products'))


@eposone_bp.route('/products/<product_ref>/update', methods=['POST'])
@login_required
def eposone_product_update(product_ref: str):
    denied = _require_eposone_admin()
    if denied is not None:
        return denied
    from nodeone.core.master.constants import MasterDataError
    from nodeone.core.platform.runtime import resolve_organization_id
    from nodeone.core.services.product import ProductService
    from nodeone.services.product_image_storage import resolve_product_image_url

    oid = resolve_organization_id()
    if oid is None:
        abort(400)
    existing = ProductService.get_by_ref(int(oid), product_ref)
    if existing is None:
        flash('Producto no encontrado.', 'danger')
        return redirect(url_for('eposone.eposone_section', slug='products'))
    image_url, img_err = resolve_product_image_url(
        organization_id=int(oid),
        file_storage=request.files.get('image_file'),
        image_url_form=(request.form.get('image_url') or '').strip() or None,
        clear_image=request.form.get('clear_image') == '1',
        existing_url=existing.image_url,
    )
    if img_err:
        flash(img_err, 'danger')
        return redirect(url_for('eposone.eposone_section', slug='products'))
    payload = {
        'name': (request.form.get('name') or '').strip(),
        'product_type': (request.form.get('product_type') or 'good').strip().lower(),
        'unit_price': request.form.get('unit_price') or 0,
        'currency': (request.form.get('currency') or 'USD').strip().upper() or 'USD',
        'description': (request.form.get('description') or '').strip() or None,
        'tracks_inventory': request.form.get('tracks_inventory') == '1',
        'status': (request.form.get('status') or 'active').strip().lower(),
        'barcode': (request.form.get('barcode') or '').strip() or None,
        'cost_price': request.form.get('cost_price'),
        'min_stock': request.form.get('min_stock'),
        'max_stock': request.form.get('max_stock'),
        'category': (request.form.get('category') or '').strip() or None,
        'image_url': image_url,
        'uom': (request.form.get('uom') or 'und').strip() or 'und',
        'purchase_uom': (request.form.get('purchase_uom') or '').strip() or None,
        'pack_factor': request.form.get('pack_factor') or 1,
    }
    try:
        dto = ProductService.update(int(oid), product_ref, payload)
    except MasterDataError as exc:
        flash(str(exc).replace('_', ' '), 'danger')
        return redirect(url_for('eposone.eposone_section', slug='products'))
    flash(f'Producto {dto.name} actualizado.', 'success')
    return redirect(url_for('eposone.eposone_section', slug='products'))


@eposone_bp.route('/products/<product_ref>/delete', methods=['POST'])
@login_required
def eposone_product_delete(product_ref: str):
    denied = _require_eposone_admin()
    if denied is not None:
        return denied
    from nodeone.core.master.constants import MasterDataError
    from nodeone.core.platform.runtime import resolve_organization_id
    from nodeone.core.services.product import ProductService

    oid = resolve_organization_id()
    if oid is None:
        abort(400)
    try:
        ProductService.delete(int(oid), product_ref)
    except MasterDataError as exc:
        code = str(exc)
        if code == 'product_has_movements':
            flash(
                'No se puede eliminar: tiene movimientos o pedidos. Desactivalo en su lugar.',
                'warning',
            )
        else:
            flash(code.replace('_', ' '), 'danger')
        return redirect(url_for('eposone.eposone_section', slug='products'))
    flash(f'Producto {product_ref} eliminado.', 'success')
    return redirect(url_for('eposone.eposone_section', slug='products'))


@eposone_bp.route('/products/<product_ref>/deactivate', methods=['POST'])
@login_required
def eposone_product_deactivate(product_ref: str):
    denied = _require_eposone_admin()
    if denied is not None:
        return denied
    from nodeone.core.master.constants import MasterDataError
    from nodeone.core.platform.runtime import resolve_organization_id
    from nodeone.core.services.product import ProductService

    oid = resolve_organization_id()
    if oid is None:
        abort(400)
    try:
        dto = ProductService.deactivate(int(oid), product_ref)
    except MasterDataError as exc:
        flash(str(exc).replace('_', ' '), 'danger')
        return redirect(url_for('eposone.eposone_section', slug='products'))
    flash(f'Producto {dto.name} desactivado.', 'success')
    return redirect(url_for('eposone.eposone_section', slug='products'))


@eposone_bp.route('/branches/create', methods=['POST'])
@login_required
def eposone_branch_create():
    denied = _require_eposone_admin()
    if denied is not None:
        return denied
    from nodeone.core.master.constants import ORG_UNIT_TYPE_BRANCH, MasterDataError
    from nodeone.core.platform.runtime import resolve_organization_id
    from nodeone.core.services.org_unit import OrgUnitService

    oid = resolve_organization_id()
    if oid is None:
        abort(400)
    payload = {
        'unit_ref': (request.form.get('unit_ref') or '').strip(),
        'name': (request.form.get('name') or '').strip(),
        'unit_type': ORG_UNIT_TYPE_BRANCH,
        'notes': (request.form.get('notes') or '').strip() or None,
    }
    try:
        dto = OrgUnitService.create(int(oid), payload)
    except MasterDataError as exc:
        flash(str(exc).replace('_', ' '), 'danger')
        return redirect(url_for('eposone.eposone_section', slug='branches'))
    flash(f'Sucursal {dto.name} ({dto.unit_ref}) creada.', 'success')
    return redirect(url_for('eposone.eposone_section', slug='branches'))


@eposone_bp.route('/registers/create', methods=['POST'])
@login_required
def eposone_register_create():
    denied = _require_eposone_admin()
    if denied is not None:
        return denied
    from nodeone.core.master.constants import ORG_UNIT_TYPE_REGISTER, MasterDataError
    from nodeone.core.platform.runtime import resolve_organization_id
    from nodeone.core.services.org_unit import OrgUnitService

    oid = resolve_organization_id()
    if oid is None:
        abort(400)
    parent_raw = (request.form.get('parent_id') or '').strip()
    redirect_slug = (request.form.get('redirect_slug') or 'registers').strip()
    if redirect_slug not in ('registers', 'pos-points', 'terminals'):
        redirect_slug = 'registers'
    payload = {
        'unit_ref': (request.form.get('unit_ref') or '').strip(),
        'name': (request.form.get('name') or '').strip(),
        'unit_type': ORG_UNIT_TYPE_REGISTER,
        'parent_id': int(parent_raw) if parent_raw.isdigit() else None,
        'notes': (request.form.get('notes') or '').strip() or None,
    }
    try:
        dto = OrgUnitService.create(int(oid), payload)
    except MasterDataError as exc:
        flash(str(exc).replace('_', ' '), 'danger')
        return redirect(url_for('eposone.eposone_section', slug=redirect_slug))
    flash(f'Caja {dto.name} ({dto.unit_ref}) creada.', 'success')
    return redirect(url_for('eposone.eposone_section', slug=redirect_slug))


@eposone_bp.route('/warehouses/create', methods=['POST'])
@login_required
def eposone_warehouse_create():
    denied = _require_eposone_admin()
    if denied is not None:
        return denied
    from nodeone.core.master.constants import ORG_UNIT_TYPE_WAREHOUSE, MasterDataError
    from nodeone.core.platform.runtime import resolve_organization_id
    from nodeone.core.services.org_unit import OrgUnitService

    oid = resolve_organization_id()
    if oid is None:
        abort(400)
    parent_raw = (request.form.get('parent_id') or '').strip()
    payload = {
        'unit_ref': (request.form.get('unit_ref') or '').strip(),
        'name': (request.form.get('name') or '').strip(),
        'unit_type': ORG_UNIT_TYPE_WAREHOUSE,
        'parent_id': int(parent_raw) if parent_raw.isdigit() else None,
        'notes': (request.form.get('notes') or '').strip() or None,
    }
    try:
        dto = OrgUnitService.create(int(oid), payload)
    except MasterDataError as exc:
        flash(str(exc).replace('_', ' '), 'danger')
        return redirect(url_for('eposone.eposone_section', slug='inventory'))
    flash(f'Bodega {dto.name} ({dto.unit_ref}) creada.', 'success')
    return redirect(url_for('eposone.eposone_section', slug='inventory'))


@eposone_bp.route('/stock/adjust', methods=['POST'])
@login_required
def eposone_stock_adjust():
    denied = _require_eposone_admin()
    if denied is not None:
        return denied
    from nodeone.core.commerce.order import OrderValidationError
    from nodeone.core.commerce.stock import StockService, StockValidationError
    from nodeone.core.platform.runtime import resolve_organization_id

    oid = resolve_organization_id()
    if oid is None:
        abort(400)
    warehouse_raw = (request.form.get('warehouse_org_unit_id') or '').strip()
    payload = {
        'warehouse_org_unit_id': int(warehouse_raw) if warehouse_raw.isdigit() else None,
        'product_ref': (request.form.get('product_ref') or '').strip(),
        'quantity': request.form.get('quantity') or 0,
        'notes': (request.form.get('notes') or '').strip() or None,
        'supervisor_user_id': getattr(current_user, 'id', None),
    }
    try:
        StockService.record_manual_adjust(int(oid), payload, source_app_id='eposone')
    except (StockValidationError, OrderValidationError) as exc:
        flash(str(exc).replace('_', ' '), 'danger')
        return redirect(url_for('eposone.eposone_section', slug='inventory'))
    flash('Ajuste de stock registrado.', 'success')
    return redirect(url_for('eposone.eposone_section', slug='inventory'))


@eposone_bp.route('/contacts/create', methods=['POST'])
@login_required
def eposone_contact_create():
    denied = _require_eposone_admin()
    if denied is not None:
        return denied
    from nodeone.core.platform.runtime import resolve_organization_id
    from nodeone.core.services.contacts import ContactService

    oid = resolve_organization_id()
    if oid is None:
        abort(400)
    payload = {
        'contact_type': (request.form.get('contact_type') or 'person').strip(),
        'display_name': (request.form.get('display_name') or '').strip(),
        'first_name': (request.form.get('first_name') or '').strip(),
        'last_name': (request.form.get('last_name') or '').strip(),
        'email': (request.form.get('email') or '').strip(),
        'phone': (request.form.get('phone') or '').strip(),
        'mobile': (request.form.get('mobile') or '').strip(),
        'tax_id': (request.form.get('tax_id') or '').strip(),
        'identification_type': (request.form.get('identification_type') or 'consumer_final').strip(),
        'is_customer': request.form.get('is_customer') == '1',
        'active': True,
    }
    try:
        dto = ContactService.create(int(oid), payload)
    except ContactService.ValidationError as exc:
        flash(str(exc), 'danger')
        return redirect(url_for('eposone.eposone_section', slug='contacts'))
    flash(f'Cliente {dto.display_name} creado correctamente.', 'success')
    return redirect(url_for('eposone.eposone_section', slug='contacts', q=dto.display_name))


@eposone_bp.route('/orders/new', methods=['GET', 'POST'])
@login_required
def eposone_order_new():
    denied = _require_eposone_admin()
    if denied is not None:
        return denied
    from nodeone.core.commerce.order import OrderService, OrderValidationError
    from nodeone.core.platform.runtime import resolve_organization_id
    from nodeone.core.services.contacts import ContactService
    from nodeone.core.services.product import ProductService

    oid = resolve_organization_id()
    if oid is None:
        abort(400)
    contacts, _ = ContactService.search(int(oid), limit=100)
    products = ProductService.search(int(oid), limit=100)
    form_data = {
        'contact_id': '',
        'product_ref': '',
        'description': '',
        'quantity': '1',
        'unit_price': '',
        'notes': '',
    }

    if request.method == 'POST':
        form_data = {
            'contact_id': (request.form.get('contact_id') or '').strip(),
            'product_ref': (request.form.get('product_ref') or '').strip(),
            'description': (request.form.get('description') or '').strip(),
            'quantity': (request.form.get('quantity') or '1').strip(),
            'unit_price': (request.form.get('unit_price') or '').strip(),
            'notes': (request.form.get('notes') or '').strip(),
        }
        try:
            qty = float(form_data['quantity'] or 1)
            unit_price = float(form_data['unit_price'] or 0)
        except ValueError:
            flash('Cantidad o precio no válidos.', 'danger')
            return render_template(
                'eposone/order_new.html',
                contacts=contacts,
                products=products,
                form_data=form_data,
            )
        line: dict = {
            'description': form_data['description'],
            'quantity': qty,
            'unit_price': unit_price,
        }
        if form_data['product_ref']:
            line['product_ref'] = form_data['product_ref']
        body: dict = {'lines': [line]}
        if form_data['notes']:
            body['notes'] = form_data['notes']
        if form_data['contact_id']:
            body['contact_id'] = int(form_data['contact_id'])
        try:
            dto = OrderService.create(int(oid), body, source_app_id='eposone')
        except OrderValidationError as exc:
            flash(str(exc).replace('_', ' '), 'danger')
            return render_template(
                'eposone/order_new.html',
                contacts=contacts,
                products=products,
                form_data=form_data,
            )
        flash(f'Pedido {dto.order_ref} creado.', 'success')
        return redirect(url_for('eposone.eposone_order_detail', order_id=dto.id))

    return render_template(
        'eposone/order_new.html',
        contacts=contacts,
        products=products,
        form_data=form_data,
    )


@eposone_bp.route('/section/<slug>')
@login_required
def eposone_section(slug: str):
    denied = _require_eposone_admin()
    if denied is not None:
        return denied
    key = (slug or '').strip().lower()
    if key not in EPOSONE_SECTION_SLUGS:
        abort(404)
    title, description = EPOSONE_SECTIONS[key]
    if key == 'orders':
        from models.eposone_order import EposoneOrder
        from nodeone.core.platform.runtime import resolve_organization_id

        oid = resolve_organization_id()
        orders: list = []
        orders_total = 0
        status_filter = (request.args.get('status') or '').strip() or None
        payment_filter = (request.args.get('payment_status') or '').strip() or None
        if oid is not None:
            q = EposoneOrder.query.filter_by(organization_id=int(oid))
            if status_filter:
                q = q.filter_by(status=status_filter)
            if payment_filter:
                q = q.filter_by(payment_status=payment_filter)
            orders = q.order_by(EposoneOrder.id.desc()).limit(100).all()
            orders_total = len(orders)
        return render_template(
            'eposone/orders_domain.html',
            section_slug=key,
            section_title=title,
            section_description=description,
            orders=orders,
            orders_total=orders_total,
            status_filter=status_filter or '',
            payment_filter=payment_filter or '',
        )
    if key == 'contacts':
        from nodeone.core.platform.runtime import resolve_organization_id
        from nodeone.core.services.contacts import ContactService

        oid = resolve_organization_id()
        contacts: list = []
        contacts_total = 0
        q = (request.args.get('q') or '').strip()
        if oid is not None:
            contacts, contacts_total = ContactService.search(int(oid), q=q, limit=50)
        return render_template(
            'eposone/contacts.html',
            section_slug=key,
            section_title=title,
            section_description=description,
            contacts=contacts,
            contacts_total=contacts_total,
            search_q=q,
        )
    if key == 'products':
        from nodeone.core.platform.runtime import resolve_organization_id
        from nodeone.core.services.product import ProductService

        oid = resolve_organization_id()
        products: list = []
        can_delete_by_ref: dict[str, bool] = {}
        categories: list[str] = []
        if oid is not None:
            products = ProductService.search(int(oid), limit=100)
            for p in products:
                can_delete_by_ref[p.product_ref] = not ProductService.has_operational_usage(
                    int(oid), p.product_ref
                )
                if p.category and p.category not in categories:
                    categories.append(p.category)
            categories.sort()
        return render_template(
            'eposone/products.html',
            section_slug=key,
            section_title=title,
            section_description=description,
            products=products,
            products_total=len(products),
            can_delete_by_ref=can_delete_by_ref,
            categories=categories,
        )
    if key == 'kds':
        from nodeone.core.platform.runtime import resolve_organization_id

        oid = resolve_organization_id()
        ctx = {'ticket_rows': [], 'tickets_total': 0}
        if oid is not None:
            ctx = _kds_page_context(int(oid))
        return render_template(
            'eposone/kds.html',
            section_slug=key,
            section_title=title,
            section_description=description,
            **ctx,
        )
    if key == 'delivery':
        from nodeone.core.platform.runtime import resolve_organization_id

        oid = resolve_organization_id()
        ctx = {'delivery_rows': [], 'deliveries_total': 0}
        if oid is not None:
            ctx = _delivery_page_context(int(oid))
        return render_template(
            'eposone/delivery.html',
            section_slug=key,
            section_title=title,
            section_description=description,
            **ctx,
        )
    if key == 'digital-menu':
        from nodeone.core.platform.runtime import resolve_organization_id
        from nodeone.modules.eposone.digital_menu_service import DigitalMenuService

        oid = resolve_organization_id()
        menus: list = []
        if oid is not None:
            menus = [
                {
                    **m.to_dict(),
                    'public_url': DigitalMenuService.public_menu_url(m.public_token),
                }
                for m in DigitalMenuService.list_menus(int(oid))
            ]
        return render_template(
            'eposone/digital_menu.html',
            section_slug=key,
            section_title=title,
            section_description=description,
            menus=menus,
        )
    if key == 'promotions':
        from nodeone.core.platform.runtime import resolve_organization_id
        from nodeone.modules.eposone.promotion_service import PromotionService

        oid = resolve_organization_id()
        promotions: list = []
        if oid is not None:
            promotions = PromotionService.list_promotions(int(oid))
        return render_template(
            'eposone/promotions.html',
            section_slug=key,
            section_title=title,
            section_description=description,
            promotions=promotions,
            promotions_total=len(promotions),
        )
    if key == 'settings':
        from nodeone.core.platform.runtime import resolve_organization_id
        from nodeone.modules.eposone.settings_service import ALLOWED_CURRENCIES, EposoneSettingsService

        oid = resolve_organization_id()
        settings = EposoneSettingsService.get_settings(int(oid)) if oid is not None else None
        return render_template(
            'eposone/settings.html',
            section_slug=key,
            section_title=title,
            section_description=description,
            settings=settings,
            allowed_currencies=sorted(ALLOWED_CURRENCIES),
        )
    if key == 'branches':
        from nodeone.core.master.constants import ORG_UNIT_TYPE_BRANCH
        from nodeone.core.platform.runtime import resolve_organization_id
        from nodeone.core.services.org_unit import OrgUnitService

        oid = resolve_organization_id()
        branches: list = []
        if oid is not None:
            branches = OrgUnitService.list_units(int(oid), unit_type=ORG_UNIT_TYPE_BRANCH)
        return render_template(
            'eposone/branches.html',
            section_slug=key,
            section_title=title,
            section_description=description,
            branches=branches,
            branches_total=len(branches),
        )
    if key == 'pos-points':
        from nodeone.core.commerce.pos import PosTerminalService
        from nodeone.core.license.policy import policy_for_organization
        from nodeone.core.master.constants import (
            ORG_UNIT_TYPE_BRANCH,
            ORG_UNIT_TYPE_POS,
            ORG_UNIT_TYPE_REGISTER,
        )
        from nodeone.core.platform.runtime import resolve_organization_id
        from nodeone.core.services.org_unit import OrgUnitService

        oid = resolve_organization_id()
        pos_units: list = []
        branches: list = []
        registers: list = []
        devices: list = []
        license_info = None
        if oid is not None:
            pos_units = OrgUnitService.list_units(int(oid), unit_type=ORG_UNIT_TYPE_POS)
            branches = OrgUnitService.list_units(int(oid), unit_type=ORG_UNIT_TYPE_BRANCH)
            registers = OrgUnitService.list_units(int(oid), unit_type=ORG_UNIT_TYPE_REGISTER)
            devices = PosTerminalService.list_terminals(int(oid), limit=100)
            policy = policy_for_organization(int(oid))
            license_info = {
                'enforcement': 'disabled',
                'can_create_pos': policy.can_create_pos(),
                'limits': policy.limits.to_dict(),
            }
        devices_by_pos: dict[str, list] = {}
        registers_by_pos: dict[int, list] = {}
        for d in devices:
            pref = getattr(d, 'pos_ref', None) or ''
            devices_by_pos.setdefault(pref, []).append(d)
        for reg in registers:
            pid = getattr(reg, 'parent_id', None)
            if pid is not None:
                registers_by_pos.setdefault(int(pid), []).append(reg)
        return render_template(
            'eposone/pos_points.html',
            section_slug=key,
            section_title=title,
            section_description=description,
            pos_units=pos_units,
            pos_units_total=len(pos_units),
            branches=branches,
            registers=registers,
            devices=devices,
            devices_by_pos=devices_by_pos,
            registers_by_pos=registers_by_pos,
            license_info=license_info,
        )
    if key == 'inventory':
        from nodeone.core.commerce.stock import StockService
        from nodeone.core.master.constants import ORG_UNIT_TYPE_BRANCH, ORG_UNIT_TYPE_WAREHOUSE
        from nodeone.core.platform.runtime import resolve_organization_id
        from nodeone.core.services.org_unit import OrgUnitService
        from nodeone.core.services.product import ProductService

        oid = resolve_organization_id()
        warehouses: list = []
        stock_balances: list = []
        stock_movements: list = []
        branches: list = []
        products: list = []
        warehouse_name_by_id: dict[int, str] = {}
        product_meta_by_ref: dict[str, dict] = {}
        if oid is not None:
            warehouses = OrgUnitService.list_units(int(oid), unit_type=ORG_UNIT_TYPE_WAREHOUSE)
            stock_balances = StockService.list_balances(int(oid), limit=200)
            stock_movements = StockService.list_movements(int(oid), limit=100)
            branches = OrgUnitService.list_units(int(oid), unit_type=ORG_UNIT_TYPE_BRANCH)
            products = ProductService.search(int(oid), status='active', limit=200)
            warehouse_name_by_id = {
                int(w.id): f'{w.name} ({w.unit_ref})' for w in warehouses
            }
            for p in products:
                product_meta_by_ref[p.product_ref] = {
                    'name': p.name,
                    'uom': p.uom or 'und',
                    'min_stock': p.min_stock,
                    'max_stock': p.max_stock,
                }
        return render_template(
            'eposone/warehouses.html',
            section_slug=key,
            section_title=title,
            section_description=description,
            warehouses=warehouses,
            warehouses_total=len(warehouses),
            stock_balances=stock_balances,
            stock_balances_total=len(stock_balances),
            stock_movements=stock_movements,
            stock_movements_total=len(stock_movements),
            warehouse_name_by_id=warehouse_name_by_id,
            product_meta_by_ref=product_meta_by_ref,
            branches=branches,
            products=products,
        )
    if key == 'registers':
        from nodeone.core.master.constants import ORG_UNIT_TYPE_POS
        from nodeone.core.platform.runtime import resolve_organization_id
        from nodeone.core.services.org_unit import OrgUnitService

        oid = resolve_organization_id()
        ctx = {'register_rows': [], 'registers_total': 0, 'open_shifts_total': 0, 'recent_closed': []}
        pos_units: list = []
        if oid is not None:
            ctx = _registers_page_context(int(oid))
            pos_units = OrgUnitService.list_units(int(oid), unit_type=ORG_UNIT_TYPE_POS)
        return render_template(
            'eposone/registers.html',
            section_slug=key,
            section_title=title,
            section_description=description,
            pos_units=pos_units,
            **ctx,
        )
    if key == 'shifts':
        from nodeone.core.platform.runtime import resolve_organization_id

        oid = resolve_organization_id()
        ctx = {
            'active_shifts': [],
            'closed_shifts': [],
            'active_total': 0,
            'closed_total': 0,
            'supervisor_ok': False,
        }
        if oid is not None:
            ctx = _shifts_page_context(int(oid))
        return render_template(
            'eposone/shifts.html',
            section_slug=key,
            section_title=title,
            section_description=description,
            **ctx,
        )
    if key == 'terminals':
        from nodeone.core.commerce.pos import PosTerminalService
        from nodeone.core.master.constants import ORG_UNIT_TYPE_POS, ORG_UNIT_TYPE_REGISTER
        from nodeone.core.platform.runtime import resolve_organization_id
        from nodeone.core.services.org_unit import OrgUnitService
        from nodeone.modules.eposone.device_provisioning import DeviceProvisioningService

        oid = resolve_organization_id()
        pos_units: list = []
        devices: list = []
        registers: list = []
        provisioning_codes: list = []
        legacy_org_code = None
        if oid is not None:
            pos_units = OrgUnitService.list_units(int(oid), unit_type=ORG_UNIT_TYPE_POS)
            registers = OrgUnitService.list_units(int(oid), unit_type=ORG_UNIT_TYPE_REGISTER)
            devices = PosTerminalService.list_terminals(int(oid), limit=100)
            provisioning_codes = DeviceProvisioningService.list_codes(int(oid), active_only=True)
            legacy_org_code = DeviceProvisioningService.ensure_provisioning_code(int(oid))
        code_by_register = {c.register_ref: c for c in provisioning_codes}
        return render_template(
            'eposone/terminals.html',
            section_slug=key,
            section_title=title,
            section_description=description,
            pos_units=pos_units,
            pos_units_total=len(pos_units),
            devices=devices,
            devices_total=len(devices),
            registers=registers,
            provisioning_codes=provisioning_codes,
            code_by_register=code_by_register,
            provisioning_code=legacy_org_code,
        )
    return render_template(
        'eposone/section.html',
        section_slug=key,
        section_title=title,
        section_description=description,
    )


def _compose_links() -> list[dict[str, str]]:
    """Enlaces opcionales a herramientas de plataforma (UX-T3: sin jerga «Core»)."""
    from flask import current_app

    from nodeone.core.platform.runtime import has_saas_module, resolve_organization_id

    oid = resolve_organization_id()
    links: list[dict[str, str]] = []

    def _add(label: str, endpoint: str, module_code: str | None = None) -> None:
        if endpoint not in current_app.view_functions:
            return
        if module_code and not has_saas_module(module_code, oid):
            return
        try:
            links.append({'label': label, 'url': url_for(endpoint)})
        except Exception:
            pass

    # Solo extras no duplicados en Accesos rápidos del dashboard.
    _add('Cotizaciones', 'admin_sales_quotations', 'sales')
    _add('Inventario contable', 'contador.contador_index', 'contador')
    return links
