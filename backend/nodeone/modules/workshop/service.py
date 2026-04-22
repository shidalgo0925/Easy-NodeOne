"""Lógica de negocio: estados, totales, cotización desde orden de taller."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Optional

from nodeone.core.db import db
from models.users import User
from nodeone.modules.accounting.models import Tax
from nodeone.modules.sales.models import Quotation, QuotationLine
from nodeone.modules.workshop.models import (
    VehicleInspectionPoint,
    WorkshopInspection,
    WorkshopLine,
    WorkshopOrder,
    WorkshopVehicle,
)
from nodeone.services.tax_calculation import compute_line_amounts
from nodeone.services.user_organization import user_in_org_clause


def _recompute_quotation_totals(quotation: Quotation) -> None:
    qlines = QuotationLine.query.filter_by(quotation_id=quotation.id).all()
    subtotal = 0.0
    tax_total = 0.0
    grand = 0.0
    for ln in qlines:
        qty = float(ln.quantity or 0)
        pu = float(ln.price_unit or 0)
        tax = (
            Tax.query.filter_by(id=ln.tax_id, organization_id=quotation.organization_id).first()
            if ln.tax_id
            else None
        )
        s, t, tx = compute_line_amounts(qty, pu, tax)
        ln.subtotal = s
        ln.total = t
        subtotal += s
        tax_total += tx
        grand += t
    quotation.total = round(subtotal, 2)
    quotation.tax_total = round(tax_total, 2)
    quotation.grand_total = round(grand, 2)


ORDER_STATUSES = (
    'draft',
    'inspected',
    'quoted',
    'approved',
    'in_progress',
    'qc',
    'done',
    'delivered',
    'cancelled',
)

# origen -> destinos permitidos
_TRANSITIONS: dict[str, tuple[str, ...]] = {
    'draft': ('inspected', 'cancelled'),
    'inspected': ('quoted', 'draft', 'cancelled'),
    'quoted': ('approved', 'inspected', 'cancelled'),
    'approved': ('in_progress', 'quoted', 'cancelled'),
    'in_progress': ('qc', 'approved', 'cancelled'),
    'qc': ('done', 'in_progress', 'cancelled'),
    'done': ('delivered', 'qc', 'cancelled'),
    'delivered': (),
    'cancelled': ('draft',),
}


_WO_CODE_RE = re.compile(r'^WO-(\d+)$', re.IGNORECASE)
_Q_NUM_RE = re.compile(r'^Q-(\d+)$', re.IGNORECASE)


def next_workshop_code(org_id: int) -> str:
    rows = db.session.query(WorkshopOrder.code).filter_by(organization_id=org_id).all()
    mx = 0
    for (code,) in rows:
        m = _WO_CODE_RE.match((code or '').strip())
        if m:
            mx = max(mx, int(m.group(1)))
    return f'WO-{mx + 1:04d}'


def next_quotation_number(org_id: int) -> str:
    rows = db.session.query(Quotation.number).filter_by(organization_id=org_id).all()
    mx = 0
    for (num,) in rows:
        m = _Q_NUM_RE.match((num or '').strip())
        if m:
            mx = max(mx, int(m.group(1)))
    return f'Q-{mx + 1:04d}'


def _tax_for_line(tax_id: Optional[int], org_id: int) -> Optional[Tax]:
    if not tax_id:
        return None
    return Tax.query.filter_by(id=int(tax_id), organization_id=org_id).first()


def recompute_workshop_order_totals(order: WorkshopOrder) -> None:
    lines = WorkshopLine.query.filter_by(order_id=order.id).all()
    sub = 0.0
    tax_sum = 0.0
    grand = 0.0
    for ln in lines:
        t = _tax_for_line(ln.tax_id, order.organization_id)
        s, tot, tx = compute_line_amounts(float(ln.quantity or 0), float(ln.price_unit or 0), t)
        ln.subtotal = s
        ln.tax_amount = tx
        ln.total = tot
        sub += s
        tax_sum += tx
        grand += tot
    order.total_estimated = grand
    order.total_final = grand


def allowed_next_statuses(order: WorkshopOrder) -> list[str]:
    """Destinos de estado permitidos desde el estado actual (respeta cotización obligatoria, etc.)."""
    cur = (order.status or 'draft').strip()
    out: list[str] = []
    for ns in _TRANSITIONS.get(cur, ()):
        ok, _ = can_transition(order, ns)
        if ok:
            out.append(ns)
    return out


def can_transition(order: WorkshopOrder, new_status: str) -> tuple[bool, str]:
    cur = (order.status or 'draft').strip()
    if new_status not in ORDER_STATUSES:
        return False, 'invalid_status'
    if new_status == cur:
        return True, ''
    allowed = _TRANSITIONS.get(cur, ())
    if new_status not in allowed:
        return False, f'transition_not_allowed:{cur}->{new_status}'
    if new_status == 'quoted' and not order.quotation_id:
        return False, 'quotation_required'
    if new_status == 'approved' and not order.quotation_id:
        return False, 'quotation_required'
    if new_status == 'delivered' and cur != 'done':
        return False, 'deliver_requires_done'
    return True, ''


def apply_transition(order: WorkshopOrder, new_status: str) -> Optional[str]:
    ns = (new_status or '').strip()
    old = (order.status or 'draft').strip()
    if old == ns:
        return None
    ok, err = can_transition(order, new_status)
    if not ok:
        return err
    order.status = ns
    try:
        from nodeone.modules.workshop import sla_service

        sla_service.on_status_changed(order, old, ns)
    except Exception:
        pass
    return None


def get_or_create_inspection(order: WorkshopOrder, user_id: Optional[int]) -> WorkshopInspection:
    row = WorkshopInspection.query.filter_by(order_id=order.id).first()
    if row:
        return row
    row = WorkshopInspection(order_id=order.id, created_by=user_id)
    db.session.add(row)
    db.session.flush()
    return row


def create_quotation_from_workshop_order(order: WorkshopOrder, user_id: Optional[int]) -> Quotation:
    """Crea cotización en borrador con líneas del taller; asocia order.quotation_id."""
    if order.quotation_id:
        existing = Quotation.query.filter_by(id=order.quotation_id, organization_id=order.organization_id).first()
        if existing:
            return existing

    lines = WorkshopLine.query.filter_by(order_id=order.id).order_by(WorkshopLine.id.asc()).all()
    if not lines:
        raise ValueError('no_lines')

    sp_uid = None
    if user_id:
        u = (
            User.query.filter(
                user_in_org_clause(User, order.organization_id),
                User.id == int(user_id),
                User.is_salesperson == True,  # noqa: E712
                User.is_active == True,  # noqa: E712
            )
            .first()
        )
        if u:
            sp_uid = u.id

    q = Quotation(
        organization_id=order.organization_id,
        number=next_quotation_number(order.organization_id),
        customer_id=order.customer_id,
        salesperson_user_id=sp_uid,
        date=datetime.utcnow(),
        status='draft',
        created_by=user_id,
    )
    db.session.add(q)
    db.session.flush()

    for wl in lines:
        ln = QuotationLine(
            quotation_id=q.id,
            product_id=wl.product_id,
            description=wl.description,
            quantity=float(wl.quantity or 0),
            price_unit=float(wl.price_unit or 0),
            tax_id=wl.tax_id,
            subtotal=0.0,
            total=0.0,
        )
        db.session.add(ln)

    _recompute_quotation_totals(q)
    order.quotation_id = q.id
    if order.status in ('draft', 'inspected'):
        order.status = 'quoted'
    db.session.flush()
    return q


ZONE_SEVERITY_RANK = {'low': 1, 'medium': 2, 'high': 3}


def max_severity_for_zone(inspection_id: int, zone_code: str) -> Optional[str]:
    pts = (
        VehicleInspectionPoint.query.filter_by(inspection_id=inspection_id, zone_code=zone_code)
        .order_by(VehicleInspectionPoint.id.desc())
        .all()
    )
    if not pts:
        return None
    best = 'low'
    for p in pts:
        s = (p.severity or 'low').lower()
        if ZONE_SEVERITY_RANK.get(s, 0) > ZONE_SEVERITY_RANK.get(best, 0):
            best = s
    return best
