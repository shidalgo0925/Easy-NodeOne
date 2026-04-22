"""SLA por proceso: configuración, cálculo, historial y transiciones de etapa."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy import func

from nodeone.core.db import db
from nodeone.modules.workshop.models import (
    WorkshopLine,
    WorkshopOrder,
    WorkshopOrderProcessLog,
    WorkshopProcessStageConfig,
    WorkshopServiceProcessConfig,
)

# Minutos por defecto si no hay fila en BD (alineado a flujo estándar).
_FALLBACK_MINUTES: dict[str, int] = {
    'draft': 10,
    'inspected': 30,
    'quoted': 120,
    'approved': 120,
    'in_progress': 180,
    'qc': 20,
    'done': 15,
    'delivered': 15,
    'cancelled': 0,
}

def _naive_utc(dt: Optional[datetime]) -> Optional[datetime]:
    """Evita TypeError al restar datetimes aware (p. ej. PostgreSQL) vs naive (utcnow)."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt
    return dt.astimezone(timezone.utc).replace(tzinfo=None)


_DEFAULT_STAGE_ROWS: tuple[tuple[str, str, int, int, str], ...] = (
    ('draft', 'Recepción', 1, 10, '#6c757d'),
    ('inspected', 'Diagnóstico', 2, 30, '#0dcaf0'),
    ('quoted', 'Cotización', 3, 120, '#0d6efd'),
    ('approved', 'Aprobación', 4, 120, '#198754'),
    ('in_progress', 'En proceso', 5, 180, '#fd7e14'),
    ('qc', 'Control calidad', 6, 20, '#ffc107'),
    ('done', 'Terminado', 7, 15, '#20c997'),
    ('delivered', 'Entrega', 8, 15, '#212529'),
)


def ensure_default_process_stages(organization_id: int) -> None:
    """Inserta configuración por defecto si la org no tiene filas."""
    n = WorkshopProcessStageConfig.query.filter_by(organization_id=organization_id).count()
    if n > 0:
        return
    for key, name, seq, minutes, color in _DEFAULT_STAGE_ROWS:
        db.session.add(
            WorkshopProcessStageConfig(
                organization_id=organization_id,
                stage_key=key,
                stage_name=name,
                sequence=seq,
                expected_duration_minutes=minutes,
                color=color,
                active=True,
                allow_skip=False,
            )
        )
    db.session.commit()


def _config_row(org_id: int, stage_key: str) -> Optional[WorkshopProcessStageConfig]:
    return (
        WorkshopProcessStageConfig.query.filter_by(
            organization_id=org_id, stage_key=stage_key, active=True
        ).first()
    )


def _primary_service_id(order: WorkshopOrder) -> Optional[int]:
    ln = (
        WorkshopLine.query.filter_by(order_id=order.id)
        .filter(WorkshopLine.product_id.isnot(None))
        .order_by(WorkshopLine.id.asc())
        .first()
    )
    return int(ln.product_id) if ln and ln.product_id else None


def expected_minutes_for_order(order: WorkshopOrder, stage_key: str) -> tuple[int, str]:
    """
    Retorna (minutos, origen) origen = service_override|config|fallback
    """
    org_id = order.organization_id
    sid = _primary_service_id(order)
    if sid:
        ov = (
            WorkshopServiceProcessConfig.query.filter_by(
                organization_id=org_id, service_id=sid, stage_key=stage_key
            ).first()
        )
        if ov:
            return max(1, int(ov.expected_duration_minutes or 1)), 'service_override'
    row = _config_row(org_id, stage_key)
    if row:
        return max(1, int(row.expected_duration_minutes or 1)), 'config'
    return max(1, int(_FALLBACK_MINUTES.get(stage_key, 60))), 'fallback'


def _effective_now(order: WorkshopOrder) -> datetime:
    if order.sla_paused and order.sla_paused_at:
        t = _naive_utc(order.sla_paused_at)
        return t if t is not None else datetime.utcnow()
    return datetime.utcnow()


