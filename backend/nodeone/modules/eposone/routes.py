"""Rutas HTML de EPosOne (Etapa 6–7)."""

from __future__ import annotations

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from nodeone.core.template_context_gates import user_can_see_tenant_admin_menu
from nodeone.modules.eposone.sections import EPOSONE_SECTIONS, EPOSONE_SECTION_SLUGS

eposone_bp = Blueprint('eposone', __name__, url_prefix='/admin/eposone')

# Query params del listado Pedidos que se preservan al abrir/volver del detalle.
_ORDERS_LIST_FILTER_KEYS = (
    'q',
    'from',
    'to',
    'status',
    'payment_status',
    'table',
    'register',
    'pos',
    'cashier',
    'customer',
    'page',
    'per_page',
)

_ORDERS_PER_PAGE_CHOICES = (15, 25, 50, 100)
_ORDERS_PER_PAGE_DEFAULT = 15


def _orders_list_filter_args(args=None) -> dict[str, str]:
    src = args if args is not None else request.args
    out: dict[str, str] = {}
    for key in _ORDERS_LIST_FILTER_KEYS:
        val = (src.get(key) or '').strip()
        if val:
            out[key] = val
    return out


def _orders_list_url(filter_args: dict[str, str] | None = None) -> str:
    params = filter_args if filter_args is not None else _orders_list_filter_args()
    return url_for('eposone.eposone_section', slug='orders', **params)


def _user_prefs_dict(user) -> dict:
    import json

    from app import UserSettings, _default_user_preferences

    prefs = dict(_default_user_preferences())
    if user is None or not getattr(user, 'is_authenticated', False):
        return prefs
    try:
        row = UserSettings.query.filter_by(user_id=int(user.id)).first()
        if row and row.preferences:
            loaded = json.loads(row.preferences)
            if isinstance(loaded, dict):
                prefs.update(loaded)
    except Exception:
        pass
    return prefs


def _resolve_orders_per_page(user) -> tuple[int, bool]:
    """Devuelve (per_page, should_persist). Preferencia usuario; query ?per_page= gana y se guarda."""
    raw = (request.args.get('per_page') or '').strip()
    from_query = False
    if raw:
        try:
            candidate = int(raw)
            if candidate in _ORDERS_PER_PAGE_CHOICES:
                from_query = True
                return candidate, True
        except (TypeError, ValueError):
            pass
    prefs = _user_prefs_dict(user)
    try:
        saved = int(prefs.get('eposone_orders_per_page') or _ORDERS_PER_PAGE_DEFAULT)
    except (TypeError, ValueError):
        saved = _ORDERS_PER_PAGE_DEFAULT
    if saved not in _ORDERS_PER_PAGE_CHOICES:
        saved = _ORDERS_PER_PAGE_DEFAULT
    return saved, from_query


def _persist_orders_per_page(user, per_page: int) -> None:
    import json

    from app import UserSettings, _default_user_preferences, db

    if user is None or not getattr(user, 'is_authenticated', False):
        return
    if per_page not in _ORDERS_PER_PAGE_CHOICES:
        return
    prefs = _user_prefs_dict(user)
    if int(prefs.get('eposone_orders_per_page') or 0) == int(per_page):
        return
    prefs['eposone_orders_per_page'] = int(per_page)
    # Solo keys conocidas + merge ya hecho
    defaults = _default_user_preferences()
    clean = {k: prefs.get(k, defaults.get(k)) for k in defaults}
    clean['eposone_orders_per_page'] = int(per_page)
    payload = json.dumps(clean)
    row = UserSettings.query.filter_by(user_id=int(user.id)).first()
    if not row:
        row = UserSettings(user_id=int(user.id), preferences=payload)
        db.session.add(row)
    else:
        # merge con existentes para no perder keys extras
        try:
            existing = json.loads(row.preferences) if row.preferences else {}
            if not isinstance(existing, dict):
                existing = {}
        except (TypeError, ValueError, json.JSONDecodeError):
            existing = {}
        existing.update(clean)
        row.preferences = json.dumps(existing)
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()


@eposone_bp.app_template_filter('epos_local')
def _epos_local_filter(value, fmt='%d/%m %H:%M'):
    """UTC naive → hora de negocio (America/Panama) para templates EPosOne."""
    from nodeone.modules.eposone.timefmt import format_business_dt

    return format_business_dt(value, fmt=fmt)


def _require_eposone_admin():
    if not user_can_see_tenant_admin_menu(current_user):
        return redirect(url_for('dashboard'))
    return None


def _require_platform_lab_wipe() -> None:
    """Solo User.is_admin (plataforma). No alcanza admin tenant / RBAC."""
    from nodeone.modules.eposone.dev_wipe_service import wipe_tool_enabled

    if not getattr(current_user, 'is_admin', False):
        abort(403)
    if not wipe_tool_enabled():
        abort(404)


@eposone_bp.route('/lab/wipe-today', methods=['GET', 'POST'])
@login_required
def eposone_lab_wipe_today():
    """Lab QA: borrar transacciones del día (solo platform admin + entorno dev)."""
    _require_platform_lab_wipe()

    from nodeone.core.platform.runtime import resolve_organization_id
    from nodeone.modules.eposone.dev_wipe_service import CONFIRM_PHRASE, preview_today, wipe_today

    oid = resolve_organization_id()
    if oid is None:
        flash('Seleccioná una organización activa.', 'warning')
        return redirect(url_for('dashboard'))

    preview = preview_today(int(oid))
    if request.method == 'POST':
        phrase = (request.form.get('confirm_phrase') or '').strip()
        if phrase != CONFIRM_PHRASE:
            flash(f'Debés escribir exactamente: {CONFIRM_PHRASE}', 'danger')
            return render_template(
                'eposone/lab_wipe_today.html',
                preview=preview,
                organization_id=int(oid),
            )
        actor = (
            getattr(current_user, 'email', None)
            or getattr(current_user, 'username', None)
            or f'user-{getattr(current_user, "id", "")}'
        )
        result = wipe_today(int(oid), actor=str(actor))
        flash(
            (
                f"Lab wipe {result['day_local']}: "
                f"{result['deleted_orders']} pedido(s), "
                f"{result['deleted_shifts']} turno(s), "
                f"{result['deleted_commercial']} commercial."
            ),
            'success',
        )
        return redirect(url_for('eposone.eposone_lab_wipe_today'))

    return render_template(
        'eposone/lab_wipe_today.html',
        preview=preview,
        organization_id=int(oid),
    )


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


def _redirect_cashiers():
    return redirect(url_for('eposone.eposone_section', slug='cashiers'))


def _cashier_contacts_for_org(organization_id: int, *, active_only: bool | None = True) -> list:
    from nodeone.modules.eposone.cashier_service import CashierService

    return CashierService.list_cashiers(int(organization_id), active_only=active_only)


def _cashier_from_form(organization_id: int):
    from nodeone.modules.eposone.cashier_service import CashierService

    raw = (request.form.get('cashier_contact_id') or '').strip()
    try:
        cashier_id = int(raw)
    except (TypeError, ValueError):
        return None
    cashier = CashierService.get(int(organization_id), cashier_id)
    if cashier is None or not cashier.active:
        return None
    return cashier


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


def _redirect_settings_module(slug: str = 'kds'):
    """Tras guardar opciones operativas, volver al módulo dueño (no a un hub)."""
    allowed = {'kds', 'registers', 'orders'}
    target = (slug or 'kds').strip()
    if target not in allowed:
        target = 'kds'
    return redirect(url_for('eposone.eposone_section', slug=target))


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


