#!/usr/bin/env python3
"""Auditoría read-only: catálogo academic_program, eventos y slugs legacy (IIUS org 1)."""

from __future__ import annotations

import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

ORG_ID = 1


def main() -> int:
    from app import app, db
    from models.academic_program import AcademicProgram
    from models.catalog import Service
    from models.events import Event
    from nodeone.modules.academic_enrollment.catalog_public import (
        ARTE_SLUGS,
        TALLERES_DISPLAY_ORDER,
        group_programs_for_template,
    )
    from nodeone.modules.academic_enrollment.wp_talleres_catalog_sync import TALLERES_SLUG_LEGACY
    from nodeone.modules.academic_enrollment.wp_talleres_sync import ARTE_SLUG_LEGACY

    issues: list[str] = []

    with app.app_context():
        print('=== IIUS catálogo / eventos (org 1) ===\n')

        progs = AcademicProgram.query.filter_by(organization_id=ORG_ID).all()
        published = [p for p in progs if (p.status or '').lower() == 'published']
        drafts = [p for p in progs if (p.status or '').lower() != 'published']
        print(f'academic_program: total={len(progs)} published={len(published)} no-published={len(drafts)}')

        slugs = [(p.slug or '').strip().lower() for p in progs if p.slug]
        dups = {s: c for s, c in Counter(slugs).items() if c > 1}
        if dups:
            issues.append(f'slugs duplicados: {dups}')
        print(f'  slugs duplicados: {dups or "ninguno"}')

        no_cat = [p.slug for p in published if not (getattr(p, 'category', None) or '').strip()]
        if no_cat:
            issues.append(f'published sin category: {no_cat}')
        print(f'  published sin categoría: {len(no_cat)}')

        for title, items in group_programs_for_template(ORG_ID):
            print(f'  vitrina [{title}]: {len(items)}')

        arte_in_db = {
            (p.slug or '').strip().lower()
            for p in published
            if (p.category or '').strip() == 'Cursos de Arte'
        }
        arte_expected = set(ARTE_SLUGS)
        if arte_in_db != arte_expected:
            issues.append(f'ARTE_SLUGS drift: bd={sorted(arte_in_db)} const={sorted(arte_expected)}')
        print(f'  ARTE alineado con constantes: {arte_in_db == arte_expected}')

        talleres_in_db = {
            (p.slug or '').strip().lower()
            for p in published
            if (p.slug or '').strip().lower() in TALLERES_DISPLAY_ORDER
        }
        print(f'  talleres publicados: {sorted(talleres_in_db)}')

        print('\n=== Eventos ===')
        evs = Event.query.order_by(Event.publish_status, Event.slug).all()
        by_st: dict[str, int] = {}
        for e in evs:
            by_st[e.publish_status or '?'] = by_st.get(e.publish_status or '?', 0) + 1
        print('  por status:', by_st)
        for e in evs:
            print(f'    [{e.publish_status}] {e.slug}')

        print('\n=== Services COURSE legacy (org 1) ===')
        legacy_keys = set(TALLERES_SLUG_LEGACY) | set(ARTE_SLUG_LEGACY)
        svcs = Service.query.filter_by(organization_id=ORG_ID, service_type='COURSE').all()
        active_legacy = [
            s
            for s in svcs
            if getattr(s, 'is_active', False) and (s.program_slug or '').strip().lower() in legacy_keys
        ]
        print(f'  services COURSE: {len(svcs)} activos con slug legacy: {len(active_legacy)}')
        for s in active_legacy[:12]:
            print(f'    legacy activo: {s.program_slug}')

        if active_legacy:
            print(
                f'  NOTA: {len(active_legacy)} service(s) legacy activos; '
                '/programs/<slug> redirige a /inscripcion/ si hay programa publicado'
            )

        if issues:
            print('\n=== ISSUES ===')
            for i in issues:
                print(' -', i)
            print(f'\nResumen: {len(issues)} issue(s)')
            return 1

        print('\nResumen: sin issues críticos de auditoría')
        return 0


if __name__ == '__main__':
    raise SystemExit(main())
