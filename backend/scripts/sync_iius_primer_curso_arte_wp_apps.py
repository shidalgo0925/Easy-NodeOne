#!/usr/bin/env python3
"""Prueba cableado WP ↔ Apps del 1.er curso de Arte (curso-en-aprendizaje-practico)."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nodeone.modules.academic_enrollment.catalog_public import ARTE_CATEGORY, ARTE_SLUGS


def main() -> int:
    org_id = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    slug = ARTE_SLUGS[0]

    from app import app, db
    from models.academic_program import AcademicProgram
    from nodeone.modules.academic_enrollment.wp_cursos_sync import (
        _CursosElementorPage,
        push_curso_slug_to_wp,
        pull_cursos_from_wp,
    )

    with app.app_context():
        print(f'Categoría catálogo Apps: {ARTE_CATEGORY!r}')
        print(f'Primer slug: {slug}')
        print()

        p = AcademicProgram.query.filter_by(organization_id=org_id, slug=slug).first()
        if not p:
            print('ERROR: no existe en Apps. Ejecutá: seed_iius_arte_slugs_apps.py')
            return 1
        print('Apps:', p.name, '|', p.category, '|', p.program_type)

        page = _CursosElementorPage()
        card = page.cards.get(slug)
        if not card:
            print('ERROR: WP no indexó tarjeta. Revisá título «Cursos en Arte» y Div id Cursos_arte.')
            print('Tarjetas WP:', sorted(page.cards.keys()))
            return 1
        from nodeone.modules.academic_enrollment.wp_diplomados_sync import _node_settings

        btn = _node_settings(card.button_node)
        print('WP tarjeta OK | orden', card.sort_order, '| categoría index', card.category)
        print('  botón →', (btn.get('link') or {}).get('url'))

        print('\n1) pull WP → Apps …')
        n, errs = pull_cursos_from_wp(org_id, db)
        print(f'   actualizados (todos los cursos+arte): {n}')
        for e in errs[:5]:
            print('  ', e)

        print('\n2) push Apps → WP (solo este slug) …')
        ok, err = push_curso_slug_to_wp(org_id, slug)
        print('   ', 'OK' if ok else err)

        page2 = _CursosElementorPage()
        btn2 = _node_settings(page2.cards[slug].button_node)
        print('   botón tras push →', (btn2.get('link') or {}).get('url'))
        print('\nListo. Recargá /cursos-detalle/ con Ctrl+F5.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
