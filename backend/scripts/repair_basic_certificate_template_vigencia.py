#!/usr/bin/env python3
"""Añade variables membership_end / dia|mes|anio_membresia_fin a plantillas PLAN-BASIC."""
import argparse
import os
import sys

_BACKEND = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)

from dotenv import load_dotenv

_SILO_ENV = os.environ.get('EASYNODEONE_SILO_ENV')
if _SILO_ENV:
    load_dotenv(_SILO_ENV)
else:
    load_dotenv()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--organization-id', type=int, default=None, help='Solo esta org (default: todas)')
    args = parser.parse_args()

    from app import app, db
    from nodeone.services.certificate_template_membership_vigencia import (
        repair_plan_basic_certificate_templates,
    )

    with app.app_context():
        stats = repair_plan_basic_certificate_templates(db, args.organization_id)
    print(stats)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
