#!/usr/bin/env python3
"""Corrige Cursos de Arte en apps: nombres/slugs alineados, program_type=curso, orden 1-4."""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Slug canónico (inscripción) → metadatos en catálogo apps
from nodeone.modules.academic_enrollment.wp_talleres_sync import ARTE_SLUGS, _FORMAL_NAMES

CURSOS_DE_ARTE: tuple[dict, ...] = (
    {
        'slug': 'curso-en-aprendizaje-practico',
        'name': _FORMAL_NAMES['curso-en-aprendizaje-practico'],
        'catalog_sort_order': 1,
        'short_description': 'Habilidades aplicadas mediante experiencias de aprendizaje dinámicas.',
        'price_from': 349.0,
    },
    {
        'slug': 'curso-en-liderazgo-y-comunicacion',
        'name': _FORMAL_NAMES['curso-en-liderazgo-y-comunicacion'],
        'catalog_sort_order': 2,
        'short_description': 'Competencias de liderazgo y comunicación en entornos personales y profesionales.',
        'price_from': 349.0,
    },
    {
        'slug': 'curso-en-creatividad-y-expresion-artistica-aplicada',
        'name': _FORMAL_NAMES['curso-en-creatividad-y-expresion-artistica-aplicada'],
        'catalog_sort_order': 3,
        'short_description': 'Arte como herramienta de bienestar e innovación.',
        'price_from': 499.0,
    },
    {
        'slug': 'curso-en-desarrollo-humano',
        'name': _FORMAL_NAMES['curso-en-desarrollo-humano'],
        'catalog_sort_order': 4,
        'short_description': 'Crecimiento integral de habilidades personales, sociales y profesionales.',
        'price_from': 349.0,
    },
)


def main() -> int:
    org_id = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    from app import app, db
    from models.academic_program import AcademicProgram

    with app.app_context():
        for spec in CURSOS_DE_ARTE:
            slug = spec['slug']
            row = AcademicProgram.query.filter_by(organization_id=org_id, slug=slug).first()
            if not row:
                print(f'FALTA slug en BD: {slug}')
                continue
            row.name = spec['name']
            row.program_type = 'curso'
            row.category = 'Cursos de Arte'
            row.catalog_sort_order = int(spec['catalog_sort_order'])
            row.short_description = spec['short_description']
            row.status = 'published'
            if spec.get('price_from') is not None:
                row.price_from = float(spec['price_from'])
            print(f"OK ord={row.catalog_sort_order} {slug} → {row.name}")
        db.session.commit()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
