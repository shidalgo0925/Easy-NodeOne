#!/usr/bin/env python3
"""FASE 2 — Inventario eventos por sección (/eventos-2/, solo lectura).

Separa Eventos_Profesionales y Eventos_Personales; propone slugs evento-profesional-* /
evento-personal-* (no reutiliza curso-*).

Uso:
  cd /opt/easynodeone/app/backend
  python3 scripts/inventory_iius_events_sections_wp.py
  python3 scripts/inventory_iius_events_sections_wp.py --json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def _print_table(report: dict) -> None:
    print('=' * 120)
    print('FASE 2 — Inventario eventos por sección (solo lectura, sin apply)')
    print('=' * 120)
    print(
        f"WP pág. {report.get('wp_page_id')} /{report.get('wp_page_slug')}/ · "
        f"tarjetas {report.get('cards_found')}/{report.get('catalog_count')}"
    )
    print()
    hdr = (
        'sección',
        'pos',
        'título visible (recorte)',
        'imagen (archivo)',
        'slug viejo botón',
        'slug evento propuesto',
        'event_type',
    )
    print('\t'.join(hdr))
    for r in report.get('rows') or []:
        title = (r.get('title_visible') or '—').replace('\t', ' ')[:55]
        img = (r.get('image') or '—').rsplit('/', 1)[-1][:40]
        print(
            f"{r.get('section')}\t{r.get('position')}\t{title}\t{img}\t"
            f"{r.get('slug_old_button')}\t{r.get('slug_evento_propuesto')}\t{r.get('event_type')}"
        )
    for e in report.get('errors') or []:
        print(f'  · {e}')
    print()
    print('- NO apply · NO publicar · slugs canónicos evento-profesional-* / evento-personal-*')
    print('- FASE 3: pull_iius_events_wp_apps.py (dry-run por defecto)')
    print('=' * 120)


def main() -> int:
    ap = argparse.ArgumentParser(description='Inventario eventos WP por sección (FASE 2)')
    ap.add_argument('--json', action='store_true')
    args = ap.parse_args()

    from nodeone.modules.events.wp_events_catalog_sync import run_events_section_inventory

    report = run_events_section_inventory()
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        _print_table(report)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
