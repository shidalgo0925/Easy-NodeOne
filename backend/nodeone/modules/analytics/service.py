"""Agregaciones analíticas por organización (multi-tenant) y rangos de fecha."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import func

from nodeone.core.db import db
from nodeone.modules.accounting.models import Invoice
from nodeone.modules.crm_api.models import CrmActivity, CrmLead, CrmStage
from nodeone.modules.sales.models import Quotation
from nodeone.services.user_organization import user_ids_query_in_organization

from models.appointments import Appointment
from models.benefits import Membership
from models.payments import Payment
from models.users import User, UserOrganization


def _parse_day(s: str | None) -> datetime | None:
    if not s or not str(s).strip():
        return None
    try:
        p = str(s).strip()[:10].split('-')
        if len(p) != 3:
            return None
        y, m, d = int(p[0]), int(p[1]), int(p[2])
        return datetime(y, m, d)
    except (TypeError, ValueError):
        return None


def default_month_range() -> tuple[datetime, datetime]:
    """Inicio del mes actual (00:00) y fin de hoy (fin de día) en UTC naive."""
    now = datetime.utcnow()
    start = datetime(now.year, now.month, 1)
    end = now.replace(hour=23, minute=59, second=59, microsecond=999999)
    return start, end


def resolve_date_range(
    start_raw: str | None,
    end_raw: str | None,
) -> tuple[datetime, datetime]:
    """Rango [start, end] inclusive por día; default = mes en curso."""
    start, end = default_month_range()
    ds = _parse_day(start_raw)
    de = _parse_day(end_raw)
    if ds:
        start = ds
    if de:
        end = de.replace(hour=23, minute=59, second=59, microsecond=999999)
    if start > end:
        start, end = end, start
    return start, end


def _fmt_money(n: float) -> str:
    return f'B/. {float(n or 0):,.2f}'


def _user_ids_in_org(org_id: int):
    return user_ids_query_in_organization(org_id)


def build_executive_snapshot(org_id: int, start: datetime, end: datetime) -> dict[str, Any]:
    """
    KPIs y series para el tablero ejecutivo.
    Todas las consultas filtran por organization_id o usuarios de la org.
    """
    uid_scope = _user_ids_in_org(org_id)

    # —— Cotizaciones ——
    q_base = Quotation.query.filter(
        Quotation.organization_id == org_id,
        Quotation.date >= start,
        Quotation.date <= end,
    )
    q_total = int(q_base.count() or 0)
    q_sum = float(
        db.session.query(func.coalesce(func.sum(Quotation.grand_total), 0.0))
        .filter(
            Quotation.organization_id == org_id,
            Quotation.date >= start,
            Quotation.date <= end,
        )
        .scalar()
        or 0.0
    )
    by_status_rows = (
        db.session.query(Quotation.status, func.count(Quotation.id))
        .filter(
            Quotation.organization_id == org_id,
            Quotation.date >= start,
            Quotation.date <= end,
        )
        .group_by(Quotation.status)
        .all()
    )
    q_by_status = {str(r[0] or ''): int(r[1]) for r in by_status_rows}

    q_confirmed_sum = float(
        db.session.query(func.coalesce(func.sum(Quotation.grand_total), 0.0))
        .filter(
            Quotation.organization_id == org_id,
            Quotation.date >= start,
            Quotation.date <= end,
            Quotation.status.in_(('confirmed', 'invoiced', 'paid')),
        )
        .scalar()
        or 0.0
    )

    # —— Facturas ——
    inv_base = Invoice.query.filter(
        Invoice.organization_id == org_id,
        Invoice.date >= start,
        Invoice.date <= end,
    )
    inv_count = int(inv_base.count() or 0)
    inv_posted_paid = (
        Invoice.query.filter(
            Invoice.organization_id == org_id,
            Invoice.date >= start,
            Invoice.date <= end,
            Invoice.status.in_(('posted', 'paid')),
        )
        .with_entities(func.coalesce(func.sum(Invoice.grand_total), 0.0))
        .scalar()
        or 0.0
    )
    inv_posted_paid = float(inv_posted_paid)
    inv_paid_sum = float(
        db.session.query(func.coalesce(func.sum(Invoice.grand_total), 0.0))
        .filter(
            Invoice.organization_id == org_id,
            Invoice.date >= start,
            Invoice.date <= end,
            Invoice.status == 'paid',
        )
        .scalar()
        or 0.0
    )
    inv_by_status_rows = (
        db.session.query(Invoice.status, func.count(Invoice.id))
        .filter(
            Invoice.organization_id == org_id,
            Invoice.date >= start,
            Invoice.date <= end,
        )
        .group_by(Invoice.status)
        .all()
    )
    inv_by_status = {str(r[0] or ''): int(r[1]) for r in inv_by_status_rows}

    now = datetime.utcnow()
    overdue_q = Invoice.query.filter(
        Invoice.organization_id == org_id,
        Invoice.status == 'posted',
        Invoice.due_date.isnot(None),
        Invoice.due_date < now,
    )
    overdue_count = int(overdue_q.count() or 0)
    overdue_sum = float(
        overdue_q.with_entities(func.coalesce(func.sum(Invoice.grand_total), 0.0)).scalar() or 0.0
    )

    open_ar = float(
        db.session.query(func.coalesce(func.sum(Invoice.grand_total), 0.0))
        .filter(
            Invoice.organization_id == org_id,
            Invoice.status == 'posted',
        )
        .scalar()
        or 0.0
    )
    balance_receivable = max(0.0, open_ar)

    # —— Pagos (tabla Payment: importes en centavos) ——
    pay_scope = Payment.query.filter(Payment.user_id.in_(uid_scope))
    pay_in_period = pay_scope.filter(
        Payment.paid_at.isnot(None),
        Payment.paid_at >= start,
        Payment.paid_at <= end,
        Payment.status == 'succeeded',
    )
    pay_count = int(pay_in_period.count() or 0)
    pay_amount_cents = (
        pay_in_period.with_entities(func.coalesce(func.sum(Payment.amount), 0)).scalar() or 0
    )
    pay_amount = float(pay_amount_cents) / 100.0

    # —— Citas ——
    appt_base = Appointment.query.filter(Appointment.organization_id == org_id)
    appt_created = appt_base.filter(
        Appointment.created_at >= start,
        Appointment.created_at <= end,
    )
    appt_scheduled = int(appt_created.count() or 0)
    appt_done = int(
        appt_created.filter(
            func.lower(func.coalesce(Appointment.status, '')).in_(('completed', 'completada', 'done'))
        ).count()
        or 0
    )

    # —— CRM ——
    stages = {s.id: s for s in CrmStage.query.filter_by(organization_id=org_id).all()}
    open_leads = CrmLead.query.filter(
        CrmLead.organization_id == org_id,
        CrmLead.active.is_(True),
        CrmLead.lead_type == 'opportunity',
    ).all()
    open_opportunities = 0
    pipeline_value = 0.0
    for lead in open_leads:
        st = stages.get(lead.stage_id)
        if st and not st.is_won and not st.is_lost:
            open_opportunities += 1
            pipeline_value += float(lead.expected_revenue or 0) * float(lead.probability or 0) / 100.0

    leads_new = int(
        CrmLead.query.filter(
            CrmLead.organization_id == org_id,
            CrmLead.create_date >= start,
            CrmLead.create_date <= end,
        ).count()
        or 0
    )

    pending_crm_act = int(
        CrmActivity.query.filter(
            CrmActivity.organization_id == org_id,
            CrmActivity.status == 'pending',
            CrmActivity.due_date < now,
        ).count()
        or 0
    )

    # —— Miembros / usuarios en org ——
    total_members = int(uid_scope.count() or 0)
    new_users = int(
        uid_scope.filter(User.created_at >= start, User.created_at <= end).count() or 0
    )
    new_links = int(
        UserOrganization.query.filter(
            UserOrganization.organization_id == org_id,
            UserOrganization.created_at >= start,
            UserOrganization.created_at <= end,
        ).count()
        or 0
    )
    active_links = int(
        UserOrganization.query.filter_by(organization_id=org_id, status='active').count() or 0
    )

    new_memberships = int(
        Membership.query.join(User, Membership.user_id == User.id)
        .filter(
            User.id.in_(uid_scope.with_entities(User.id)),
            Membership.created_at >= start,
            Membership.created_at <= end,
        )
        .count()
        or 0
    )

    # Cotizaciones pendientes (borrador + enviada)
    q_pending = int(
        Quotation.query.filter(
            Quotation.organization_id == org_id,
            Quotation.status.in_(('draft', 'sent')),
        ).count()
        or 0
    )

    # Conversión simple: confirmadas / cotizaciones en el período
    q_confirmed_n = int(
        q_base.filter(Quotation.status.in_(('confirmed', 'invoiced', 'paid'))).count() or 0
    )
    conversion_pct = round(100.0 * q_confirmed_n / q_total, 1) if q_total else 0.0

    # Ingreso promedio por cliente (facturación del período / clientes únicos)
    cust_ids_period = (
        db.session.query(func.count(func.distinct(Invoice.customer_id)))
        .filter(
            Invoice.organization_id == org_id,
            Invoice.date >= start,
            Invoice.date <= end,
            Invoice.status.in_(('posted', 'paid')),
        )
        .scalar()
        or 0
    )
    avg_per_customer = (
        float(inv_posted_paid) / float(cust_ids_period) if cust_ids_period else 0.0
    )

    # —— Series: facturación por mes (últimos 12 meses) ——
    series_start = (datetime.utcnow().replace(day=1) - timedelta(days=365)).replace(day=1)
    inv_12m = (
        Invoice.query.filter(
            Invoice.organization_id == org_id,
            Invoice.date >= series_start,
            Invoice.status.in_(('posted', 'paid')),
        )
        .with_entities(Invoice.date, Invoice.grand_total)
        .all()
    )
    month_bucket: dict[str, float] = defaultdict(float)
    for d, gt in inv_12m:
        if not d:
            continue
        key = f'{d.year}-{d.month:02d}'
        month_bucket[key] += float(gt or 0)
    # Ordenar últimas 12 claves
    keys_sorted = sorted(month_bucket.keys())[-12:]
    invoicing_by_month = [{'month': k, 'total': round(month_bucket[k], 2)} for k in keys_sorted]

    # Top clientes por facturación en período
    top_cust_rows = (
        db.session.query(Invoice.customer_id, func.coalesce(func.sum(Invoice.grand_total), 0.0))
        .filter(
            Invoice.organization_id == org_id,
            Invoice.date >= start,
            Invoice.date <= end,
            Invoice.status.in_(('posted', 'paid')),
        )
        .group_by(Invoice.customer_id)
        .order_by(func.sum(Invoice.grand_total).desc())
        .limit(5)
        .all()
    )
    top_clients = []
    for cid, total in top_cust_rows:
        u = User.query.get(cid)
        label = (u.email if u else f'#{cid}') if cid else '—'
        if u and (u.first_name or u.last_name):
            label = f'{(u.first_name or "").strip()} {(u.last_name or "").strip()}'.strip() or label
        top_clients.append({'customer_id': cid, 'label': label, 'total': float(total)})

    # Próximas citas (5)
    upcoming = (
        Appointment.query.filter(
            Appointment.organization_id == org_id,
            Appointment.start_datetime.isnot(None),
            Appointment.start_datetime >= now,
            func.lower(func.coalesce(Appointment.status, '')).notin_(('cancelled', 'rechazada', 'cancelled')),
        )
        .order_by(Appointment.start_datetime.asc())
        .limit(5)
        .all()
    )
    upcoming_list = []
    for a in upcoming:
        upcoming_list.append(
            {
                'id': a.id,
                'start': a.start_datetime.isoformat() if a.start_datetime else None,
                'status': a.status,
            }
        )

    kpis = {
        'sales_month': _fmt_money(q_confirmed_sum),
        'sales_collected': _fmt_money(inv_paid_sum),
        'quotations_count': q_total,
        'quotations_sum': _fmt_money(q_sum),
        'quotations_confirmed_value': _fmt_money(q_confirmed_sum),
        'invoices_issued': inv_count,
        'invoicing_posted': _fmt_money(inv_posted_paid),
        'invoices_paid_sum': _fmt_money(inv_paid_sum),
        'payments_received': _fmt_money(pay_amount),
        'payments_count': pay_count,
        'appointments_scheduled': appt_scheduled,
        'appointments_completed': appt_done,
        'new_members': new_users,
        'new_org_links': new_links,
        'memberships_new': new_memberships,
        'crm_open_opportunities': open_opportunities,
        'crm_pipeline_value': _fmt_money(pipeline_value),
        'crm_leads_new': leads_new,
        'conversion_rate_pct': conversion_pct,
        'crm_overdue_activities': pending_crm_act,
        'avg_revenue_per_customer': _fmt_money(avg_per_customer),
        'balance_receivable': _fmt_money(balance_receivable),
        'quotations_pending': q_pending,
        'invoices_overdue_count': overdue_count,
        'invoices_overdue_sum': _fmt_money(overdue_sum),
        'active_memberships_links': active_links,
        'total_users_org': total_members,
    }

    return {
        'org_id': org_id,
        'period': {'start': start.isoformat(), 'end': end.isoformat()},
        'kpis': kpis,
        'quotations_by_status': q_by_status,
        'invoices_by_status': inv_by_status,
        'charts': {
            'invoicing_by_month': invoicing_by_month,
        },
        'top_clients': top_clients,
        'upcoming_appointments': upcoming_list,
        'legacy_metrics': _legacy_metrics_compat(
            org_id,
            start,
            end,
            uid_scope,
            total_members,
            new_users,
            pay_amount,
            pay_count,
        ),
    }


def _legacy_metrics_compat(
    org_id: int,
    start: datetime,
    end: datetime,
    uid_scope,
    total_users: int,
    new_users: int,
    pay_revenue: float,
    pay_count: int,
) -> dict[str, Any]:
    """Compatibilidad mínima con métricas usadas en plantillas antiguas (opcional)."""
    active_u = int(uid_scope.filter(User.is_active.is_(True)).count() or 0)
    memberships = Membership.query.join(User, Membership.user_id == User.id).filter(
        User.id.in_(uid_scope.with_entities(User.id))
    )
    total_m = int(memberships.count() or 0)
    active_m = int(memberships.filter(Membership.is_active.is_(True)).count() or 0)
    new_m = int(
        memberships.filter(Membership.created_at >= start, Membership.created_at <= end).count() or 0
    )
    by_type_rows = (
        db.session.query(Membership.membership_type, func.count(Membership.id))
        .join(User, Membership.user_id == User.id)
        .filter(User.id.in_(uid_scope.with_entities(User.id)))
        .group_by(Membership.membership_type)
        .all()
    )
    by_type = {str(r[0] or ''): int(r[1]) for r in by_type_rows if r[0]}

    successful = Payment.query.filter(
        Payment.user_id.in_(uid_scope),
        Payment.status == 'succeeded',
        Payment.paid_at >= start,
        Payment.paid_at <= end,
    ).count()

    monthly_trend: list[dict[str, Any]] = []
    for i in range(11, -1, -1):
        dt = datetime.utcnow().replace(day=1) - timedelta(days=30 * i)
        m_start = datetime(dt.year, dt.month, 1)
        if dt.month == 12:
            m_end = datetime(dt.year + 1, 1, 1) - timedelta(microseconds=1)
        else:
            m_end = datetime(dt.year, dt.month + 1, 1) - timedelta(microseconds=1)
        cents = (
            Payment.query.filter(
                Payment.user_id.in_(uid_scope),
                Payment.status == 'succeeded',
                Payment.paid_at.isnot(None),
                Payment.paid_at >= m_start,
                Payment.paid_at <= m_end,
            )
            .with_entities(func.coalesce(func.sum(Payment.amount), 0))
            .scalar()
            or 0
        )
        cnt = (
            Payment.query.filter(
                Payment.user_id.in_(uid_scope),
                Payment.status == 'succeeded',
                Payment.paid_at.isnot(None),
                Payment.paid_at >= m_start,
                Payment.paid_at <= m_end,
            ).count()
            or 0
        )
        monthly_trend.append(
            {
                'month': f'{dt.year}-{dt.month:02d}',
                'total': round(float(cents) / 100.0, 2),
                'count': int(cnt),
            }
        )

    return {
        'users': {
            'total_users': total_users,
            'active_users': active_u,
            'new_users': new_users,
            'users_by_country': {},
        },
        'memberships': {
            'total_memberships': total_m,
            'active_memberships': active_m,
            'expired_memberships': max(0, total_m - active_m),
            'paused_memberships': 0,
            'new_memberships': new_m,
            'by_type': by_type,
        },
        'payments': {
            'total_revenue': round(pay_revenue, 2),
            'total_payments': pay_count,
            'successful_payments': int(successful or 0),
            'by_method': {},
            'monthly_trend': monthly_trend,
        },
        'events': {
            'total_events': 0,
            'total_registrations': 0,
            'by_status': {},
            'popular_events': [],
        },
    }


def build_realtime_24h(org_id: int) -> dict[str, Any]:
    """Métricas rápidas últimas 24 h (usuarios nuevos, membresías, pagos en scope org)."""
    uid_scope = _user_ids_in_org(org_id)
    since = datetime.utcnow() - timedelta(hours=24)
    new_users = int(uid_scope.filter(User.created_at >= since).count() or 0)
    new_m = int(
        Membership.query.join(User, Membership.user_id == User.id)
        .filter(
            User.id.in_(uid_scope.with_entities(User.id)),
            Membership.created_at >= since,
        )
        .count()
        or 0
    )
    new_pay = int(
        Payment.query.filter(
            Payment.user_id.in_(uid_scope),
            Payment.created_at >= since,
        ).count()
        or 0
    )
    cents = (
        Payment.query.filter(
            Payment.user_id.in_(uid_scope),
            Payment.status == 'succeeded',
            Payment.paid_at.isnot(None),
            Payment.paid_at >= since,
        )
        .with_entities(func.coalesce(func.sum(Payment.amount), 0))
        .scalar()
        or 0
    )
    revenue = round(float(cents) / 100.0, 2)
    return {
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        'last_24h': {
            'new_users': new_users,
            'new_memberships': new_m,
            'new_payments': new_pay,
            'revenue_24h': revenue,
        },
    }


def build_sales_board(org_id: int, start: datetime, end: datetime) -> dict[str, Any]:
    """Resumen extendido ventas (mismo rango)."""
    snap = build_executive_snapshot(org_id, start, end)
    q_rows = (
        db.session.query(
            Quotation.salesperson_user_id,
            func.coalesce(func.sum(Quotation.grand_total), 0.0),
            func.count(Quotation.id),
        )
        .filter(
            Quotation.organization_id == org_id,
            Quotation.date >= start,
            Quotation.date <= end,
            Quotation.salesperson_user_id.isnot(None),
        )
        .group_by(Quotation.salesperson_user_id)
        .order_by(func.sum(Quotation.grand_total).desc())
        .limit(10)
        .all()
    )
    by_salesperson = []
    for uid, total, cnt in q_rows:
        u = User.query.get(uid)
        name = u.email if u else f'#{uid}'
        if u and (u.first_name or u.last_name):
            name = f'{(u.first_name or "").strip()} {(u.last_name or "").strip()}'.strip() or name
        by_salesperson.append({'user_id': uid, 'name': name, 'total': float(total), 'count': int(cnt)})

    return {'snapshot': snap, 'by_salesperson': by_salesperson}


def build_crm_board(org_id: int, start: datetime, end: datetime) -> dict[str, Any]:
    """KPIs CRM en el período."""
    won_ids = [s.id for s in CrmStage.query.filter_by(organization_id=org_id, is_won=True).all()]
    lost_ids = [s.id for s in CrmStage.query.filter_by(organization_id=org_id, is_lost=True).all()]

    base = CrmLead.query.filter(
        CrmLead.organization_id == org_id,
        CrmLead.create_date >= start,
        CrmLead.create_date <= end,
    )
    leads_new = int(base.filter(CrmLead.lead_type == 'lead').count() or 0)
    opps = base.filter(CrmLead.lead_type == 'opportunity')
    opps_won = int(opps.filter(CrmLead.stage_id.in_(won_ids)).count() or 0) if won_ids else 0
    opps_lost = int(opps.filter(CrmLead.stage_id.in_(lost_ids)).count() or 0) if lost_ids else 0
    opps_open = int(
        CrmLead.query.filter(
            CrmLead.organization_id == org_id,
            CrmLead.lead_type == 'opportunity',
            CrmLead.active.is_(True),
        ).count()
        or 0
    )

    return {
        'leads_new': leads_new,
        'opportunities_open': opps_open,
        'opportunities_won_period': opps_won,
        'opportunities_lost_period': opps_lost,
        'activities_overdue': int(
            CrmActivity.query.filter(
                CrmActivity.organization_id == org_id,
                CrmActivity.status == 'pending',
                CrmActivity.due_date < datetime.utcnow(),
            ).count()
            or 0
        ),
    }
