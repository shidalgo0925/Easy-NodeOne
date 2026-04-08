#!/usr/bin/env python3
"""
Migra filas automation_flows → communication_rule (canal email, marketing).

Idempotente: no duplica si ya existe regla con mismo evento, plantilla, delay y ámbito global.

Uso:
    python3 backend/migrate_automation_flows_to_communication_rules.py
    python3 backend/migrate_automation_flows_to_communication_rules.py --deactivate-flows

--deactivate-flows: pone active=False en cada AutomationFlow para el que se creó regla nueva
(reduce doble envío hasta activar NODEONE_AUTOMATION_DEFER_TO_COMM_ENGINE=1).
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db  # noqa: E402
from models.communications import AutomationFlow  # noqa: E402
from models.communication_rules import CommunicationEvent, CommunicationRule  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description='AutomationFlow → CommunicationRule')
    parser.add_argument(
        '--deactivate-flows',
        action='store_true',
        help='Desactivar AutomationFlow tras crear regla (evitar duplicar con trigger_automation)',
    )
    parser.add_argument(
        '--all-flows',
        action='store_true',
        help='Incluir flujos inactivos (por defecto solo active=True)',
    )
    args = parser.parse_args()

    with app.app_context():
        CommunicationEvent.__table__.create(db.engine, checkfirst=True)
        CommunicationRule.__table__.create(db.engine, checkfirst=True)

        fq = AutomationFlow.query
        if not args.all_flows:
            fq = fq.filter_by(active=True)
        flows = fq.order_by(AutomationFlow.id.asc()).all()
        created = 0
        skipped_dup = 0
        skipped_unknown = 0
        deactivated = 0

        for flow in flows:
            ev = CommunicationEvent.query.filter_by(code=flow.trigger_event).first()
            if not ev:
                skipped_unknown += 1
                print(f'⚠️ Flow id={flow.id}: sin communication_event para trigger={flow.trigger_event!r}')
                continue

            delay_minutes = int(flow.delay_hours or 0) * 60
            dup = (
                CommunicationRule.query.filter_by(
                    event_id=ev.id,
                    channel='email',
                    marketing_template_id=flow.template_id,
                    delay_minutes=delay_minutes,
                    organization_id=None,
                ).first()
            )
            if dup:
                skipped_dup += 1
                continue

            rule = CommunicationRule(
                event_id=ev.id,
                organization_id=None,
                channel='email',
                marketing_template_id=flow.template_id,
                enabled=bool(flow.active),
                delay_minutes=delay_minutes,
                is_marketing=True,
                respect_user_prefs=True,
                priority=20,
            )
            db.session.add(rule)
            created += 1

            if args.deactivate_flows and flow.active:
                flow.active = False
                deactivated += 1

        db.session.commit()
        print(
            f'✅ communication_rule desde automation_flows: +{created} nuevas, '
            f'{skipped_dup} ya existían, {skipped_unknown} trigger sin catálogo, '
            f'flows desactivados: {deactivated}'
        )


if __name__ == '__main__':
    main()
