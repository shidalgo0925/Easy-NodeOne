#!/usr/bin/env python3
"""Renombra slugs de Cursos de Arte: taller-* / diplomado-* → curso-en-* (como Espiritualidad)."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Viejo slug WP/histórico → slug canónico (mismo patrón que curso-en-mindfulness-…)
ARTE_SLUG_RENAME: tuple[tuple[str, str], ...] = (
    ('taller-aprendizaje-practico', 'curso-en-aprendizaje-practico'),
    ('taller-liderazgo-y-comunicacion', 'curso-en-liderazgo-y-comunicacion'),
    (
        'diplomado-en-creatividad-y-expresion-artistica-aplicada',
        'curso-en-creatividad-y-expresion-artistica-aplicada',
    ),
    ('taller-desarrollo-humano', 'curso-en-desarrollo-humano'),
)


def main() -> int:
    org_id = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    from app import app, db
    from models.academic_program import AcademicProgram

    with app.app_context():
        for old, new in ARTE_SLUG_RENAME:
            row = AcademicProgram.query.filter_by(organization_id=org_id, slug=old).first()
            if not row:
                print(f'SKIP (no existe): {old}')
                continue
            clash = AcademicProgram.query.filter_by(organization_id=org_id, slug=new).first()
            if clash and clash.id != row.id:
                print(f'CONFLICTO: {new} ya existe id={clash.id}; archivando {old} id={row.id}')
                row.status = 'archived'
                row.slug = f'{old}-archived-{row.id}'
            else:
                row.slug = new
                row.program_type = 'curso'
                row.category = 'Cursos de Arte'
                print(f'OK {old} → {new} (id={row.id})')
        db.session.commit()

        print('\n--- Cursos de Arte publicados ---')
        for p in (
            AcademicProgram.query.filter_by(
                organization_id=org_id, category='Cursos de Arte', status='published'
            )
            .order_by(AcademicProgram.catalog_sort_order)
            .all()
        ):
            print(f'  {p.catalog_sort_order} {p.slug}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
