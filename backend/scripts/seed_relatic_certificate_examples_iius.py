#!/usr/bin/env python3
"""Siembra plantillas/formatos de ejemplo Relatic en org IIUS (1).

Copia el layout institucional Relatic (data/relatic_event_certificate_layout.json),
asegura assets en static/uploads/certificates/layout/ y crea:
  - CertificateTemplate «Ejemplo Relatic — institucional»
  - Actualiza CertificateEvent REG/MEM con branding Relatic de ejemplo
  - ensure_certificate_assets_for_org(1)

Uso:
  cd /opt/easynodeone/app/backend && source ../.venv/bin/activate
  python scripts/seed_relatic_certificate_examples_iius.py
"""

from __future__ import annotations

import json
import os
import shutil
import sys

_BACKEND = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)

ROOT = os.path.abspath(os.path.join(_BACKEND, '..'))
LAYOUT_SRC = os.path.join(_BACKEND, 'data', 'relatic_event_certificate_layout.json')
LAYOUT_DIR = os.path.join(ROOT, 'static', 'uploads', 'certificates', 'layout')


def _ensure_layout_assets() -> None:
    os.makedirs(LAYOUT_DIR, exist_ok=True)
    mapping = {
        'logo_relatic.png': [
            os.path.join(ROOT, 'static', 'images', 'logo-relatic.png'),
            os.path.join(ROOT, 'static', 'public', 'emails', 'logos', 'logo-relatic.png'),
        ],
        'seal_relatic.png': [
            os.path.join(ROOT, 'static', 'images', 'logo-relatic.png'),
            os.path.join(ROOT, 'static', 'public', 'emails', 'logos', 'logo-relatic.png'),
        ],
        'logo_ujml.png': [
            os.path.join(ROOT, 'static', 'public', 'emails', 'logos', 'logo-platform.png'),
            os.path.join(ROOT, 'static', 'images', 'logo-primary.svg'),
        ],
    }
    for dest_name, candidates in mapping.items():
        dest = os.path.join(LAYOUT_DIR, dest_name)
        if os.path.isfile(dest) and os.path.getsize(dest) > 0:
            continue
        for src in candidates:
            if os.path.isfile(src):
                shutil.copy2(src, dest)
                print(f'  asset {dest_name} <- {src}')
                break
        else:
            print(f'  WARN missing asset for {dest_name}')


def main() -> int:
    from dotenv import load_dotenv

    load_dotenv(os.path.join(ROOT, '.env'), override=False)
    os.environ.setdefault('NODEONE_ROOT', ROOT)

    from app import CertificateEvent, CertificateTemplate, app, db
    from nodeone.services.certificate_assets import ensure_certificate_assets_for_org
    from nodeone.services.certificate_institutional_pdf import _load_org_layout_defaults
    from nodeone.services.event_certificate_visual_layout import build_institutional_visual_layout
    from sqlalchemy import text

    with app.app_context():
        print('=== migrate emission_snapshot ===')
        db.session.execute(text('ALTER TABLE certificates ADD COLUMN IF NOT EXISTS emission_snapshot TEXT'))
        db.session.commit()

        print('=== layout assets ===')
        _ensure_layout_assets()
        if not os.path.isfile(LAYOUT_SRC):
            print(f'ERROR: no existe {LAYOUT_SRC}', file=sys.stderr)
            return 1
        with open(LAYOUT_SRC, encoding='utf-8') as f:
            layout = json.load(f)

        # IIUS org 1 uses Relatic example layout file as defaults
        print('=== CertificateTemplate ejemplo Relatic ===')
        name = 'Ejemplo Relatic — institucional'
        tpl = CertificateTemplate.query.filter_by(organization_id=1, name=name).first()
        visual = build_institutional_visual_layout(layout, event_id=0)
        payload = json.dumps(visual, ensure_ascii=False)
        if tpl is None:
            tpl = CertificateTemplate(
                organization_id=1,
                name=name,
                width=1056,
                height=816,
                background_image=None,
                json_layout=payload,
            )
            db.session.add(tpl)
            db.session.flush()
            print(f'  created template #{tpl.id}')
        else:
            tpl.json_layout = payload
            tpl.width = 1056
            tpl.height = 816
            print(f'  updated template #{tpl.id}')

        print('=== CertificateEvent REG/MEM branding Relatic ===')
        for code, label in (('REG', 'Certificado por Registro (ejemplo Relatic)'), ('MEM', 'Certificado de Membresía (ejemplo Relatic)')):
            ev = (
                CertificateEvent.query.filter_by(organization_id=1, code_prefix=code)
                .order_by(CertificateEvent.id.asc())
                .first()
            )
            if ev is None:
                ev = CertificateEvent(
                    organization_id=1,
                    name=label,
                    code_prefix=code,
                    is_active=True,
                    verification_enabled=True,
                )
                db.session.add(ev)
                db.session.flush()
                print(f'  created cert_event {code} #{ev.id}')
            else:
                ev.name = label
                print(f'  update cert_event {code} #{ev.id}')
            ev.institution = layout.get('header_text') or ev.institution
            ev.convenio = layout.get('convenio_text') or ev.convenio
            ev.rector_name = layout.get('signatory_left_name') or ev.rector_name
            ev.academic_director_name = layout.get('signatory_right_name') or ev.academic_director_name
            ev.partner_organization = layout.get('signatory_right_org') or ev.partner_organization
            ev.logo_left_url = layout.get('logo_left_url') or ev.logo_left_url
            ev.logo_right_url = layout.get('logo_right_url') or ev.logo_right_url
            ev.seal_url = layout.get('seal_url') or ev.seal_url
            ev.duration_hours = layout.get('academic_hours') or ev.duration_hours
            ev.template_id = int(tpl.id)
            ev.is_active = True

        db.session.commit()

        print('=== ensure_certificate_assets_for_org(1) ===')
        stats = ensure_certificate_assets_for_org(db, 1, commit=True)
        print('  stats', stats)

        defaults = _load_org_layout_defaults(1)
        print('=== resumen ===')
        print('  layout keys', sorted(defaults.keys())[:8], '...')
        print('  templates', CertificateTemplate.query.filter_by(organization_id=1).count())
        for t in CertificateTemplate.query.filter_by(organization_id=1).order_by(CertificateTemplate.id):
            n_el = 0
            try:
                n_el = len((json.loads(t.json_layout or '{}') or {}).get('elements') or [])
            except Exception:
                pass
            print(f'    #{t.id} {t.name!r} elements={n_el}')
        for e in CertificateEvent.query.filter_by(organization_id=1).order_by(CertificateEvent.id):
            print(f'    event #{e.id} {e.code_prefix} {e.name!r} template_id={e.template_id} active={e.is_active}')
        print('DONE')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
