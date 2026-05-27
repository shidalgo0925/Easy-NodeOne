#!/usr/bin/env python3
"""Cablea 1.er curso de arte en Apps: ② CollageMapas (catálogo) + ③ ChatGPT (inscripción). Sin WP."""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nodeone.modules.academic_enrollment.catalog_public import ARTE_CATEGORY, ARTE_SLUGS

SLUG = ARTE_SLUGS[0]
_MEDIA = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'iius_wp_media_urls.json')


def main() -> int:
    org_id = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    media = json.load(open(_MEDIA, encoding='utf-8')).get('programs') or {}
    catalog_url = (media.get(SLUG) or '').strip()
    flyer_url = (media.get(f'{SLUG}-inscripcion') or catalog_url).strip()

    from app import app, db
    from models.academic_program import AcademicProgram
    from nodeone.modules.academic_enrollment.uploads import import_remote_media_url, _remove_stored_if_local

    with app.app_context():
        p = AcademicProgram.query.filter_by(organization_id=org_id, slug=SLUG).first()
        if not p:
            print(f'No existe {SLUG}. Crear antes con seed o admin.')
            return 1

        for old in (p.image_url, p.flyer_url):
            _remove_stored_if_local(old)

        path_img, err_i = import_remote_media_url(org_id, SLUG, catalog_url, kind='image')
        path_fly, err_f = import_remote_media_url(org_id, SLUG, flyer_url, kind='flyer')
        if not path_img:
            print('ERROR catálogo:', err_i)
            return 1
        p.image_url = path_img
        p.flyer_url = path_fly or path_img
        if err_f:
            print('WARN inscripción:', err_f)
        p.category = ARTE_CATEGORY
        db.session.commit()

        print('Cableado Apps (sin WP):')
        print('  Nombre:', p.name)
        print('  ② Catálogo (CollageMapas):', p.image_url)
        print('  ③ Inscripción:', p.flyer_url)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
