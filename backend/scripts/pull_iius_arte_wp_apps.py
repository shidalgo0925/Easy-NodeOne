#!/usr/bin/env python3
"""
Pull selectivo WordPress → Apps: solo 4 títulos «Cursos de Arte» (pág. 2006).

Por defecto: DRY-RUN (tabla de revisión, sin cambios en BD).
  --apply     Persistir crear/actualizar (solo tras revisar la tabla)
  --org ID    organization_id (default 1)

Protegido: image_url, flyer_url, price_from, status, planes.
Permitido: name, slug (solo al crear), category, short_description, image_wp_landing.
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _fmt_fields(d: dict) -> str:
    if not d:
        return '—'
    parts = []
    for k, v in sorted(d.items()):
        if k.startswith('_'):
            if k == '_create_status':
                parts.append(f'status→{v}')
            continue
        sv = str(v)
        if len(sv) > 48:
            sv = sv[:45] + '…'
        parts.append(f'{k}={sv!r}')
    return '; '.join(parts) or '—'


def _print_table(report: dict) -> None:
    print('=' * 100)
    print('DRY-RUN — Pull WP → Apps (solo Cursos de Arte, 4 títulos canónicos)')
    print('=' * 100)
    print(f"Org {report.get('organization_id')} · WP página {report.get('wp_page_id')}")
    print(f"Tarjetas WP detectadas en sección Arte: {report.get('wp_cards_found')} / 4")
    print()
    hdr = (
        'título WP',
        'slug WP',
        'Apps',
        'slug Apps',
        'acción',
        'campos a actualizar',
        'protegidos',
    )
    print('\t'.join(hdr))
    for r in report.get('rows') or []:
        print(
            '\t'.join(
                [
                    (r.get('wp_title') or '')[:55],
                    r.get('slug_wp') or '—',
                    r.get('existe_en_apps') or '?',
                    r.get('slug_apps_relacionado') or '—',
                    r.get('accion_propuesta') or '—',
                    _fmt_fields(r.get('campos_actualizar') or {}),
                    ','.join(r.get('campos_protegidos') or []),
                ]
            )
        )
    errs = report.get('errors') or []
    if errs:
        print('\nAvisos:')
        for e in errs:
            print(f'  · {e}')
    print()
    for r in report.get('rows') or []:
        if r.get('nota'):
            print(f"  Nota [{r.get('canonical_slug') or r.get('slug_apps_relacionado')}]: {r['nota']}")
    if report.get('dry_run', True):
        print(
            f"Resumen: crear={report.get('would_create', 0)} · "
            f"actualizar={report.get('would_update', 0)} · "
            f"legacy/revisar={report.get('would_legacy', sum(1 for x in report.get('rows', []) if x.get('accion_propuesta') == 'legacy/revisar'))} · "
            f"ignorar={sum(1 for x in report.get('rows', []) if x.get('accion_propuesta') == 'ignorar')}"
        )
        print('NO se aplicaron cambios. Revisar tabla y luego usar --apply si corresponde.')
    else:
        print(f"Aplicado: creados={report.get('created', 0)} · actualizados={report.get('updated', 0)}")
    print('=' * 100)


def main() -> int:
    parser = argparse.ArgumentParser(description='Pull seguro Cursos de Arte (4 títulos)')
    parser.add_argument('--org', type=int, default=1)
    parser.add_argument('--apply', action='store_true', help='Escribir BD (solo tras revisar dry-run)')
    args = parser.parse_args()

    from app import app, db
    from nodeone.modules.academic_enrollment.wp_talleres_sync import apply_arte_wp_title_pull

    with app.app_context():
        _n, errors, report = apply_arte_wp_title_pull(int(args.org), db, dry_run=not args.apply)
        _print_table(report)

        if not args.apply:
            print('\n(audit opcional post dry-run)')
        print('\n--- audit_program_media.py --published-only ---')
        import subprocess

        audit = subprocess.run(
            [
                sys.executable,
                os.path.join(os.path.dirname(__file__), 'audit_program_media.py'),
                str(args.org),
                '--published-only',
            ],
            cwd=os.path.dirname(os.path.dirname(__file__)),
            capture_output=True,
            text=True,
        )
        print(audit.stdout)
        if audit.stderr:
            print(audit.stderr, file=sys.stderr)

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
