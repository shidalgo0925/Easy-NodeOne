#!/usr/bin/env python3
"""Restaura json_layout institucional visual de una plantilla de evento.

Uso (Relatic aislada):
  cd /opt/easynodeone/relatic/app/backend
  set -a && source /opt/easynodeone/relatic/.env && set +a
  export NODEONE_ROOT=/opt/easynodeone/relatic/app
  /opt/easynodeone/dev/venv/bin/python3 scripts/repair_event_visual_certificate_template.py --event-id 2 --preserve-background
"""

from __future__ import annotations

import argparse
import json
import os
import sys

_BACKEND = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)


def main() -> int:
    parser = argparse.ArgumentParser(description='Repara plantilla visual de certificado de evento')
    parser.add_argument('--event-id', type=int, required=True)
    parser.add_argument('--template-id', type=int, default=0, help='Opcional; por defecto visual_template_id del evento')
    parser.add_argument('--preserve-background', action='store_true', help='Mantiene background_image actual')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()

    from dotenv import load_dotenv

    root = os.environ.get('NODEONE_ROOT') or os.path.abspath(os.path.join(_BACKEND, '..'))
    load_dotenv(os.path.join(os.path.dirname(root), '.env'), override=False)
    load_dotenv(os.path.join(root, '.env'), override=False)
    os.environ.setdefault('NODEONE_ROOT', root)

    from app import CertificateTemplate, Event, app, db
    from nodeone.services.certificate_visual_templates import (
        apply_institutional_visual_layout_to_template,
        link_visual_template_to_event,
        parse_visual_layout,
        resolve_event_org_id,
        visual_template_id_for_event,
    )

    with app.app_context():
        event = Event.query.get(int(args.event_id))
        if not event:
            print(f'Evento #{args.event_id} no encontrado', file=sys.stderr)
            return 1
        org_id = resolve_event_org_id(event)
        tid = int(args.template_id or visual_template_id_for_event(event) or 0)
        if not tid:
            print('Sin visual_template_id en el evento', file=sys.stderr)
            return 1
        tpl = CertificateTemplate.query.filter_by(id=tid, organization_id=org_id).first()
        if not tpl:
            tpl = CertificateTemplate.query.get(tid)
        if not tpl:
            print(f'Plantilla #{tid} no encontrada', file=sys.stderr)
            return 1

        before = parse_visual_layout(tpl.json_layout) or {}
        before_n = len(before.get('elements') or [])
        prev_bg = tpl.background_image

        if args.dry_run:
            print(f'[dry-run] event={event.id} template={tid} elements_antes={before_n} bg={prev_bg!r}')
            return 0

        apply_institutional_visual_layout_to_template(
            tpl,
            event,
            org_id,
            preserve_background=bool(args.preserve_background),
            app_root=root,
        )
        link_visual_template_to_event(event, int(tpl.id))
        db.session.commit()

        after = parse_visual_layout(tpl.json_layout) or {}
        after_n = len(after.get('elements') or [])
        print(
            json.dumps(
                {
                    'ok': True,
                    'event_id': event.id,
                    'template_id': tpl.id,
                    'elements_before': before_n,
                    'elements_after': after_n,
                    'background_image': tpl.background_image,
                    'name': tpl.name,
                },
                ensure_ascii=False,
            )
        )
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
