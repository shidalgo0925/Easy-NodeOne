#!/usr/bin/env python3
"""Auditoría de media en programas de inscripción (image_url / flyer_url)."""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main() -> int:
    parser = argparse.ArgumentParser(description='Audita image_url y flyer_url por programa.')
    parser.add_argument('organization_id', nargs='?', type=int, default=1)
    parser.add_argument('--published-only', action='store_true')
    parser.add_argument('--fail-on-error', action='store_true', help='Exit 1 si hay published con problemas')
    args = parser.parse_args()

    from app import app
    from models.academic_program import AcademicProgram
    from nodeone.modules.academic_enrollment.program_display_media import audit_program_media_row

    with app.app_context():
        q = AcademicProgram.query.filter_by(organization_id=int(args.organization_id))
        if args.published_only:
            q = q.filter_by(status='published')
        rows = q.order_by(AcademicProgram.slug.asc()).all()

        header = ('slug', 'published', 'image_url', 'flyer_url', 'catalog_ok', 'enroll_ok', 'audit_status')
        print('\t'.join(header))
        problems = 0
        for p in rows:
            r = audit_program_media_row(p)
            if r['audit_status'] not in ('ok', 'draft_or_archived'):
                problems += 1
            print(
                '\t'.join(
                    [
                        r['slug'],
                        'yes' if r['published'] else 'no',
                        r['image_url'] or '',
                        r['flyer_url'] or '',
                        _ok_label(r['catalog_file_exists']),
                        _ok_label(r['enrollment_file_exists']),
                        r['audit_status'],
                    ]
                )
            )
        print(f'\nTotal: {len(rows)} | Problemas (published/archived con media rota): {problems}')
        if args.fail_on_error and problems:
            return 1
    return 0


def _ok_label(v) -> str:
    if v is None:
        return '-'
    return 'yes' if v else 'no'


if __name__ == '__main__':
    raise SystemExit(main())
