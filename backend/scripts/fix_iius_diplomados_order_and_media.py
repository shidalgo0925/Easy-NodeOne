#!/usr/bin/env python3
"""Orden IIUS diplomados neuro (1–4) + medios desde data/iius_wp_media_urls.json."""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Orden de negocio (WP): ① Liderazgo … ④ Heurística
_DIPLOMADO_NEURO_ORDER: tuple[tuple[str, int, str], ...] = (
    ('neuro-liderazgo-intercultural', 1, 'right'),
    ('neuro-descodificacion-psicogenealogia-pnl', 2, 'left'),
    ('neuro-teologia-coaching-cristiano-transgeneracional', 3, 'right'),
    ('neuro-heuristica-coaching-vida', 4, 'left'),
)

_DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'iius_wp_media_urls.json')


def main() -> int:
    org_id = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    with open(_DATA, encoding='utf-8') as f:
        media_map = (json.load(f).get('programs') or {})

    from app import app, db
    from nodeone.services.academic_program_schema import ensure_academic_program_schema
    from models.academic_program import AcademicProgram

    with app.app_context():
        ensure_academic_program_schema(db, db.engine, printfn=print)
        for slug, sort_order, media_pos in _DIPLOMADO_NEURO_ORDER:
            row = AcademicProgram.query.filter_by(organization_id=org_id, slug=slug).first()
            if not row:
                print(f'MISSING slug={slug}')
                continue
            row.catalog_sort_order = sort_order
            row.media_position = media_pos
            url = (media_map.get(slug) or '').strip()
            if url:
                row.flyer_url = url
                row.image_url = url
            landing = (row.image_wp_landing or '').strip()
            if not landing:
                row.image_wp_landing = (row.flyer_url or row.image_url or url or '').strip() or None
            print(
                f'OK sort={sort_order} pos={media_pos} slug={slug} '
                f'wp_landing={"yes" if row.image_wp_landing else "no"}'
            )
        db.session.commit()
    print('Done.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
