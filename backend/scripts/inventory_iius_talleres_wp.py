#!/usr/bin/env python3
"""FASE 1 — Inventario talleres IIUS (solo lectura, sin apply).

Escanea:
  - WP pág. 2006 (/cursos-detalle/): sección «Talleres» si existe
  - WP pág. 2233 (histórica, puede estar en papelera)
  - Apps org 1: programas category=Talleres o slug taller-*

Uso:
  cd /opt/easynodeone/app/backend
  python3 scripts/inventory_iius_talleres_wp.py
  python3 scripts/inventory_iius_talleres_wp.py --org 1 --json

---
CIERRE Apps (2026-05-22) — ids 24–27 publicados con media ②③ OK.

Estado Apps:
  - taller-de-aprendizaje-practico (24), creatividad (26), desarrollo (27), liderazgo (25)
  - catalog_sort_order 1–4 · audit_program_media --published-only --fail-on-error: ok
  - Redirecciones legacy taller-* → taller-de-* activas en /inscripcion/

WP (manual, no push desde Apps):
  - /cursos-detalle/ (2006): bloque Talleres lo arregla el cliente en Elementor
  - Fuente pull lectura: pág. 2233 (papelera)
  - pull_iius_talleres_wp_apps.py --apply: ignorar×4 si ya existen (no re-pull innecesario)
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from html import unescape
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

WP_CURSOS_PAGE_ID = 2006
WP_TALLERES_PAGE_ID = 2233

# FASE 2 propuesta (no se escribe en BD ni WP desde este script)
TALLERES_CANONICAL_SLUGS_PROPOSED: tuple[dict[str, str], ...] = (
    {'position': '1', 'wp_title_hint': 'Aprendizaje Práctico', 'canonical_slug': 'taller-de-aprendizaje-practico'},
    {'position': '2', 'wp_title_hint': 'Creatividad e Innovación', 'canonical_slug': 'taller-de-creatividad-e-innovacion'},
    {'position': '3', 'wp_title_hint': 'Desarrollo Humano', 'canonical_slug': 'taller-de-desarrollo-humano'},
    {'position': '4', 'wp_title_hint': 'Liderazgo y Comunicación', 'canonical_slug': 'taller-de-liderazgo-y-comunicacion'},
)


def _strip_html(s: str) -> str:
    return re.sub(r'\s+', ' ', unescape(re.sub(r'<[^>]+>', ' ', s or ''))).strip()


def _slug_from_url(url: str | None) -> str | None:
    if not url or '/inscripcion/' not in url:
        return None
    return url.split('/inscripcion/')[-1].split('?')[0].strip('/').lower()


def _image_stem(url: str) -> str:
    if not url:
        return ''
    fn = url.rsplit('/', 1)[-1].lower()
    return re.sub(r'\.[a-z0-9]+$', '', fn)


def _scan_section(data: list, section_titles: frozenset[str], end_titles: frozenset[str]) -> list[dict]:
    from nodeone.modules.academic_enrollment.wp_diplomados_sync import _walk_nodes

    flat: list[dict] = []
    _walk_nodes(data, flat)
    in_sec = False
    cards: list[dict] = []
    pending_img: tuple[dict, str] | None = None
    pending_txt: tuple[dict, str] | None = None
    slot = 0

    def flush(btn_node: dict | None, btn_slug: str | None) -> None:
        nonlocal pending_img, pending_txt, slot
        if not in_sec:
            return
        slot += 1
        title = pending_txt[1][:200] if pending_txt else ''
        img_url = pending_img[1] if pending_img else ''
        btn_text = ''
        if btn_node:
            btn_text = ((btn_node.get('settings') or {}).get('text') or '').strip()
        cards.append(
            {
                'position': slot,
                'title_wp': title,
                'slug_button_wp': btn_slug or '',
                'image_wp': img_url,
                'image_stem': _image_stem(img_url),
                'button_label': btn_text,
            }
        )
        pending_img = pending_txt = None

    for node in flat:
        wt = node.get('widgetType') or ''
        st = node.get('settings') or {}
        if wt == 'heading':
            title = (st.get('title') or '').strip()
            if title in section_titles:
                in_sec = True
                slot = 0
                pending_img = pending_txt = None
                continue
            if in_sec and title and (
                title in end_titles
                or title.startswith('Cursos de')
                or title.startswith('Cursos en')
                or 'Diplomado' in title
            ):
                in_sec = False
                continue
        if not in_sec:
            continue
        if wt == 'image':
            url = (st.get('image') or {}).get('url') or ''
            if url and 'uploads' in url:
                pending_img = (node, url)
        elif wt == 'text-editor':
            plain = _strip_html(st.get('editor') or '')
            if plain and (not pending_txt or len(plain) > len(pending_txt[1])):
                pending_txt = (node, plain)
        elif wt == 'button':
            btn_slug = _slug_from_url((st.get('link') or {}).get('url') or '')
            if btn_slug or pending_img:
                flush(node, btn_slug)
    return cards


def _wp_page_meta(page_id: int) -> dict:
    from nodeone.modules.academic_enrollment.wp_talleres_sync import _run_wp_cli

    title = (_run_wp_cli(['post', 'get', str(page_id), '--field=post_title']).stdout or '').strip()
    slug = (_run_wp_cli(['post', 'get', str(page_id), '--field=post_name']).stdout or '').strip()
    status = (_run_wp_cli(['post', 'get', str(page_id), '--field=post_status']).stdout or '').strip()
    return {'page_id': page_id, 'title': title, 'slug': slug, 'status': status}


def _load_elementor(page_id: int) -> list:
    from nodeone.modules.academic_enrollment.wp_talleres_sync import _run_wp_cli

    proc = _run_wp_cli(['post', 'meta', 'get', str(page_id), '_elementor_data'])
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr or proc.stdout or 'wp-cli falló')
    raw = (proc.stdout or '').strip()
    if not raw or raw == '[]':
        return []
    return json.loads(raw)


def _apps_lookup(organization_id: int) -> dict[str, object]:
    from models.academic_program import AcademicProgram

    return {
        (p.slug or '').strip().lower(): p
        for p in AcademicProgram.query.filter_by(organization_id=int(organization_id)).all()
    }


def _enrich_row(row: dict, apps: dict, proposed_by_pos: dict[int, str]) -> dict:
    slug_wp = (row.get('slug_button_wp') or '').strip().lower()
    p = apps.get(slug_wp) if slug_wp else None
    pos = int(row['position'])
    proposed = proposed_by_pos.get(pos, '')
    p_prop = apps.get(proposed) if proposed else None
    return {
        **row,
        'exists_in_apps': 'sí' if p else 'no',
        'apps_id': getattr(p, 'id', None) if p else None,
        'apps_status': (getattr(p, 'status', None) or '') if p else '',
        'apps_category': (getattr(p, 'category', None) or '') if p else '',
        'apps_program_type': (getattr(p, 'program_type', None) or '') if p else '',
        'canonical_slug_recommended': proposed,
        'apps_has_canonical': 'sí' if p_prop else 'no',
    }


def run_inventory(organization_id: int = 1) -> dict:
    from app import create_app

    app = create_app()
    with app.app_context():
        apps = _apps_lookup(organization_id)
        proposed_by_pos = {
            int(x['position']): x['canonical_slug'] for x in TALLERES_CANONICAL_SLUGS_PROPOSED
        }

        meta_2006 = _wp_page_meta(WP_CURSOS_PAGE_ID)
        data_2006 = _load_elementor(WP_CURSOS_PAGE_ID)
        arte_live = _scan_section(
            data_2006,
            frozenset({'Cursos de Arte', 'Cursos en Arte'}),
            frozenset({'Talleres', 'Catálogo de Cursos'}),
        )
        talleres_live = _scan_section(
            data_2006,
            frozenset({'Talleres'}),
            frozenset({'Catálogo de Cursos', 'Cursos de Negocios', 'Cursos en Arte'}),
        )

        meta_2233: dict = {'page_id': WP_TALLERES_PAGE_ID, 'status': 'missing'}
        talleres_2233: list[dict] = []
        try:
            meta_2233 = _wp_page_meta(WP_TALLERES_PAGE_ID)
            if meta_2233.get('status') != 'trash' or _load_elementor(WP_TALLERES_PAGE_ID):
                data_2233 = _load_elementor(WP_TALLERES_PAGE_ID)
                talleres_2233 = _scan_section(
                    data_2233,
                    frozenset({'Talleres', 'Catálogo de Talleres'}),
                    frozenset({'Cursos de Negocios', 'Cursos en Ciencia'}),
                )
        except Exception as e:
            meta_2233['error'] = str(e)

        rows_2233 = [_enrich_row(r, apps, proposed_by_pos) for r in talleres_2233]
        rows_live = [_enrich_row(r, apps, proposed_by_pos) for r in talleres_live]

        apps_talleres = [
            {
                'id': p.id,
                'slug': p.slug,
                'status': p.status,
                'program_type': p.program_type,
                'category': p.category,
                'name': p.name,
            }
            for p in apps.values()
            if (getattr(p, 'category', None) or '') == 'Talleres'
            or (getattr(p, 'slug', None) or '').startswith('taller-')
            or (getattr(p, 'program_type', None) or '') == 'taller'
        ]

        return {
            'organization_id': organization_id,
            'wp_page_cursos_detalle': meta_2006,
            'wp_page_talleres_legacy': meta_2233,
            'cursos_de_arte_on_2006_count': len(arte_live),
            'talleres_section_on_2006_count': len(talleres_live),
            'talleres_section_on_2006': rows_live,
            'talleres_page_2233': rows_2233,
            'apps_talleres_programs': apps_talleres,
            'canonical_slugs_proposed': list(TALLERES_CANONICAL_SLUGS_PROPOSED),
            'notes': [
                'Apps CERRADO: 4 talleres publicados (taller-de-*, ids 24–27), media ②③ ok, sort 1–4.',
                'WP /cursos-detalle/ (2006): bloque Talleres — arreglo manual Elementor (no push desde Apps).',
                'Pág. 2233: fuente lectura legacy (papelera); slugs taller-* no son canónicos.',
                'pull --apply: ignorar×4 si ya existen; no re-pull sin cambio en WP fuente.',
            ],
        }


def _print_table(rows: list[dict], source: str) -> None:
    print(f'\n=== {source} ({len(rows)} tarjetas) ===')
    if not rows:
        print('(sin tarjetas)')
        return
    hdr = (
        'pos',
        'título WP (recorte)',
        'slug botón WP',
        'imagen (stem)',
        'Apps',
        'slug canónico propuesto',
    )
    print('\t'.join(hdr))
    for r in rows:
        title = (r.get('title_wp') or '').replace('\t', ' ')[:55]
        print(
            f"{r.get('position')}\t{title}\t{r.get('slug_button_wp')}\t"
            f"{r.get('image_stem')}\t{r.get('exists_in_apps')}\t{r.get('canonical_slug_recommended')}"
        )


def main() -> int:
    ap = argparse.ArgumentParser(description='Inventario talleres WP (FASE 1, solo lectura)')
    ap.add_argument('--org', type=int, default=1)
    ap.add_argument('--json', action='store_true')
    args = ap.parse_args()
    report = run_inventory(args.org)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    print('IIUS — Inventario Talleres (FASE 1, sin apply)')
    print('WP 2006:', report['wp_page_cursos_detalle'])
    print('WP 2233:', report['wp_page_talleres_legacy'])
    print('Arte en 2006:', report['cursos_de_arte_on_2006_count'], 'tarjetas')
    _print_table(report['talleres_section_on_2006'], 'Talleres en /cursos-detalle/ (2006)')
    _print_table(report['talleres_page_2233'], 'Talleres página legacy (2233)')
    print('\n--- Apps (talleres / taller-*) ---')
    for p in report['apps_talleres_programs']:
        print(p)
    if not report['apps_talleres_programs']:
        print('(ninguno)')
    print('\nNotas:')
    for n in report['notes']:
        print('-', n)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
