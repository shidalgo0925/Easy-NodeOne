#!/usr/bin/env python3
"""Completa catálogo IIUS en apps: 12 cursos + 4 arte + 4 talleres (sin WP)."""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nodeone.modules.academic_enrollment.wp_cursos_sync import CURSO_SLUGS_BY_SECTION
from nodeone.modules.academic_enrollment.wp_talleres_sync import ARTE_SLUGS
from nodeone.modules.academic_enrollment.catalog_public import TALLERES_DISPLAY_ORDER

_DATA = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'iius_academic_catalog.json')

from nodeone.modules.academic_enrollment.wp_talleres_sync import ARTE_SLUGS, _FORMAL_NAMES

ARTE_FIX = {slug: (_FORMAL_NAMES[slug], i) for i, slug in enumerate(ARTE_SLUGS, 1)}


def main() -> int:
    org_id = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    catalog = {p['slug']: p for p in json.load(open(_DATA, encoding='utf-8')).get('programs', [])}

    from app import app, db
    from models.academic_program import AcademicProgram

    with app.app_context():
        # 12 cursos WP: categoría + orden 1–4
        for category, slugs in CURSO_SLUGS_BY_SECTION.items():
            for order, slug in enumerate(slugs, 1):
                row = AcademicProgram.query.filter_by(organization_id=org_id, slug=slug).first()
                if not row:
                    print(f'FALTA curso: {slug}')
                    continue
                row.category = category
                row.program_type = 'curso'
                row.catalog_sort_order = order
                row.status = 'published'
                seed = catalog.get(slug) or {}
                if seed.get('name'):
                    row.name = seed['name']
                if seed.get('short_description'):
                    row.short_description = seed['short_description']
                print(f'curso {order} {category[:12]} {slug}')

        # Neuroplasticidad (apps, no en WP cursos-detalle): publicado al final de Ciencia
        np = AcademicProgram.query.filter_by(
            organization_id=org_id, slug='curso-de-neuroeducacion-y-neuroplasticidad'
        ).first()
        if np:
            np.category = 'Cursos en Ciencia'
            np.program_type = 'curso'
            np.catalog_sort_order = 5
            np.status = 'published'
            seed = catalog.get(np.slug) or {}
            if seed.get('name'):
                np.name = seed['name']
            print(f'curso 5 Ciencia {np.slug}')

        # Cursos de Arte: 4 cursos, orden 1–4
        for slug, (name, order) in ARTE_FIX.items():
            row = AcademicProgram.query.filter_by(organization_id=org_id, slug=slug).first()
            if not row:
                print(f'FALTA arte: {slug}')
                continue
            row.name = name
            row.program_type = 'curso'
            row.category = 'Cursos de Arte'
            row.catalog_sort_order = order
            row.status = 'published'
            seed = catalog.get(slug) or {}
            if seed.get('short_description'):
                row.short_description = seed['short_description']
            print(f'arte {order} {slug}')

        # Talleres (solo Fundamentos en categoría Talleres; orden vitrina en catalog_public)
        tf = AcademicProgram.query.filter_by(
            organization_id=org_id, slug='taller-fundamentos-coaching-ejecutivo'
        ).first()
        if tf:
            tf.program_type = 'taller'
            tf.category = 'Talleres'
            tf.catalog_sort_order = 4
            tf.status = 'published'
            print(f'taller {tf.slug}')

        db.session.commit()

        from nodeone.modules.academic_enrollment.catalog_public import group_programs_for_template

        print('\n--- Vitrina ---')
        for title, progs in group_programs_for_template(org_id):
            if 'Curso' in title or title == 'Talleres':
                print(f'[{title}] {len(progs)}', [p.catalog_sort_order for p in progs])
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