def _sla_payload_safe_fallback(order: WorkshopOrder) -> dict[str, Any]:
    """Si falla el cálculo (datos raros, migración incompleta), el taller sigue respondiendo JSON."""
    st = (getattr(order, 'status', None) or 'draft').strip()
    return {
        'applicable': False,
        'stage_key': st,
        'stage_name': st,
        'label': 'SLA no disponible',
        'state': 'gray',
        'elapsed_minutes': None,
        'expected_minutes': None,
        'pct': None,
        'bar_pct': 0,
        'paused': bool(getattr(order, 'sla_paused', False)),
        'origin': 'error',
        'color': '#6c757d',
    }


def compute_sla_payload(order: WorkshopOrder) -> dict[str, Any]:
    """Estado visual SLA para API / tarjetas (nunca debe tumbar la petición del taller)."""
    try:
        return _compute_sla_payload_core(order)
    except Exception:
        return _sla_payload_safe_fallback(order)


def _compute_sla_payload_core(order: WorkshopOrder) -> dict[str, Any]:
    st = (order.status or 'draft').strip()
    if st in ('cancelled',):
        return {
            'applicable': False,
            'stage_key': st,
            'label': 'Sin SLA',
            'state': 'gray',
            'elapsed_minutes': None,
            'expected_minutes': None,
            'pct': None,
            'bar_pct': 0,
            'paused': bool(getattr(order, 'sla_paused', False)),
        }

    exp, origin = expected_minutes_for_order(order, st)
    if exp <= 0:
        return {
            'applicable': False,
            'stage_key': st,
            'label': '—',
            'state': 'gray',
            'elapsed_minutes': 0.0,
            'expected_minutes': 0,
            'pct': None,
            'bar_pct': 0,
            'paused': bool(getattr(order, 'sla_paused', False)),
            'origin': origin,
        }

    start = (
        _naive_utc(order.sla_stage_started_at)
        or _naive_utc(order.entry_date)
        or _naive_utc(order.created_at)
        or datetime.utcnow()
    )
    now = _naive_utc(_effective_now(order)) or datetime.utcnow()
    elapsed = max(0.0, (now - start).total_seconds() / 60.0)
    pct = elapsed / float(exp) if exp else 0.0
    if pct <= 0.8:
        state = 'green'
    elif pct <= 1.0:
        state = 'yellow'
    else:
        state = 'red'
    bar_pct = min(100.0, round(pct * 100.0, 1))
    cfg = _config_row(order.organization_id, st)
    stage_name = cfg.stage_name if cfg else st
    return {
        'applicable': True,
        'stage_key': st,
        'stage_name': stage_name,
        'label': _state_label(state, elapsed, exp),
        'state': state,
        'elapsed_minutes': round(elapsed, 1),
        'expected_minutes': exp,
        'pct': round(pct * 100.0, 1),
        'bar_pct': bar_pct,
        'delay_minutes': max(0.0, round(elapsed - exp, 1)) if pct > 1.0 else 0.0,
        'paused': bool(getattr(order, 'sla_paused', False)),
        'origin': origin,
        'color': (cfg.color if cfg else '#6c757d'),
    }


def _state_label(state: str, elapsed: float, expected: int) -> str:
    em = int(round(elapsed))
    if state == 'green':
        return f'{em} min / {expected} min · En tiempo'
    if state == 'yellow':
        return f'{em} min / {expected} min · En riesgo'
    return f'{em} min / {expected} min · Retrasado'


def bootstrap_new_order(order: WorkshopOrder) -> None:
    """Al crear orden: inicia primera etapa y log."""
    ensure_default_process_stages(order.organization_id)
    now = datetime.utcnow()
    exp, _ = expected_minutes_for_order(order, order.status or 'draft')
    order.sla_stage_started_at = now
    order.sla_expected_minutes = exp
    order.sla_paused = False
    order.sla_paused_at = None
    db.session.add(
        WorkshopOrderProcessLog(
            order_id=order.id,
            stage_key=order.status or 'draft',
            started_at=now,
            ended_at=None,
            expected_minutes=float(exp),
        )
    )


