#!/usr/bin/env python3
"""Crea/actualiza los 4 slugs de Cursos de Arte en apps (sin WordPress)."""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nodeone.modules.academic_enrollment.wp_talleres_sync import ARTE_SLUGS

_CATALOG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'iius_academic_catalog.json')
_MEDIA_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'iius_wp_media_urls.json')


def main() -> int:
    org_id = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    catalog_by_slug = {e['slug']: e for e in json.load(open(_CATALOG_PATH, encoding='utf-8')).get('programs', [])}
    media = json.load(open(_MEDIA_PATH, encoding='utf-8')).get('programs') or {}

    from app import app, db
    from models.academic_program import AcademicProgram, AcademicProgramPricingPlan
    from nodeone.modules.academic_enrollment.uploads import import_remote_media_url, is_apps_local_media_path
    from scripts.seed_iius_academic_catalog_paso1 import _upsert_plans_from_json

    created = updated = 0
    with app.app_context():
        for slug in ARTE_SLUGS:
            entry = catalog_by_slug.get(slug)
            if not entry:
                print(f'FALTA en JSON: {slug}')
                continue
            row = AcademicProgram.query.filter_by(organization_id=org_id, slug=slug).first()
            is_new = row is None
            if is_new:
                row = AcademicProgram(organization_id=org_id, slug=slug, name=entry.get('name') or slug)
                db.session.add(row)

            row.name = entry.get('name') or row.name
            row.program_type = (entry.get('program_type') or 'curso').strip().lower()
            row.category = (entry.get('category') or 'Cursos de Arte').strip()
            row.catalog_sort_order = int(entry.get('catalog_sort_order') or ARTE_SLUGS.index(slug) + 1)
            row.status = (entry.get('status') or 'published').strip().lower()
            row.modality = entry.get('modality') or '100% online'
            row.language = entry.get('language') or 'Español'
            row.currency = 'USD'
            row.price_from = float(entry.get('price_from') or 349)
            row.short_description = (entry.get('short_description') or '').strip() or None

            remote = (media.get(slug) or '').strip()
            force_img = '--force-images' in sys.argv
            if remote and (force_img or not is_apps_local_media_path(row.image_url)):
                path, err = import_remote_media_url(org_id, slug, remote, kind='image')
                if path:
                    row.image_url = path
                elif err:
                    print(f'WARN imagen {slug}: {err}')

            db.session.flush()
            if entry.get('plans'):
                _upsert_plans_from_json(row, entry['plans'], AcademicProgramPricingPlan, db)
            db.session.commit()

            if is_new:
                created += 1
                print(f'CREATED {slug} id={row.id}')
            else:
                updated += 1
                print(f'UPDATED {slug} id={row.id}')

        print(f'\nArte org={org_id}: created={created} updated={updated}')
        for slug in ARTE_SLUGS:
            p = AcademicProgram.query.filter_by(organization_id=org_id, slug=slug).first()
            ok = 'OK' if p and p.status == 'published' else 'FALTA'
            print(f'  {ok} ord={getattr(p,"catalog_sort_order",None)} {slug}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
