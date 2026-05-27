#!/usr/bin/env python3
"""Apps: archivos estáticos + BD para curso-en-aprendizaje-practico (sin WP)."""
from __future__ import annotations

import json
import os
import sys
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

SLUG = 'curso-en-aprendizaje-practico'
CATALOG_STATIC = '/static/uploads/CollageMapas.png'
ENROLLMENT_STATIC = '/static/uploads/ChatGPT-Image-19-may-2026-21_51_22.png'

_MEDIA = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'iius_wp_media_urls.json')


def _download_to_static(public_path: str, remote_url: str, app_root: str) -> tuple[bool, str]:
    rel = public_path.lstrip('/')
    if not rel.startswith('static/uploads/'):
        return False, 'Ruta pública no válida'
    dest = os.path.normpath(os.path.join(app_root, '..', rel))
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    parts = urllib.parse.urlsplit(remote_url.strip())
    safe_path = urllib.parse.quote(parts.path, safe='/:@!$&\'()*+,;=-._~')
    url = urllib.parse.urlunsplit((parts.scheme, parts.netloc, safe_path, parts.query, parts.fragment))
    req = urllib.request.Request(url, headers={'User-Agent': 'NodeOne/1.0 (iius-media-fix)'})
    with urllib.request.urlopen(req, timeout=90) as resp:
        data = resp.read()
    if len(data) > 12 * 1024 * 1024:
        return False, 'Archivo demasiado grande'
    with open(dest, 'wb') as f:
        f.write(data)
    return True, dest


def main() -> int:
    org_id = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    media = json.load(open(_MEDIA, encoding='utf-8')).get('programs') or {}
    catalog_remote = (media.get(SLUG) or '').strip()
    enroll_remote = (media.get(f'{SLUG}-inscripcion') or '').strip()
    if not catalog_remote or not enroll_remote:
        print('Faltan URLs en iius_wp_media_urls.json')
        return 1

    from app import app, db
    from models.academic_program import AcademicProgram

    with app.app_context():
        root = app.root_path
        p = AcademicProgram.query.filter_by(organization_id=org_id, slug=SLUG).first()
        if not p:
            print(f'No existe programa {SLUG}')
            return 1
        for pub, remote in (
            (CATALOG_STATIC, catalog_remote),
            (ENROLLMENT_STATIC, enroll_remote),
        ):
            ok, msg = _download_to_static(pub, remote, root)
            if not ok:
                print('ERROR descarga', pub, msg)
                return 1
            print('OK archivo:', msg)
        p.image_url = CATALOG_STATIC
        p.flyer_url = ENROLLMENT_STATIC
        db.session.commit()
        print('BD image_url (② catálogo):', p.image_url)
        print('BD flyer_url (③ inscripción):', p.flyer_url)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