def on_status_changed(order: WorkshopOrder, old_status: str, new_status: str) -> None:
    """Cierra log anterior, abre uno nuevo, reinicia reloj SLA."""
    ensure_default_process_stages(order.organization_id)
    now = datetime.utcnow()

    # Cerrar log abierto de old_status
    open_log = (
        WorkshopOrderProcessLog.query.filter_by(order_id=order.id, ended_at=None)
        .order_by(WorkshopOrderProcessLog.id.desc())
        .first()
    )
    if open_log:
        started = _naive_utc(open_log.started_at) or now
        dur = max(0.0, (now - started).total_seconds() / 60.0)
        exp = float(open_log.expected_minutes or 0) or float(
            expected_minutes_for_order(order, open_log.stage_key)[0]
        )
        open_log.ended_at = now
        open_log.duration_minutes = dur
        open_log.is_delayed = dur > exp + 1e-6
        open_log.delay_minutes = max(0.0, dur - exp) if open_log.is_delayed else 0.0

    if new_status in ('cancelled',):
        order.sla_stage_started_at = None
        order.sla_expected_minutes = None
        db.session.flush()
        return

    exp_new, _ = expected_minutes_for_order(order, new_status)
    order.sla_stage_started_at = now
    order.sla_expected_minutes = exp_new
    order.sla_paused = False
    order.sla_paused_at = None
    db.session.add(
        WorkshopOrderProcessLog(
            order_id=order.id,
            stage_key=new_status,
            started_at=now,
            ended_at=None,
            expected_minutes=float(exp_new),
        )
    )


def apply_sla_pause(order: WorkshopOrder, paused: bool) -> None:
    now = datetime.utcnow()
    if paused:
        if not order.sla_paused:
            order.sla_paused = True
            order.sla_paused_at = now
        return
    # resume
    paused_at = _naive_utc(order.sla_paused_at)
    started = _naive_utc(order.sla_stage_started_at)
    if order.sla_paused and paused_at and started:
        delta = now - paused_at
        order.sla_stage_started_at = started + delta
    order.sla_paused = False
    order.sla_paused_at = None


def monitor_kpis(organization_id: int, orders: list[WorkshopOrder]) -> dict[str, Any]:
    """KPIs agregados para cabecera / panel (órdenes activas)."""
    on_time = risk = delayed = 0
    for o in orders:
        st = (o.status or '').strip()
        if st in ('delivered', 'cancelled'):
            continue
        p = compute_sla_payload(o)
        if not p.get('applicable'):
            continue
        s = p.get('state')
        if s == 'green':
            on_time += 1
        elif s == 'yellow':
            risk += 1
        elif s == 'red':
            delayed += 1

    n = on_time + risk + delayed
    # % de órdenes activas en verde (cumplimiento operativo instantáneo)
    compliance_pct = round(100.0 * on_time / n, 1) if n else None
    if n == 0:
        return {
            'orders_on_time': 0,
            'orders_at_risk': 0,
            'orders_delayed': 0,
            'sla_compliance_pct': compliance_pct,
            'active_count': 0,
        }
    return {
        'orders_on_time': on_time,
        'orders_at_risk': risk,
        'orders_delayed': delayed,
        'sla_compliance_pct': compliance_pct,
        'active_count': n,
    }


def avg_minutes_by_stage(organization_id: int, days: int = 30) -> dict[str, float]:
    """Tiempo medio real por etapa (logs cerrados recientes)."""
    cutoff = datetime.utcnow() - timedelta(days=days)
    rows = (
        db.session.query(
            WorkshopOrderProcessLog.stage_key,
            func.avg(WorkshopOrderProcessLog.duration_minutes),
        )
        .join(WorkshopOrder, WorkshopOrder.id == WorkshopOrderProcessLog.order_id)
        .filter(
            WorkshopOrder.organization_id == organization_id,
            WorkshopOrderProcessLog.ended_at.isnot(None),
            WorkshopOrderProcessLog.duration_minutes.isnot(None),
            WorkshopOrderProcessLog.ended_at >= cutoff,
        )
        .group_by(WorkshopOrderProcessLog.stage_key)
        .all()
    )
    return {str(k): round(float(v or 0), 1) for k, v in rows}


