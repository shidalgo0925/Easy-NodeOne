"""
Repara logs SLA de órdenes de taller (logs abiertos desincronizados, OT cerradas con SLA activo).

Uso (staging primero):
  python3 scripts/repair_workshop_sla_logs.py <organization_id>           # dry-run
  python3 scripts/repair_workshop_sla_logs.py <organization_id> --commit
  python3 scripts/repair_workshop_sla_logs.py --all-orgs --commit

No modifica cotizaciones ni facturas.
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _repair_organization(org_id: int, *, commit: bool) -> dict:
    from app import app, db
    from nodeone.modules.workshop import sla_service
    from nodeone.modules.workshop.models import WorkshopOrder, WorkshopOrderProcessLog

    stats = {
        'orders_seen': 0,
        'closed_logs': 0,
        'created_logs': 0,
        'sla_started_synced': 0,
        'terminal_cleared': 0,
    }

    with app.app_context():
        sla_service.ensure_default_process_stages(org_id)
        now = datetime.utcnow()
        orders = WorkshopOrder.query.filter_by(organization_id=org_id).order_by(WorkshopOrder.id).all()
        for order in orders:
            stats['orders_seen'] += 1
            st = (order.status or 'draft').strip()

            open_logs = WorkshopOrderProcessLog.query.filter_by(
                order_id=order.id, ended_at=None
            ).all()

            if st in sla_service.CLOSED_ORDER_STATUSES:
                for log in open_logs:
                    sla_service._close_open_log(log, order, now)
                    stats['closed_logs'] += 1
                if order.sla_stage_started_at is not None or order.sla_expected_minutes is not None:
                    order.sla_stage_started_at = None
                    order.sla_expected_minutes = None
                    stats['terminal_cleared'] += 1
                continue

            if st not in sla_service.ACTIVE_ORDER_STATUSES:
                continue

            for log in open_logs:
                if (log.stage_key or '').strip() != st:
                    sla_service._close_open_log(log, order, now)
                    stats['closed_logs'] += 1

            current_open = WorkshopOrderProcessLog.query.filter_by(
                order_id=order.id, stage_key=st, ended_at=None
            ).first()
            if not current_open:
                exp_new, _ = sla_service.expected_minutes_for_order(order, st)
                started = order.sla_stage_started_at or now
                current_open = WorkshopOrderProcessLog(
                    order_id=order.id,
                    stage_key=st,
                    started_at=started,
                    ended_at=None,
                    expected_minutes=float(exp_new),
                )
                db.session.add(current_open)
                db.session.flush()
                stats['created_logs'] += 1

            if current_open and order.sla_stage_started_at != current_open.started_at:
                order.sla_stage_started_at = current_open.started_at
                exp_new, _ = sla_service.expected_minutes_for_order(order, st)
                order.sla_expected_minutes = exp_new
                stats['sla_started_synced'] += 1

        if commit:
            db.session.commit()
        else:
            db.session.rollback()

    return stats


def main() -> int:
    parser = argparse.ArgumentParser(description='Repara logs SLA del taller por organización.')
    parser.add_argument('organization_id', nargs='?', type=int, help='ID de organización')
    parser.add_argument('--all-orgs', action='store_true', help='Procesar todas las organizaciones')
    parser.add_argument('--commit', action='store_true', help='Persistir cambios (por defecto dry-run)')
    args = parser.parse_args()

    if not args.all_orgs and args.organization_id is None:
        parser.print_help()
        return 2

    from app import app
    from models.saas import SaasOrganization

    org_ids: list[int] = []
    with app.app_context():
        if args.all_orgs:
            org_ids = [r.id for r in SaasOrganization.query.order_by(SaasOrganization.id).all()]
        else:
            org_ids = [int(args.organization_id)]

    mode = 'COMMIT' if args.commit else 'DRY-RUN'
    print(f'[{mode}] Reparación SLA taller — {len(org_ids)} org(s)')
    for oid in org_ids:
        stats = _repair_organization(oid, commit=args.commit)
        print(f'  org {oid}: {stats}')
    if not args.commit:
        print('Sin --commit: no se guardaron cambios.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
