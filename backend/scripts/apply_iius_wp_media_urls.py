#!/usr/bin/env python3
"""Aplica URLs de medios WP a academic_program (flyer_url + media_position)."""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'iius_wp_media_urls.json')


def main() -> int:
    org_id = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    with open(_DATA, encoding='utf-8') as f:
        cfg = json.load(f)
    default_pos = (cfg.get('default_media_position') or 'left').strip().lower()
    if default_pos not in ('left', 'right'):
        default_pos = 'left'
    mapping = cfg.get('programs') or {}

    from app import app, db
    from nodeone.services.academic_program_schema import ensure_academic_program_schema
    from models.academic_program import AcademicProgram

    updated = missing = 0
    with app.app_context():
        ensure_academic_program_schema(db, db.engine, printfn=print)
        for row in AcademicProgram.query.filter_by(organization_id=org_id).all():
            url = (mapping.get(row.slug) or '').strip()
            if not url:
                missing += 1
                print(f'SKIP no WP url slug={row.slug}')
                continue
            row.flyer_url = url
            if not (row.image_url or '').strip():
                row.image_url = url
            row.media_position = default_pos
            updated += 1
            print(f'OK {row.slug}')
        db.session.commit()
    print(f'Done org={org_id}: updated={updated} missing_mapping={missing}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