def historical_stage_efficiency_pct(organization_id: int, days: int = 30) -> Optional[float]:
    """% de etapas cerradas sin retraso vs SLA (histórico reciente)."""
    cutoff = datetime.utcnow() - timedelta(days=days)
    total = (
        db.session.query(func.count(WorkshopOrderProcessLog.id))
        .join(WorkshopOrder, WorkshopOrder.id == WorkshopOrderProcessLog.order_id)
        .filter(
            WorkshopOrder.organization_id == organization_id,
            WorkshopOrderProcessLog.ended_at.isnot(None),
            WorkshopOrderProcessLog.ended_at >= cutoff,
        )
        .scalar()
    )
    if not total:
        return None
    ok = (
        db.session.query(func.count(WorkshopOrderProcessLog.id))
        .join(WorkshopOrder, WorkshopOrder.id == WorkshopOrderProcessLog.order_id)
        .filter(
            WorkshopOrder.organization_id == organization_id,
            WorkshopOrderProcessLog.ended_at.isnot(None),
            WorkshopOrderProcessLog.ended_at >= cutoff,
            WorkshopOrderProcessLog.is_delayed.is_(False),
        )
        .scalar()
    )
    return round(100.0 * float(ok or 0) / float(total), 1)


def delayed_counts_by_stage(orders: list[WorkshopOrder]) -> dict[str, int]:
    """Para heatmap / cuello de botella: órdenes activas retrasadas por etapa."""
    heat: dict[str, int] = {}
    for o in orders:
        st = (o.status or '').strip()
        if st in ('delivered', 'cancelled'):
            continue
        p = compute_sla_payload(o)
        if not p.get('applicable') or p.get('state') != 'red':
            continue
        k = str(p.get('stage_key') or '')
        heat[k] = heat.get(k, 0) + 1
    return heat


def sla_monitor_bundle(organization_id: int, orders: list[WorkshopOrder]) -> dict[str, Any]:
    """KPIs + métricas históricas + heatmap + alertas (un solo endpoint monitor)."""
    try:
        workshop_sla_kpis = monitor_kpis(organization_id, orders)
    except Exception:
        workshop_sla_kpis = {
            'orders_on_time': 0,
            'orders_at_risk': 0,
            'orders_delayed': 0,
            'sla_compliance_pct': None,
            'active_count': 0,
        }
    try:
        avg_stage = avg_minutes_by_stage(organization_id, 30)
    except Exception:
        avg_stage = {}
    try:
        eff_hist = historical_stage_efficiency_pct(organization_id, 30)
    except Exception:
        eff_hist = None
    try:
        heat = delayed_counts_by_stage(orders)
    except Exception:
        heat = {}
    top_delayed_stage = None
    if heat:
        sk = max(heat.items(), key=lambda x: x[1])[0]
        top_delayed_stage = {'stage_key': sk, 'count': heat[sk]}
    try:
        alerts = alerts_for_org(organization_id, orders)
    except Exception:
        alerts = {'critical': [], 'preventive': []}
    return {
        'kpis': {
            **workshop_sla_kpis,
            'avg_minutes_by_stage': avg_stage,
            'workshop_efficiency_pct': eff_hist,
        },
        'heatmap_delayed_by_stage': heat,
        'top_delayed_stage': top_delayed_stage,
        'alerts': alerts,
    }


def alerts_for_org(organization_id: int, orders: list[WorkshopOrder]) -> dict[str, list[dict[str, Any]]]:
    """Alertas críticas y preventivas (texto breve)."""
    critical: list[dict[str, Any]] = []
    preventive: list[dict[str, Any]] = []
    for o in orders:
        st = (o.status or '').strip()
        if st in ('delivered', 'cancelled'):
            continue
        p = compute_sla_payload(o)
        if not p.get('applicable'):
            continue
        code = o.code or str(o.id)
        if p['state'] == 'red':
            critical.append(
                {'order_id': o.id, 'code': code, 'message': f'{code}: SLA superado en {p["stage_name"]}'}
            )
        elif p['state'] == 'yellow':
            preventive.append(
                {'order_id': o.id, 'code': code, 'message': f'{code}: Cerca del límite SLA ({p["stage_name"]})'}
            )
        if o.sla_paused:
            critical.append({'order_id': o.id, 'code': code, 'message': f'{code}: Orden en pausa SLA'})

    return {'critical': critical[:50], 'preventive': preventive[:50]}
