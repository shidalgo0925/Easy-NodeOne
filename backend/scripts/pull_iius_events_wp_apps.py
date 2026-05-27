#!/usr/bin/env python3
"""
Pull selectivo WordPress → Apps: eventos /eventos-2/ (8 tarjetas, 2 secciones).

Por defecto: DRY-RUN (FASE 3).
  --apply     Crear borradores en Apps (publish_status=draft, fechas placeholder)
  --org ID    organization_id (default 1)

Protegido en pull: publish_status, fechas reales, cover_image local, precio, cupos, modalidad.
NO publica · NO toca cursos/talleres/arte · NO reutiliza slugs curso-*.

---
FASE 3 CERRADA (--apply ejecutado): 8 draft, 0 published, 0 push WP.
FASE 4 manual en admin. NO pull/push/publish/sync hasta 8 eventos completos y publicados.
FASE 5: push WP dry-run → revisar mapping → apply → validar enlaces (solo tras FASE 4).
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
        if len(sv) > 40:
            sv = sv[:37] + '…'
        parts.append(f'{k}={sv!r}')
    return '; '.join(parts) or '—'


def _print_table(report: dict) -> None:
    print('=' * 110)
    print('Pull WP → Apps — Eventos (FASE 3, borradores draft)')
    print('=' * 110)
    print(f"Org {report.get('organization_id')} · WP {report.get('wp_page_id')} · mode={'dry_run' if report.get('dry_run', True) else 'apply'}")
    print()
    for r in report.get('rows') or []:
        print(
            f"{r.get('section')}\t{r.get('position')}\t{(r.get('title_short') or '')[:35]}\t"
            f"{r.get('slug_proposed')}\t{r.get('existe_en_apps')}\t{r.get('accion_propuesta')}\t"
            f"{_fmt_fields(r.get('campos_actualizar') or {})}"
        )
    for e in report.get('errors') or []:
        print(f'  · {e}')
    if report.get('dry_run', True):
        print(f"\nResumen: crear={report.get('would_create', 0)} · actualizar={report.get('would_update', 0)}")
        print('NO se aplicaron cambios. Usar --apply tras revisar FASE 2.')
    else:
        print(f"\nAplicado: creados={report.get('created', 0)}")
    print('=' * 110)


def main() -> int:
    parser = argparse.ArgumentParser(description='Pull seguro eventos IIUS (FASE 3)')
    parser.add_argument('--org', type=int, default=1)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()

    from app import app, db
    from nodeone.modules.events.wp_events_catalog_sync import apply_events_wp_pull

    with app.app_context():
        _n, errors, report = apply_events_wp_pull(int(args.org), db, dry_run=not args.apply)
        _print_table(report)
        if errors:
            print('\nErrores:', *errors[:12], sep='\n  ')

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