def _cash_shift_state(shift_row) -> dict:
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
    return {
        'shift': shift_dto,
        'expected_balance': expected_balance,
        'can_reconcile': can_reconcile,
        'can_close': can_close,
        'can_move': can_move,
    }


def _shift_operational_row(
    organization_id: int,
    shift_row,
    *,
    registers_by_ref: dict,
) -> dict:
    from models.commercial_core import CoreCashMovement

    state = _cash_shift_state(shift_row)
    reg = registers_by_ref.get(str(shift_row.register_ref))
    movement_count = CoreCashMovement.query.filter_by(
        organization_id=int(organization_id),
        shift_id=int(shift_row.id),
    ).count()
    return {
        **state,
        'register_ref': str(shift_row.register_ref),
        'register_name': str(getattr(reg, 'name', None) or shift_row.register_ref),
        'movement_count': int(movement_count),
    }


def _registers_page_context(organization_id: int) -> dict:
    from models.commercial_core import CoreCashShift, CorePosTerminal
    from nodeone.core.commerce.constants import CASH_SHIFT_CLOSED, CASH_SHIFT_OPEN, CASH_SHIFT_RECONCILING
    from nodeone.core.commerce.persistence import cash_shift_to_dto
    from nodeone.core.master.constants import (
        ORG_UNIT_TYPE_BRANCH,
        ORG_UNIT_TYPE_POS,
        ORG_UNIT_TYPE_REGISTER,
    )
    from nodeone.core.services.org_unit import OrgUnitService
    from nodeone.modules.eposone.device_provisioning import DeviceProvisioningService

    oid = int(organization_id)
    registers = OrgUnitService.list_units(oid, unit_type=ORG_UNIT_TYPE_REGISTER)
    pos_units = OrgUnitService.list_units(oid, unit_type=ORG_UNIT_TYPE_POS)
    branches = OrgUnitService.list_units(oid, unit_type=ORG_UNIT_TYPE_BRANCH)
    pos_by_id = {int(p.id): p for p in pos_units}
    branch_by_id = {int(b.id): b for b in branches}

    devices = (
        CorePosTerminal.query.filter_by(organization_id=oid)
        .order_by(CorePosTerminal.id.desc())
        .all()
    )
    device_by_register: dict[str, object] = {}
    for d in devices:
        ref = (d.register_ref or '').strip()
        if ref and ref not in device_by_register:
            device_by_register[ref] = d

    try:
        codes = DeviceProvisioningService.list_codes(oid, active_only=True)
    except Exception:
        codes = []
    code_by_register = {
        str(c.register_ref): c for c in codes if getattr(c, 'register_ref', None)
    }

    active_shifts = (
        CoreCashShift.query.filter(
            CoreCashShift.organization_id == oid,
            CoreCashShift.status.in_((CASH_SHIFT_OPEN, CASH_SHIFT_RECONCILING)),
        )
        .order_by(CoreCashShift.register_ref.asc())
        .all()
    )
    shift_by_register = {str(row.register_ref): row for row in active_shifts}

    from nodeone.modules.eposone.register_license_service import RegisterLicenseService

    register_rows: list[dict] = []
    for reg in registers:
        ref = str(reg.unit_ref)
        shift_row = shift_by_register.get(ref)
        shift_dto = None
        expected_balance = None
        device = device_by_register.get(ref)
        has_device = device is not None
        can_open = shift_row is None and has_device
        can_reconcile = False
        can_close = False
        if shift_row is not None:
            shift_state = _cash_shift_state(shift_row)
            shift_dto = shift_state['shift']
            expected_balance = shift_state['expected_balance']
            can_reconcile = shift_state['can_reconcile']
            can_close = shift_state['can_close']

        pos = pos_by_id.get(int(reg.parent_id)) if reg.parent_id is not None else None
        branch = None
        if pos is not None and pos.parent_id is not None:
            branch = branch_by_id.get(int(pos.parent_id))

        prov = DeviceProvisioningService.get_active_code_for_register(oid, ref)

        if shift_row is not None:
            ui_status = 'open' if str(shift_row.status) == CASH_SHIFT_OPEN else 'reconciling'
        elif not has_device:
            ui_status = 'code_pending' if prov is not None else 'no_device'
        elif str(getattr(reg, 'status', '') or '') not in ('', 'active'):
            ui_status = 'blocked'
        else:
            last_seen = getattr(device, 'last_seen_at', None) if device else None
            ui_status = 'assigned' if last_seen else 'disconnected'

        lic = RegisterLicenseService.snapshot(oid, ref)
        register_rows.append(
            {
                'register': reg,
                'shift': shift_dto,
                'expected_balance': expected_balance,
                'can_open': can_open,
                'can_reconcile': can_reconcile,
                'can_close': can_close,
                'has_device': has_device,
                'ui_status': ui_status,
                'pos_name': pos.name if pos is not None else None,
                'pos_ref': pos.unit_ref if pos is not None else None,
                'branch_name': branch.name if branch is not None else None,
                'device': device,
                'provisioning_code': getattr(prov, 'code', None) if prov is not None else None,
                'provisioning_expires_at': getattr(prov, 'expires_at', None) if prov is not None else None,
                'license': lic,
                'commercial_ui': lic.commercial_ui,
                'commercial_key': lic.commercial_ui_key(),
                'can_operate': lic.can_operate,
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
        'cashier_contacts': _cashier_contacts_for_org(oid),
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
        'supervisor_ok': supervisor_ok,
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

    board = None
    oid = resolve_organization_id()
    range_key = (request.args.get('range') or 'hoy').strip().lower()
    date_from = (request.args.get('from') or '').strip() or None
    date_to = (request.args.get('to') or '').strip() or None
    if oid is not None:
        board = CommerceDashboardService.build_operational_dashboard(
            int(oid),
            range_key=range_key,
            date_from=date_from,
            date_to=date_to,
        )
    kpis = board['kpis'] if board else None
    return render_template(
        'eposone/dashboard.html',
        board=board,
        kpis=kpis,
        dash_range=(board or {}).get('range') or range_key,
        dash_from=(board or {}).get('date_from') or date_from or '',
        dash_to=(board or {}).get('date_to') or date_to or '',
        dashboard_refresh_seconds=30,
        filter_action=url_for('eposone.eposone_home'),
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
    redirect_slug = (request.form.get('redirect_slug') or 'terminals').strip()
    if redirect_slug not in ('terminals', 'registers', 'pos-points'):
        redirect_slug = 'terminals'
    if oid is None or not register_ref:
        flash('Falta register_ref (caja).', 'warning')
        return redirect(url_for('eposone.eposone_section', slug=redirect_slug))
    try:
        row = DeviceProvisioningService.issue_code_for_register(int(oid), register_ref=register_ref)
        flash(
            f'Código generado para {register_ref}. Cópialo desde el panel de la caja (válido una sola vez).',
            'success',
        )
        return redirect(
            url_for('eposone.eposone_section', slug=redirect_slug, issued=register_ref)
        )
    except DeviceProvisioningError as exc:
        flash(f'No se pudo generar código: {exc.code}', 'danger')
    return redirect(url_for('eposone.eposone_section', slug=redirect_slug))


@eposone_bp.route('/registers/<register_ref>/license', methods=['POST'])
@login_required
def eposone_register_license_set(register_ref: str):
    """Admin: activar/extender licencia comercial de una Caja (no es provisioning)."""
    denied = _require_eposone_admin()
    if denied is not None:
        return denied
    from flask import flash, redirect, request, url_for

    from nodeone.core.platform.runtime import resolve_organization_id
    from nodeone.modules.eposone.register_license_service import (
        LICENSE_TYPE_COURTESY,
        LICENSE_TYPE_PERPETUAL,
        LICENSE_TYPE_SUBSCRIPTION,
        LICENSE_TYPE_TRIAL,
        RegisterLicenseService,
    )

    oid = resolve_organization_id()
    if oid is None:
        abort(400)
    action = (request.form.get('action') or 'activate').strip().lower()
    uid = getattr(current_user, 'id', None)
    try:
        if action == 'extend':
            days = int(request.form.get('days') or 30)
            RegisterLicenseService.extend(
                int(oid), register_ref, days=days, notes=request.form.get('notes'), user_id=uid
            )
            flash(f'Licencia de {register_ref} extendida {days} día(s).', 'success')
        elif action == 'courtesy':
            days_raw = (request.form.get('days') or '').strip()
            RegisterLicenseService.activate(
                int(oid),
                register_ref,
                license_type=LICENSE_TYPE_COURTESY,
                duration_days=int(days_raw) if days_raw.isdigit() else None,
                notes=request.form.get('notes'),
                reason=request.form.get('reason') or 'courtesy',
                user_id=uid,
            )
            flash(f'Cortesía aplicada a {register_ref}.', 'success')
        elif action == 'perpetual':
            RegisterLicenseService.activate(
                int(oid),
                register_ref,
                license_type=LICENSE_TYPE_PERPETUAL,
                notes=request.form.get('notes'),
                reason='admin_perpetual',
                user_id=uid,
            )
            flash(f'Licencia permanente en {register_ref}.', 'success')
        else:
            ltype = (request.form.get('license_type') or LICENSE_TYPE_TRIAL).strip()
            days_raw = (request.form.get('days') or '').strip()
            days = int(days_raw) if days_raw.isdigit() else None
            RegisterLicenseService.activate(
                int(oid),
                register_ref,
                license_type=ltype if ltype != 'active' else LICENSE_TYPE_SUBSCRIPTION,
                duration_days=days,
                notes=request.form.get('notes'),
                reason=request.form.get('reason') or 'admin_activate',
                user_id=uid,
                mark_trial_used=(ltype == LICENSE_TYPE_TRIAL),
            )
            flash(f'Licencia actualizada en {register_ref}.', 'success')
    except Exception as exc:
        flash(f'No se pudo actualizar licencia: {exc}', 'danger')
    return redirect(url_for('eposone.eposone_section', slug='registers'))


@eposone_bp.route('/analytics')
@login_required
def eposone_analytics():
    """Legacy UX-T4: redirige al Dashboard V2 (una sola pantalla operativa)."""
    denied = _require_eposone_admin()
    if denied is not None:
        return denied
    # Conserva querystring por si llega con filtros futuros.
    qs = request.query_string.decode('utf-8') if request.query_string else ''
    target = url_for('eposone.eposone_home')
    if qs:
        target = f'{target}?{qs}'
    return redirect(target)


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
    """Detalle Order Domain Hito 3 (eposone_order) — cobro BO vía /api/v1/orders/{id}/payments."""
    denied = _require_eposone_admin()
    if denied is not None:
        return denied
    from models.core_master import CoreProduct
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

    refs = {str(it.product_ref) for it in (order.items or []) if it.product_ref}
    product_names: dict[str, str] = {}
    if refs:
        for row in CoreProduct.query.filter(
            CoreProduct.organization_id == int(oid),
            CoreProduct.product_ref.in_(list(refs)),
        ).all():
            product_names[str(row.product_ref)] = str(row.name)

    _EVENT_TITLES = {
        'pedido.creado': 'Pedido creado',
        'pedido.actualizado': 'Pedido actualizado',
        'pedido.dividido': 'Pedido dividido',
        'producto.agregado': 'Producto agregado',
        'producto.eliminado': 'Producto quitado',
        'cantidad.modificada': 'Cantidad modificada',
        'pedido.enviado': 'Enviado a cocina',
        'linea.lista': 'Línea lista',
        'pedido.listo': 'Listo',
        'linea.entregada': 'Línea entregada',
        'pedido.entregado': 'Entregado',
        'pago.registrado': 'Pago',
        'pedido.cobrado': 'Cobrado',
        'linea.cancelada': 'Línea cancelada',
        'pedido.anulado': 'Anulado',
        'pedido.devuelto': 'Devuelto',
    }
    from nodeone.modules.eposone.timefmt import format_business_dt

    timeline: list[dict] = []
    if order.opened_at:
        timeline.append(
            {
                'title': 'Pedido creado',
                'at': format_business_dt(order.opened_at, '%Y-%m-%d %H:%M:%S'),
                'meta': order.en1_number,
            }
        )
    for ev in events:
        etype = str(ev.type or '')
        title = _EVENT_TITLES.get(etype) or etype.replace('.', ' · ').replace('_', ' ')
        # Evitar duplicar "Pedido creado" si el primer evento lo repite
        if etype in {'pedido.creado'} and timeline:
            continue
        timeline.append(
            {
                'title': title,
                'at': format_business_dt(ev.occurred_at, '%Y-%m-%d %H:%M:%S') if ev.occurred_at else '',
                'meta': ev.actor_user_ref or ev.actor_device_uuid or '',
            }
        )
    if order.financially_closed and not any('Cerrado' in (s.get('title') or '') for s in timeline):
        timeline.append(
            {
                'title': 'Cerrado',
                'at': format_business_dt(order.updated_at, '%Y-%m-%d %H:%M:%S') if order.updated_at else '',
                'meta': '',
            }
        )

    payment_methods: list[dict] = []
    payment_method_labels: dict[str, str] = {}
    try:
        from nodeone.modules.eposone.order_payment_service import OrderPaymentService

        payment_methods = OrderPaymentService.list_methods(int(oid), enabled_only=True)
        payment_method_labels = {m['method_key']: m['label'] for m in payment_methods}
    except Exception:
        payment_methods = []

    order_origin = None
    try:
        from models.commercial_core import CorePosTerminal
        from nodeone.modules.eposone.bo_actor import order_origin_meta

        t = None
        if order.owner_device_uuid:
            t = CorePosTerminal.query.filter_by(
                organization_id=int(oid), terminal_ref=str(order.owner_device_uuid)
            ).first()
        order_origin = order_origin_meta(
            owner_device_uuid=order.owner_device_uuid,
            device_label=getattr(t, 'device_label', None) if t else None,
            profile=getattr(t, 'profile', None) if t else None,
        )
    except Exception:
        order_origin = None

    return render_template(
        'eposone/order_domain_detail.html',
        order=order,
        events=events,
        product_names=product_names,
        timeline=timeline,
        payment_methods=payment_methods,
        payment_method_labels=payment_method_labels,
        order_origin=order_origin,
        orders_back_url=_orders_list_url(_orders_list_filter_args()),
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


@eposone_bp.route('/cashiers/create', methods=['POST'])
@login_required
def eposone_cashier_create():
    denied = _require_eposone_admin()
    if denied is not None:
        return denied
    from nodeone.core.platform.runtime import resolve_organization_id
    from nodeone.modules.eposone.cashier_service import CashierService, CashierValidationError

    oid = resolve_organization_id()
    if oid is None:
        abort(400)
    try:
        dto = CashierService.create(
            int(oid),
            {
                'display_name': request.form.get('display_name'),
                'email': request.form.get('email'),
                'phone': request.form.get('phone'),
                'pin': request.form.get('pin'),
            },
        )
    except CashierValidationError as exc:
        flash(str(exc), 'danger')
        return _redirect_cashiers()
    flash(f'Cajero {dto.display_name} creado.', 'success')
    return _redirect_cashiers()


@eposone_bp.route('/cashiers/<int:cashier_id>/update', methods=['POST'])
@login_required
def eposone_cashier_update(cashier_id: int):
    denied = _require_eposone_admin()
    if denied is not None:
        return denied
    from nodeone.core.platform.runtime import resolve_organization_id
    from nodeone.modules.eposone.cashier_service import CashierService, CashierValidationError

    oid = resolve_organization_id()
    if oid is None:
        abort(400)
    try:
        dto = CashierService.update(
            int(oid),
            int(cashier_id),
            {
                'display_name': request.form.get('display_name'),
                'email': request.form.get('email'),
                'phone': request.form.get('phone'),
                'pin': request.form.get('pin'),
            },
        )
    except CashierValidationError as exc:
        flash(str(exc), 'danger')
        return _redirect_cashiers()
    flash(f'Cajero {dto.display_name} actualizado.', 'success')
    return _redirect_cashiers()


@eposone_bp.route('/cashiers/<int:cashier_id>/status', methods=['POST'])
@login_required
def eposone_cashier_status(cashier_id: int):
    denied = _require_eposone_admin()
    if denied is not None:
        return denied
    from nodeone.core.platform.runtime import resolve_organization_id
    from nodeone.modules.eposone.cashier_service import CashierService, CashierValidationError

    oid = resolve_organization_id()
    if oid is None:
        abort(400)
    active = (request.form.get('active') or '').strip() == '1'
    try:
        dto = CashierService.set_active(int(oid), int(cashier_id), active=active)
    except CashierValidationError as exc:
        flash(str(exc), 'danger')
        return _redirect_cashiers()
    flash(
        f'Cajero {dto.display_name} {"activado" if dto.active else "desactivado"}.',
        'success',
    )
    return _redirect_cashiers()


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
    # UX/arquitectura EN1-02: no abrir turno sin tablet vinculada a la caja.
    from models.commercial_core import CorePosTerminal

    has_device = (
        CorePosTerminal.query.filter_by(organization_id=int(oid), register_ref=register_ref).first()
        is not None
    )
    if not has_device:
        flash(
            'Esta caja no tiene un dispositivo asignado. '
            'Registrá una tablet con el código de provisioning antes de abrir un turno.',
            'warning',
        )
        return _redirect_registers()
    try:
        opening_balance = float(request.form.get('opening_balance') or 0)
    except ValueError:
        flash('Saldo inicial no válido.', 'danger')
        return _redirect_registers()
    cashier = _cashier_from_form(int(oid))
    if cashier is None:
        flash('Seleccioná un cajero activo de esta empresa.', 'warning')
        return _redirect_registers()
    try:
        dto = CashRegisterService.open_shift(
            int(oid),
            register_ref=register_ref,
            opening_balance=opening_balance,
            cashier_contact_id=int(cashier.id),
            cashier_name=cashier.display_name,
            assigned_by_user_id=int(current_user.id),
            source_app_id='eposone',
        )
    except OrderValidationError as exc:
        flash(str(exc).replace('_', ' '), 'danger')
        return _redirect_registers()
    flash(
        f'Turno abierto en {dto.register_ref} para {dto.cashier_name} '
        f'(saldo inicial {dto.opening_balance:.2f}).',
        'success',
    )
    return _redirect_registers()


@eposone_bp.route('/registers/<int:shift_id>/cashier', methods=['POST'])
@login_required
def eposone_register_change_cashier(shift_id: int):
    denied = _require_eposone_admin()
    if denied is not None:
        return denied
    from nodeone.core.commerce.cash import CashRegisterService
    from nodeone.core.commerce.order import OrderValidationError
    from nodeone.core.platform.runtime import resolve_organization_id

    oid = resolve_organization_id()
    if oid is None:
        abort(400)
    cashier = _cashier_from_form(int(oid))
    if cashier is None:
        flash('Seleccioná un cajero activo de esta empresa.', 'warning')
        return _redirect_registers()
    try:
        CashRegisterService.change_cashier(
            int(oid),
            int(shift_id),
            cashier_contact_id=int(cashier.id),
            cashier_name=cashier.display_name,
            changed_by_user_id=int(current_user.id),
            source_app_id='eposone',
        )
    except OrderValidationError as exc:
        flash(str(exc).replace('_', ' '), 'danger')
        return _redirect_registers()
    flash(f'Cajero actual: {cashier.display_name}.', 'success')
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
    panel = (request.form.get('settings_panel') or '').strip()
    redirect_slug = (request.form.get('redirect_slug') or '').strip()
    # Moneda no se edita desde EPosOne (herencia EN1). Opciones por módulo dueño.
    update_kwargs: dict = {}
    label = 'Opciones'
    if panel == 'kds':
        update_kwargs = {
            'kds_auto_enqueue': request.form.get('kds_auto_enqueue') == '1',
            'delivery_auto_create': request.form.get('delivery_auto_create') == '1',
        }
        label = 'Cocina (KDS)'
        redirect_slug = redirect_slug or 'kds'
    elif panel == 'fe':
        update_kwargs = {
            'fiscal_on_payment': request.form.get('fiscal_on_payment') == '1',
        }
        label = 'Facturación'
        redirect_slug = redirect_slug or 'orders'
    elif panel == 'seguridad':
        update_kwargs = {
            'supervisor_approval_required': request.form.get('supervisor_approval_required') == '1',
        }
        label = 'Caja'
        redirect_slug = redirect_slug or 'registers'
    else:
        flash('Opciones no válidas.', 'warning')
        return _redirect_settings_module(redirect_slug or 'kds')
    try:
        EposoneSettingsService.update_settings(int(oid), **update_kwargs)
    except OrderValidationError as exc:
        flash(str(exc).replace('_', ' '), 'danger')
        return _redirect_settings_module(redirect_slug or 'kds')
    flash(f'{label}: cambios guardados.', 'success')
    return _redirect_settings_module(redirect_slug or 'kds')


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
    # UX: SKU opcional en el formulario; el dominio sigue exigiendo product_ref.
    product_ref = (request.form.get('product_ref') or '').strip()
    name = (request.form.get('name') or '').strip()
    if not product_ref and name:
        import re
        import time

        base = re.sub(r'[^a-z0-9]+', '_', name.lower())[:40].strip('_') or 'prod'
        product_ref = f'{base}_{int(time.time()) % 100000:05d}'
    payload = {
        'product_ref': product_ref,
        'name': name,
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
        'fiscal_category': (request.form.get('fiscal_category') or '').strip() or None,
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
        'fiscal_category': (request.form.get('fiscal_category') or '').strip() or None,
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


@eposone_bp.route('/organization/save', methods=['POST'])
@login_required
def eposone_organization_save():
    denied = _require_eposone_admin()
    if denied is not None:
        return denied
    from models.saas import SaasOrganization
    from nodeone.core.commerce.order import OrderValidationError
    from nodeone.core.platform.runtime import resolve_organization_id
    from nodeone.modules.eposone.settings_service import EposoneSettingsService
    from app import db

    oid = resolve_organization_id()
    if oid is None:
        abort(400)
    org = SaasOrganization.query.get(int(oid))
    if org is None:
        flash('Organización no encontrada.', 'danger')
        return redirect(url_for('eposone.eposone_section', slug='organization'))
    name = (request.form.get('name') or '').strip()
    if not name:
        flash('El nombre comercial es obligatorio.', 'danger')
        return redirect(url_for('eposone.eposone_section', slug='organization'))
    org.name = name[:200]
    org.legal_name = (request.form.get('legal_name') or '').strip()[:200] or None
    org.tax_id = (request.form.get('tax_id') or '').strip()[:80] or None
    org.tax_regime = (request.form.get('tax_regime') or '').strip()[:120] or None
    org.fiscal_address = (request.form.get('fiscal_address') or '').strip()[:255] or None
    org.fiscal_city = (request.form.get('fiscal_city') or '').strip()[:120] or None
    org.fiscal_state = (request.form.get('fiscal_state') or '').strip()[:120] or None
    org.fiscal_country = (request.form.get('fiscal_country') or '').strip()[:120] or None
    org.fiscal_phone = (request.form.get('fiscal_phone') or '').strip()[:60] or None
    org.fiscal_email = (request.form.get('fiscal_email') or '').strip()[:200] or None
    org.timezone = (request.form.get('timezone') or 'America/Panama').strip()[:64] or 'America/Panama'
    currency = (request.form.get('default_currency') or '').strip().upper() or None
    try:
        if currency:
            EposoneSettingsService.update_settings(int(oid), default_currency=currency)
        db.session.commit()
    except OrderValidationError as exc:
        db.session.rollback()
        flash(str(exc).replace('_', ' '), 'danger')
        return redirect(url_for('eposone.eposone_section', slug='organization'))
    flash('Datos de empresa guardados.', 'success')
    return redirect(url_for('eposone.eposone_section', slug='organization'))


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
        return redirect(url_for('eposone.eposone_section', slug='inventory', tab='bodegas'))
    flash(f'Bodega {dto.name} ({dto.unit_ref}) creada.', 'success')
    tab = (request.form.get('redirect_tab') or 'bodegas').strip() or 'bodegas'
    return redirect(url_for('eposone.eposone_section', slug='inventory', tab=tab))


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
    tab = (request.form.get('redirect_tab') or 'ajustes').strip() or 'ajustes'
    try:
        StockService.record_manual_adjust(int(oid), payload, source_app_id='eposone')
    except (StockValidationError, OrderValidationError) as exc:
        flash(str(exc).replace('_', ' '), 'danger')
        return redirect(url_for('eposone.eposone_section', slug='inventory', tab=tab))
    flash('Ajuste de stock registrado.', 'success')
    return redirect(url_for('eposone.eposone_section', slug='inventory', tab=tab))


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
    profile = (request.form.get('client_profile') or 'pos').strip().lower()
    contact_type = (request.form.get('contact_type') or 'person').strip()
    identification_type = (request.form.get('identification_type') or 'cedula').strip()
    # UX: Cliente POS nunca usa consumer_final (eso es el registro del sistema).
    if profile == 'pos':
        contact_type = 'person'
        identification_type = 'cedula'
    payload = {
        'contact_type': contact_type,
        'display_name': (request.form.get('display_name') or '').strip(),
        'first_name': (request.form.get('first_name') or '').strip(),
        'last_name': (request.form.get('last_name') or '').strip(),
        'company_name': (request.form.get('company_name') or '').strip(),
        'commercial_name': (request.form.get('commercial_name') or '').strip(),
        'email': (request.form.get('email') or '').strip(),
        'phone': (request.form.get('phone') or '').strip(),
        'mobile': (request.form.get('mobile') or '').strip(),
        'tax_id': (request.form.get('tax_id') or '').strip(),
        'dv': (request.form.get('dv') or '').strip(),
        'identification_type': identification_type,
        'province': (request.form.get('province') or '').strip(),
        'district': (request.form.get('district') or '').strip(),
        'township': (request.form.get('township') or '').strip(),
        'fiscal_address': (request.form.get('fiscal_address') or '').strip(),
        'country': (request.form.get('country') or 'PA').strip() or 'PA',
        'is_customer': request.form.get('is_customer') == '1',
        'active': True,
    }
    # Empresa: company_name obligatorio en el maestro — reutilizar display_name si falta.
    if payload['contact_type'] == 'company' and not payload['company_name']:
        payload['company_name'] = payload['display_name']
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
    """POS ligero BO → Order Domain (sin contrato tablet nuevo)."""
    denied = _require_eposone_admin()
    if denied is not None:
        return denied
    import json
    import uuid

    from models.commercial_core import CorePosTerminal
    from nodeone.core.platform.runtime import resolve_organization_id
    from nodeone.core.services.product import ProductService
    from nodeone.modules.eposone.bo_actor import ensure_backoffice_terminal
    from nodeone.modules.eposone.order_domain import OrderDomainError, OrderDomainService

    oid = resolve_organization_id()
    if oid is None:
        abort(400)

    products = ProductService.search(int(oid), status='active', limit=500)
    categories = sorted({(p.category or '').strip() for p in products if (p.category or '').strip()})
    catalog = [
        {
            'product_ref': p.product_ref,
            'name': p.name,
            'category': p.category or '',
            'fiscal_category': p.fiscal_category or 'ITBMS_7',
            'tax_percent': (
                10.0
                if (p.fiscal_category or '') == 'ITBMS_10'
                else 15.0
                if (p.fiscal_category or '') == 'ITBMS_15'
                else 0.0
                if (p.fiscal_category or '') == 'EXENTO'
                else 7.0
            ),
            'unit_price': float(p.unit_price or 0),
            'image_url': p.image_url,
        }
        for p in products
    ]

    def _render(**extra):
        return render_template(
            'eposone/order_new.html',
            catalog=catalog,
            categories=categories,
            **extra,
        )

    if request.method == 'GET':
        return _render()

    try:
        device = ensure_backoffice_terminal(int(oid))
    except Exception:
        device = None
    if device is None:
        flash('No hay terminal POS activo. Provisioná una caja/tablet primero.', 'warning')
        return redirect(url_for('eposone.eposone_section', slug='terminals'))

    service_mode = (request.form.get('service_mode') or 'mesa').strip().lower()
    table_raw = (request.form.get('table_ref') or '').strip()
    guest_name = (request.form.get('guest_name') or '').strip()
    notes = (request.form.get('notes') or '').strip() or None
    lines_raw = (request.form.get('lines_json') or '[]').strip()
    try:
        lines = json.loads(lines_raw)
        if not isinstance(lines, list):
            raise ValueError('lines')
    except (TypeError, ValueError, json.JSONDecodeError):
        flash('Ticket inválido. Agregá al menos un producto.', 'danger')
        return _render()

    clean_lines: list[dict] = []
    for row in lines:
        if not isinstance(row, dict):
            continue
        pref = str(row.get('product_ref') or '').strip()
        if not pref:
            continue
        try:
            qty = float(row.get('qty') or 1)
            price = float(row.get('unit_price') or 0)
        except (TypeError, ValueError):
            continue
        if qty <= 0:
            continue
        line_payload = {
            'product_ref': pref,
            'qty': qty,
            'unit_price': price,
            'notes': (str(row.get('notes') or '').strip() or None),
        }
        if 'tax' in row:
            try:
                line_payload['tax'] = float(row.get('tax') or 0)
            except (TypeError, ValueError):
                pass
        clean_lines.append(line_payload)
    if not clean_lines:
        flash('Agregá al menos un producto al ticket.', 'danger')
        return _render()

    table_ref = None
    local_number = None
    customer_ref = None
    if service_mode == 'mesa':
        if not table_raw:
            flash('Indicá el número/nombre de mesa.', 'danger')
            return _render()
        table_ref = table_raw if table_raw.lower().startswith('mesa') else f'mesa-{table_raw}'
        local_number = guest_name or None
    elif service_mode == 'llevar':
        # table_ref único: evita reutilizar un único pedido "llevar" abierto
        table_ref = f"llevar-{uuid.uuid4().hex[:8]}"
        local_number = guest_name or 'Llevar'
        customer_ref = guest_name or None
    else:  # delivery
        table_ref = f"delivery-{uuid.uuid4().hex[:8]}"
        local_number = guest_name or 'Delivery'
        customer_ref = guest_name or None

    try:
        order = OrderDomainService.create_order(
            device,
            {
                'table_ref': table_ref,
                'local_number': local_number,
                'customer_ref': customer_ref,
                'notes': notes,
                'user_ref': getattr(current_user, 'email', None)
                or getattr(current_user, 'username', None)
                or str(getattr(current_user, 'id', '')),
                'event_id': str(uuid.uuid4()),
            },
        )
        for line in clean_lines:
            OrderDomainService.apply_event(
                device,
                int(order.id),
                {
                    'type': 'producto.agregado',
                    'event_id': str(uuid.uuid4()),
                    'payload': line,
                },
            )
    except OrderDomainError as exc:
        flash(f'No se pudo crear el pedido: {exc.code}', 'danger')
        return _render()

    flash(f'Pedido {order.en1_number} creado.', 'success')
    return redirect(url_for('eposone.eposone_order_domain_detail', order_id=int(order.id)))


@eposone_bp.route('/section/<slug>')
@login_required
def eposone_section(slug: str):
    denied = _require_eposone_admin()
    if denied is not None:
        return denied
    key = (slug or '').strip().lower()
    # Legacy: Centro de Configuración eliminado — opciones viven en cada módulo.
    if key == 'settings':
        return redirect(url_for('eposone.eposone_home'))
    if key not in EPOSONE_SECTION_SLUGS:
        abort(404)
    title, description = EPOSONE_SECTIONS[key]
    if key == 'orders':
        from sqlalchemy import or_

        from models.eposone_order import EposoneOrder
        from nodeone.core.platform.runtime import resolve_organization_id

        oid = resolve_organization_id()
        orders: list = []
        orders_total = 0
        q_text = (request.args.get('q') or '').strip()
        status_filter = (request.args.get('status') or '').strip() or None
        payment_filter = (request.args.get('payment_status') or '').strip() or None
        table_filter = (request.args.get('table') or '').strip() or None
        register_filter = (request.args.get('register') or '').strip() or None
        pos_filter = (request.args.get('pos') or '').strip() or None
        cashier_filter = (request.args.get('cashier') or '').strip() or None
        customer_filter = (request.args.get('customer') or '').strip() or None
        # Presencia en query: vacío explícito (Aplicar sin fechas) ≠ primera visita.
        has_date_from = 'from' in request.args
        has_date_to = 'to' in request.args
        date_from = (request.args.get('from') or '').strip() or None
        date_to = (request.args.get('to') or '').strip() or None
        per_page, persist_pp = _resolve_orders_per_page(current_user)
        if persist_pp:
            _persist_orders_per_page(current_user, per_page)
        try:
            page = max(1, int((request.args.get('page') or '1').strip()))
        except (TypeError, ValueError):
            page = 1
        pages_total = 1
        today_local = ''
        if oid is not None:
            from datetime import datetime as _dt

            from models.saas import SaasOrganization
            from nodeone.core.timezone_service import TimeZoneService

            org = SaasOrganization.query.filter_by(id=int(oid)).first()
            zone = TimeZoneService.effective_timezone(
                user=current_user if getattr(current_user, 'is_authenticated', False) else None,
                organization=org,
            )
            today_local = _dt.now(zone).strftime('%Y-%m-%d')
            # Entrada a Pedidos sin from/to → hoy (zona efectiva).
            if not has_date_from and not has_date_to:
                date_from = today_local
                date_to = today_local

            q = EposoneOrder.query.filter_by(organization_id=int(oid))
            if status_filter:
                q = q.filter_by(status=status_filter)
            if payment_filter:
                q = q.filter_by(payment_status=payment_filter)
            if table_filter:
                q = q.filter(EposoneOrder.table_ref.ilike(f'%{table_filter}%'))
            if register_filter:
                q = q.filter(EposoneOrder.register_ref.ilike(f'%{register_filter}%'))
            if pos_filter:
                q = q.filter(EposoneOrder.pos_ref.ilike(f'%{pos_filter}%'))
            if cashier_filter:
                q = q.filter(EposoneOrder.user_ref.ilike(f'%{cashier_filter}%'))
            if customer_filter:
                q = q.filter(EposoneOrder.customer_ref.ilike(f'%{customer_filter}%'))
            if q_text:
                like = f'%{q_text}%'
                q = q.filter(
                    or_(
                        EposoneOrder.en1_number.ilike(like),
                        EposoneOrder.local_number.ilike(like),
                        EposoneOrder.customer_ref.ilike(like),
                        EposoneOrder.table_ref.ilike(like),
                        EposoneOrder.user_ref.ilike(like),
                    )
                )
            if date_from or date_to:
                if date_from:
                    try:
                        start, _ = TimeZoneService.day_bounds_utc_naive(date_from[:10], zone)
                        q = q.filter(EposoneOrder.opened_at >= start)
                    except ValueError:
                        pass
                if date_to:
                    try:
                        _, end = TimeZoneService.day_bounds_utc_naive(date_to[:10], zone)
                        q = q.filter(EposoneOrder.opened_at < end)
                    except ValueError:
                        pass
            orders_total = int(q.count())
            pages_total = max(1, (orders_total + per_page - 1) // per_page)
            if page > pages_total:
                page = pages_total
            offset = (page - 1) * per_page
            orders = (
                q.order_by(EposoneOrder.opened_at.desc(), EposoneOrder.id.desc())
                .offset(offset)
                .limit(per_page)
                .all()
            )
            showing_from = (offset + 1) if orders_total else 0
            showing_to = offset + len(orders)

            from models.commercial_core import CorePosTerminal
            from nodeone.modules.eposone.bo_actor import order_origin_meta

            owner_refs = {
                str(o.owner_device_uuid).strip()
                for o in orders
                if (o.owner_device_uuid or '').strip()
            }
            terminals_by_ref: dict = {}
            if owner_refs:
                trows = (
                    CorePosTerminal.query.filter_by(organization_id=int(oid))
                    .filter(CorePosTerminal.terminal_ref.in_(sorted(owner_refs)))
                    .all()
                )
                terminals_by_ref = {str(t.terminal_ref): t for t in trows}
            order_origins = {}
            for o in orders:
                t = terminals_by_ref.get(str(o.owner_device_uuid or '').strip())
                order_origins[int(o.id)] = order_origin_meta(
                    owner_device_uuid=o.owner_device_uuid,
                    device_label=getattr(t, 'device_label', None) if t else None,
                    profile=getattr(t, 'profile', None) if t else None,
                )
        else:
            showing_from = 0
            showing_to = 0
            order_origins = {}
        # Query string para Ver/detalle: filtros + paginación actual (incluye hoy por defecto)
        from urllib.parse import urlencode

        detail_params = _orders_list_filter_args()
        if date_from:
            detail_params['from'] = str(date_from)
        if date_to:
            detail_params['to'] = str(date_to)
        detail_params['per_page'] = str(per_page)
        detail_params['page'] = str(page)
        orders_detail_qs = urlencode(detail_params)
        pager_params = {k: v for k, v in detail_params.items() if k != 'page'}
        orders_pager_qs = urlencode(pager_params)
        settings = None
        fe_module_enabled = False
        if oid is not None:
            from nodeone.modules.eposone.settings_service import EposoneSettingsService
            from nodeone.services.org_scope import has_saas_module_enabled

            settings = EposoneSettingsService.get_settings(int(oid))
            fe_module_enabled = bool(has_saas_module_enabled(int(oid), 'efactura'))
        return render_template(
            'eposone/orders_domain.html',
            section_slug=key,
            section_title=title,
            section_description=description,
            orders=orders,
            order_origins=order_origins,
            orders_total=orders_total,
            q=q_text,
            status_filter=status_filter or '',
            payment_filter=payment_filter or '',
            table_filter=table_filter or '',
            register_filter=register_filter or '',
            pos_filter=pos_filter or '',
            cashier_filter=cashier_filter or '',
            customer_filter=customer_filter or '',
            date_from=date_from or '',
            date_to=date_to or '',
            today_local=today_local,
            orders_refresh_seconds=15,
            orders_detail_qs=orders_detail_qs,
            orders_pager_qs=orders_pager_qs,
            page=page,
            per_page=per_page,
            pages_total=pages_total,
            per_page_choices=_ORDERS_PER_PAGE_CHOICES,
            showing_from=showing_from,
            showing_to=showing_to,
            settings=settings,
            fe_module_enabled=fe_module_enabled,
        )
    if key == 'contacts':
        from nodeone.core.platform.runtime import resolve_organization_id
        from nodeone.core.services.contacts import ContactService

        oid = resolve_organization_id()
        contacts: list = []
        contacts_total = 0
        q = (request.args.get('q') or '').strip()
        if oid is not None:
            contacts, contacts_total = ContactService.search(int(oid), q=q, limit=200)
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
            # Catálogo BO: más filas para filtros client-side (UX); no cambia API/dominio.
            products = ProductService.search(int(oid), limit=500)
            for p in products:
                can_delete_by_ref[p.product_ref] = not ProductService.has_operational_usage(
                    int(oid), p.product_ref
                )
                if p.category and p.category not in categories:
                    categories.append(p.category)
            categories.sort()
            try:
                from nodeone.modules.eposone.fiscal_categories import ensure_panama_fiscal_seed

                ensure_panama_fiscal_seed(int(oid))
            except Exception:
                pass
        from nodeone.modules.eposone.fiscal_categories import FISCAL_CATEGORIES_PA

        return render_template(
            'eposone/products.html',
            section_slug=key,
            section_title=title,
            section_description=description,
            products=products,
            products_total=len(products),
            can_delete_by_ref=can_delete_by_ref,
            categories=categories,
            fiscal_categories=FISCAL_CATEGORIES_PA,
        )
    if key == 'kds':
        from nodeone.core.platform.runtime import resolve_organization_id
        from nodeone.modules.eposone.settings_service import EposoneSettingsService

        oid = resolve_organization_id()
        ctx = {'ticket_rows': [], 'tickets_total': 0}
        settings = None
        if oid is not None:
            ctx = _kds_page_context(int(oid))
            settings = EposoneSettingsService.get_settings(int(oid))
        return render_template(
            'eposone/kds.html',
            section_slug=key,
            section_title=title,
            section_description=description,
            settings=settings,
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
    if key == 'organization':
        from models.saas import SaasOrganization
        from nodeone.core.platform.runtime import resolve_organization_id
        from nodeone.modules.eposone.settings_service import (
            ALLOWED_CURRENCIES,
            EposoneSettingsService,
        )

        oid = resolve_organization_id()
        org = SaasOrganization.query.get(int(oid)) if oid is not None else None
        if org is None:
            abort(404)
        settings = EposoneSettingsService.get_settings(int(oid))
        timezones = (
            'America/Panama',
            'America/Bogota',
            'America/Costa_Rica',
            'America/Mexico_City',
            'America/New_York',
            'UTC',
        )
        return render_template(
            'eposone/organization.html',
            section_slug=key,
            section_title=title,
            section_description=description,
            org=org,
            settings=settings,
            timezones=timezones,
            currencies=sorted(ALLOWED_CURRENCIES),
        )
    if key == 'branches':
        from nodeone.core.master.constants import (
            ORG_UNIT_TYPE_BRANCH,
            ORG_UNIT_TYPE_POS,
            ORG_UNIT_TYPE_REGISTER,
        )
        from nodeone.core.platform.runtime import resolve_organization_id
        from nodeone.core.services.org_unit import OrgUnitService

        oid = resolve_organization_id()
        branch_rows: list = []
        if oid is not None:
            branches = OrgUnitService.list_units(int(oid), unit_type=ORG_UNIT_TYPE_BRANCH)
            pos_units = OrgUnitService.list_units(int(oid), unit_type=ORG_UNIT_TYPE_POS)
            registers = OrgUnitService.list_units(int(oid), unit_type=ORG_UNIT_TYPE_REGISTER)
            pos_by_branch: dict[int, list] = {}
            for pos in pos_units:
                pid = getattr(pos, 'parent_id', None)
                if pid is not None:
                    pos_by_branch.setdefault(int(pid), []).append(pos)
            reg_by_pos: dict[int, int] = {}
            for reg in registers:
                pp = getattr(reg, 'parent_id', None)
                if pp is not None:
                    reg_by_pos[int(pp)] = reg_by_pos.get(int(pp), 0) + 1
            for branch in branches:
                pos_list = pos_by_branch.get(int(branch.id), [])
                pos_n = len(pos_list)
                reg_n = sum(reg_by_pos.get(int(p.id), 0) for p in pos_list)
                branch_rows.append(
                    {
                        'branch': branch,
                        'pos_count': pos_n,
                        'register_count': reg_n,
                    }
                )
        return render_template(
            'eposone/branches.html',
            section_slug=key,
            section_title=title,
            section_description=description,
            branch_rows=branch_rows,
            branches_total=len(branch_rows),
        )
    if key == 'pos-points':
        from nodeone.core.commerce.pos import PosTerminalService
        from nodeone.core.master.constants import (
            ORG_UNIT_TYPE_BRANCH,
            ORG_UNIT_TYPE_POS,
            ORG_UNIT_TYPE_REGISTER,
        )
        from nodeone.core.platform.runtime import resolve_organization_id
        from nodeone.core.services.org_unit import OrgUnitService
        from nodeone.modules.eposone.register_license_service import RegisterLicenseService

        oid = resolve_organization_id()
        pos_units: list = []
        branches: list = []
        registers: list = []
        devices: list = []
        if oid is not None:
            pos_units = OrgUnitService.list_units(int(oid), unit_type=ORG_UNIT_TYPE_POS)
            branches = OrgUnitService.list_units(int(oid), unit_type=ORG_UNIT_TYPE_BRANCH)
            registers = OrgUnitService.list_units(int(oid), unit_type=ORG_UNIT_TYPE_REGISTER)
            devices = PosTerminalService.list_terminals(int(oid), limit=500)

        branch_by_id = {int(b.id): b for b in branches}
        registers_by_pos: dict[int, list] = {}
        for reg in registers:
            pid = getattr(reg, 'parent_id', None)
            if pid is not None:
                registers_by_pos.setdefault(int(pid), []).append(reg)

        device_by_register: dict[str, object] = {}
        for d in devices:
            ref = (getattr(d, 'register_ref', None) or '').strip()
            if ref and ref not in device_by_register:
                device_by_register[ref] = d

        pos_rows: list[dict] = []
        for item in pos_units:
            regs = registers_by_pos.get(int(item.id), [])
            with_dev = sum(1 for r in regs if str(r.unit_ref) in device_by_register)
            branch = branch_by_id.get(int(item.parent_id)) if item.parent_id is not None else None
            pos_rows.append(
                {
                    'pos': item,
                    'branch_name': branch.name if branch is not None else None,
                    'register_count': len(regs),
                    'registers_with_device': with_dev,
                }
            )

        pos_ref = (request.args.get('pos') or '').strip()
        active_pos = None
        active_branch_name = None
        active_register_rows: list[dict] = []
        if pos_ref:
            active_pos = next((p for p in pos_units if str(p.unit_ref) == pos_ref), None)
            if active_pos is None:
                return redirect(url_for('eposone.eposone_section', slug='pos-points'))
            branch = (
                branch_by_id.get(int(active_pos.parent_id))
                if active_pos.parent_id is not None
                else None
            )
            active_branch_name = branch.name if branch is not None else None
            for reg in registers_by_pos.get(int(active_pos.id), []):
                lic = None
                if oid is not None:
                    lic = RegisterLicenseService.snapshot(int(oid), str(reg.unit_ref))
                active_register_rows.append(
                    {
                        'register': reg,
                        'device': device_by_register.get(str(reg.unit_ref)),
                        'license': lic,
                    }
                )

        return render_template(
            'eposone/pos_points.html',
            section_slug=key,
            section_title=title,
            section_description=description,
            branches=branches,
            pos_rows=pos_rows,
            active_pos=active_pos,
            active_branch_name=active_branch_name,
            active_register_rows=active_register_rows,
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
        categories: list[str] = []
        warehouse_name_by_id: dict[int, str] = {}
        branch_name_by_id: dict[int, str] = {}
        product_meta_by_ref: dict[str, dict] = {}
        if oid is not None:
            warehouses = OrgUnitService.list_units(int(oid), unit_type=ORG_UNIT_TYPE_WAREHOUSE)
            # UX: más filas para filtros client-side; no cambia API/dominio.
            stock_balances = StockService.list_balances(int(oid), limit=500)
            stock_movements = StockService.list_movements(int(oid), limit=200)
            branches = OrgUnitService.list_units(int(oid), unit_type=ORG_UNIT_TYPE_BRANCH)
            products = ProductService.search(int(oid), status='active', limit=500)
            warehouse_name_by_id = {
                int(w.id): f'{w.name} ({w.unit_ref})' for w in warehouses
            }
            branch_name_by_id = {
                int(b.id): f'{b.name} ({b.unit_ref})' for b in branches
            }
            for p in products:
                product_meta_by_ref[p.product_ref] = {
                    'name': p.name,
                    'uom': p.uom or 'und',
                    'min_stock': p.min_stock,
                    'max_stock': p.max_stock,
                    'category': (p.category or '').strip(),
                    'unit_price': float(p.unit_price or 0),
                }
                cat = (p.category or '').strip()
                if cat and cat not in categories:
                    categories.append(cat)
            categories.sort()
            # Completar meta de productos con saldo pero fuera del search activo.
            for bal in stock_balances:
                if bal.product_ref in product_meta_by_ref:
                    continue
                dto = ProductService.get_by_ref(int(oid), bal.product_ref)
                if dto is None:
                    continue
                product_meta_by_ref[dto.product_ref] = {
                    'name': dto.name,
                    'uom': dto.uom or 'und',
                    'min_stock': dto.min_stock,
                    'max_stock': dto.max_stock,
                    'category': (dto.category or '').strip(),
                    'unit_price': float(dto.unit_price or 0),
                }
        return render_template(
            'eposone/inventory.html',
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
            branch_name_by_id=branch_name_by_id,
            product_meta_by_ref=product_meta_by_ref,
            branches=branches,
            products=products,
            categories=categories,
        )
    if key == 'registers':
        from nodeone.core.master.constants import ORG_UNIT_TYPE_POS
        from nodeone.core.platform.runtime import resolve_organization_id
        from nodeone.core.services.org_unit import OrgUnitService

        oid = resolve_organization_id()
        ctx = {
            'register_rows': [],
            'registers_total': 0,
            'open_shifts_total': 0,
            'recent_closed': [],
            'cashier_contacts': [],
        }
        pos_units: list = []
        settings = None
        if oid is not None:
            from nodeone.modules.eposone.settings_service import EposoneSettingsService

            ctx = _registers_page_context(int(oid))
            pos_units = OrgUnitService.list_units(int(oid), unit_type=ORG_UNIT_TYPE_POS)
            settings = EposoneSettingsService.get_settings(int(oid))
        issued_register_ref = (request.args.get('issued') or '').strip() or None
        return render_template(
            'eposone/registers.html',
            section_slug=key,
            section_title=title,
            section_description=description,
            pos_units=pos_units,
            settings=settings,
            issued_register_ref=issued_register_ref,
            en1_api_base_url=request.url_root.rstrip('/'),
            **ctx,
        )
    if key == 'cashiers':
        from nodeone.core.platform.runtime import resolve_organization_id

        oid = resolve_organization_id()
        cashiers: list = []
        if oid is not None:
            cashiers = _cashier_contacts_for_org(int(oid), active_only=None)
        return render_template(
            'eposone/cashiers.html',
            section_slug=key,
            section_title=title,
            section_description=description,
            cashiers=cashiers,
            cashiers_total=len(cashiers),
            active_cashiers_total=sum(1 for row in cashiers if row.active),
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
        from nodeone.core.platform.runtime import resolve_organization_id

        oid = resolve_organization_id()
        devices: list = []
        if oid is not None:
            devices = PosTerminalService.list_terminals(int(oid), limit=500)

        from nodeone.modules.eposone.bo_actor import is_ops_device

        show_all = (request.args.get('all') or '').strip() == '1'
        ops_devices = [d for d in devices if is_ops_device(d)]
        hidden_n = len(devices) - len(ops_devices)
        view_devices = devices if show_all else ops_devices

        return render_template(
            'eposone/terminals.html',
            section_slug=key,
            section_title=title,
            section_description=description,
            devices=view_devices,
            devices_total=len(view_devices),
            devices_all_total=len(devices),
            hidden_test_devices=hidden_n,
            show_all_devices=show_all,
        )
    if key == 'licenses':
        from nodeone.core.master.constants import ORG_UNIT_TYPE_POS, ORG_UNIT_TYPE_REGISTER
        from nodeone.core.platform.runtime import resolve_organization_id
        from nodeone.core.services.org_unit import OrgUnitService
        from nodeone.modules.eposone.register_license_service import RegisterLicenseService

        oid = resolve_organization_id()
        license_rows: list = []
        if oid is not None:
            registers = OrgUnitService.list_units(int(oid), unit_type=ORG_UNIT_TYPE_REGISTER)
            pos_units = OrgUnitService.list_units(int(oid), unit_type=ORG_UNIT_TYPE_POS)
            pos_by_id = {int(p.id): p for p in pos_units}
            for reg in registers:
                snap = RegisterLicenseService.snapshot(int(oid), str(reg.unit_ref))
                pos = pos_by_id.get(int(reg.parent_id)) if reg.parent_id is not None else None
                license_rows.append(
                    {
                        'register': reg,
                        'pos_name': pos.name if pos is not None else None,
                        'license': snap,
                    }
                )
        return render_template(
            'eposone/licenses.html',
            section_slug=key,
            section_title=title,
            section_description=description,
            license_rows=license_rows,
            licenses_total=len(license_rows),
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
