#!/usr/bin/env python3
"""
Pull selectivo WordPress → Apps: sección Talleres (fuente WP 2233, 4 posiciones).

Por defecto: DRY-RUN.
  --apply     Persistir crear/actualizar (borrador)
  --push-wp   Publicar botones en WP solo si el bloque Talleres ya existe en 2006 (no crea bloque)
  --org ID    organization_id (default 1)

Protegido: image_url, flyer_url, price_from, status, planes.
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
            continue
        sv = str(v)
        if len(sv) > 48:
            sv = sv[:45] + '…'
        parts.append(f'{k}={sv!r}')
    return '; '.join(parts) or '—'


def _print_table(report: dict) -> None:
    print('=' * 100)
    print('Pull WP → Apps — Talleres (4 posiciones, catálogo por título)')
    print('=' * 100)
    print(
        f"Org {report.get('organization_id')} · fuente WP {report.get('wp_source_page_id')} · "
        f"push WP {report.get('wp_push_page_id')} · tarjetas fuente {report.get('wp_cards_found')}/4 · "
        f"tarjetas en 2006 {report.get('wp_push_cards_found')}/4"
    )
    print()
    for r in report.get('rows') or []:
        print(
            f"{r.get('position')}\t{(r.get('wp_title') or '')[:40]}\t{r.get('slug_wp') or '—'}\t"
            f"{r.get('canonical_slug')}\t{r.get('existe_en_apps')}\t{r.get('accion_propuesta')}\t"
            f"{_fmt_fields(r.get('campos_actualizar') or {})}"
        )
    for e in report.get('errors') or []:
        print(f'  · {e}')
    if report.get('dry_run', True):
        print(
            f"\nResumen: crear={report.get('would_create', 0)} · "
            f"actualizar={report.get('would_update', 0)} · "
            f"ignorar={sum(1 for x in report.get('rows', []) if x.get('accion_propuesta') == 'ignorar')}"
        )
        print('NO se aplicaron cambios. Usar --apply tras revisar.')
    else:
        print(f"\nAplicado: creados={report.get('created', 0)} · actualizados={report.get('updated', 0)}")
    print('=' * 100)


def main() -> int:
    parser = argparse.ArgumentParser(description='Pull seguro Talleres IIUS')
    parser.add_argument('--org', type=int, default=1)
    parser.add_argument('--apply', action='store_true')
    parser.add_argument(
        '--ensure-wp',
        action='store_true',
        help='(deshabilitado) No modifica WP; solo muestra aviso de política',
    )
    parser.add_argument(
        '--push-wp',
        action='store_true',
        help='Actualiza botones solo en bloque Talleres ya existente en 2006',
    )
    args = parser.parse_args()

    from app import app, db

    with app.app_context():
        if args.ensure_wp:
            from nodeone.modules.academic_enrollment.wp_talleres_catalog_sync import (
                ensure_talleres_block_on_cursos_page,
            )

            _, msg = ensure_talleres_block_on_cursos_page(save=False)
            print(msg)

        from nodeone.modules.academic_enrollment.wp_talleres_catalog_sync import (
            apply_talleres_wp_title_pull,
        )

        _n, errors, report = apply_talleres_wp_title_pull(int(args.org), db, dry_run=not args.apply)
        _print_table(report)

        if args.push_wp and args.apply:
            from nodeone.modules.academic_enrollment.wp_talleres_catalog_sync import (
                WP_TALLERES_PUSH_SLUGS,
                push_talleres_slug_to_wp,
            )

            for slug in sorted(WP_TALLERES_PUSH_SLUGS):
                ok, err = push_talleres_slug_to_wp(int(args.org), slug)
                print(slug, 'OK' if ok else f'FAIL: {err}')

        if errors:
            print('\nErrores:', *errors[:10], sep='\n  ')

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
