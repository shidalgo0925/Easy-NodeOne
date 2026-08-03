#!/usr/bin/env python3
"""
Repara usuarios sin membresía vigente para habilitar certificado de Membresía Básico.

Uso (Dev EN1):
  /opt/easynodeone/dev/venv/bin/python scripts/repair_basic_membership_for_certificates.py
  /opt/easynodeone/dev/venv/bin/python scripts/repair_basic_membership_for_certificates.py --commit
  /opt/easynodeone/dev/venv/bin/python scripts/repair_basic_membership_for_certificates.py --org 3 --commit
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main() -> int:
    parser = argparse.ArgumentParser(description='Asignar membresía básica a usuarios sin plan vigente.')
    parser.add_argument('--org', type=int, default=0, help='Solo usuarios de esta organization_id (0 = todas)')
    parser.add_argument('--commit', action='store_true', help='Aplicar cambios (sin esto: dry-run)')
    args = parser.parse_args()

    from app import app
    from nodeone.services.certificate_membership_rules import repair_users_without_active_membership

    org = int(args.org) if args.org else None
    dry_run = not args.commit

    with app.app_context():
        stats = repair_users_without_active_membership(organization_id=org, dry_run=dry_run)

    mode = 'DRY-RUN' if dry_run else 'COMMIT'
    print(f'=== repair_basic_membership_for_certificates ({mode}) ===')
    for k, v in stats.items():
        print(f'  {k}: {v}')
    if dry_run:
        print('\nEjecutá con --commit para aplicar.')
    return 0 if stats.get('errors', 0) == 0 else 1


if __name__ == '__main__':
    raise SystemExit(main())
