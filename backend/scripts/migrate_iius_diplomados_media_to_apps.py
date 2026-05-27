#!/usr/bin/env python3
"""Copia imágenes de diplomados neuro desde WP (URLs) → /static/uploads/ en apps y publica en Elementor."""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nodeone.modules.academic_enrollment.wp_diplomados_sync import DIPLOMADO_SLUGS

_DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'iius_wp_media_urls.json')
APPS_BASE = os.environ.get('NODEONE_PUBLIC_BASE_URL', 'https://apps.internationalinstitute.us').rstrip('/')

_WP_ATTACHMENT_ID_BY_SLUG: dict[str, int] = {
    'neuro-teologia-coaching-cristiano-transgeneracional': 899,
}


def _wp_attachment_url(attachment_id: int) -> str | None:
    import subprocess

    proc = subprocess.run(
        [
            'sudo',
            '-u',
            'www-data',
            'wp',
            'eval',
            f'echo wp_get_attachment_url({int(attachment_id)});',
            '--path=/var/www/wordpress',
        ],
        capture_output=True,
        text=True,
        env={'WP_CLI_CACHE_DIR': '/var/www/.wp-cli/cache'},
    )
    if proc.returncode != 0:
        return None
    return (proc.stdout or '').strip() or None


def main() -> int:
    org_id = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    with open(_DATA, encoding='utf-8') as f:
        media_map = json.load(f).get('programs') or {}

    from app import app, db
    from models.academic_program import AcademicProgram
    from nodeone.modules.academic_enrollment.uploads import import_remote_media_url, is_apps_local_media_path
    from nodeone.modules.academic_enrollment.wp_diplomados_sync import push_diplomados_to_wp
    from nodeone.services.academic_program_schema import ensure_academic_program_schema

    with app.app_context():
        ensure_academic_program_schema(db, db.engine, printfn=print)
        for slug in DIPLOMADO_SLUGS:
            row = AcademicProgram.query.filter_by(organization_id=org_id, slug=slug).first()
            if not row:
                print(f'MISSING {slug}')
                continue
            remote = (media_map.get(slug) or row.flyer_url or row.image_url or '').strip()
            aid = _WP_ATTACHMENT_ID_BY_SLUG.get(slug)
            if aid:
                wp_url = _wp_attachment_url(aid)
                if wp_url:
                    remote = wp_url
            if not remote:
                print(f'SKIP no url {slug}')
                continue
            for kind, attr in (('image', 'image_url'), ('flyer', 'flyer_url')):
                current = (getattr(row, attr) or '').strip()
                src = remote
                if is_apps_local_media_path(current) and os.path.isfile(
                    os.path.normpath(os.path.join(app.root_path, '..', current.lstrip('/')))
                ):
                    print(f'OK already local {slug} {attr}')
                    continue
                path, err = import_remote_media_url(org_id, slug, src, kind=kind)
                if err:
                    print(f'ERR {slug} {kind}: {err}')
                    continue
                setattr(row, attr, path)
                print(f'OK {slug} {attr} -> {path}')
        db.session.commit()

        print('--- Push Apps → WP (URLs absolutas apps) ---')
        n, errs = push_diplomados_to_wp(org_id)
        print(f'push programs={n} errs={errs}')
    print('Done.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
