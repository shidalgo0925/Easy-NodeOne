#!/usr/bin/env python3
"""
Desactiva formatos certificate_events huérfanos (REL seminario sin evento/plan)
y deduplica MEM/REL vs PLAN-* por plan de membresía.

Uso:
  python scripts/repair_orphan_seminar_certificate_events.py
  python scripts/repair_orphan_seminar_certificate_events.py --org 1
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--org', type=int, default=0, help='Organización (0 = todas activas)')
    args = parser.parse_args()

    from app import SaasOrganization, app
    from nodeone.services.certificate_membership_rules import (
        run_legacy_certificate_event_cleanup,
        seed_membership_certificate_events_for_org,
    )

    from nodeone.core.db import db

    with app.app_context():
        if args.org:
            org_ids = [int(args.org)]
        else:
            org_ids = [int(o.id) for o in SaasOrganization.query.filter_by(is_active=True).all()]
        for oid in org_ids:
            seed_membership_certificate_events_for_org(db, oid)
            run_legacy_certificate_event_cleanup(db, oid)
            print(f'org {oid}: seed + cleanup OK')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
