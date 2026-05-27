#!/usr/bin/env python3
"""FASE 1 — Inventario eventos IIUS (solo lectura, sin apply).

Escanea:
  - WP: plugin Event Manager (event_listing), páginas Elementor «Eventos»
  - Apps: tabla ``event`` (org del tenant)

Uso:
  cd /opt/easynodeone/app/backend
  python3 scripts/inventory_iius_events_wp.py
  python3 scripts/inventory_iius_events_wp.py --org 1 --json

---
CIERRE FASE 1 (2026-05-22) — no hay eventos que sincronizar.

Estado acordado:
  - /eventos/ (pág. 210) = landing pública canónica → CTA https://apps.internationalinstitute.us/events
  - /events (Apps) = catálogo vacío hasta que el cliente entregue eventos reales
  - /eventos-2/ (pág. 2262) = limpiar manualmente en WP (despublicar, papelera o redir. a /eventos/)

Prohibido:
  - pull/apply de eventos desde inventario actual
  - migrar las 8 tarjetas de /eventos-2/ (son cursos /inscripcion/, no eventos)
  - reutilizar slugs curso-* para eventos

FASE 2+ (solo cuando existan eventos reales con título, fechas, modalidad, precio,
cupos, flyer y descripción):
  - módulo/script WP↔Apps separado de cursos/talleres
  - slugs canónicos: evento-<nombre-corto>
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from html import unescape
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

WP_ROOT = '/var/www/wordpress'
WP_CLI = 'wp'
APPS_EVENTS_BASE = 'https://apps.internationalinstitute.us/events'

# Páginas WP conocidas relacionadas con eventos (solo lectura).
WP_EVENT_PAGES: tuple[tuple[int, str], ...] = (
    (210, '/eventos/ (landing → Apps)'),
    (2262, '/eventos-2/ (página publicada «Eventos»)'),
    (2084, '/talleres/ obsoleta (papelera)'),
)


def _wp(*args: str) -> tuple[str, int]:
    proc = subprocess.run(
        ['sudo', '-u', 'www-data', WP_CLI, *args, f'--path={WP_ROOT}'],
        capture_output=True,
        text=True,
        env={'WP_CLI_CACHE_DIR': '/var/www/.wp-cli/cache'},
    )
    return (proc.stdout or proc.stderr or '').strip(), proc.returncode


def _strip_html(s: str) -> str:
    return re.sub(r'\s+', ' ', unescape(re.sub(r'<[^>]+>', ' ', s or ''))).strip()


def _load_elementor(page_id: int) -> list | None:
    out, rc = _wp('post', 'meta', 'get', str(page_id), '_elementor_data')
    if rc != 0 or not out or out == '[]':
        return None
    return json.loads(out)


def _walk_nodes(data: list) -> list[dict]:
    flat: list[dict] = []

    def walk(o):
        if isinstance(o, dict):
            flat.append(o)
            for c in o.get('elements') or []:
                walk(c)
        elif isinstance(o, list):
            for x in o:
                walk(x)

    walk(data)
    return flat


def _slug_from_url(url: str | None) -> str:
    if not url:
        return ''
    u = (url or '').strip().rstrip('\\')
    if '/events/' in u:
        return u.split('/events/')[-1].split('?')[0].strip('/').lower()
    if '/inscripcion/' in u:
        return u.split('/inscripcion/')[-1].split('?')[0].strip('/').lower()
    return ''


def _scan_wp_event_pages() -> list[dict]:
    """Tarjetas/botones en páginas Elementor «Eventos» (puede incluir cursos mal colocados)."""
    rows: list[dict] = []
    pos = 0
    for page_id, page_note in WP_EVENT_PAGES:
        meta, rc = _wp(
            'post',
            'get',
            str(page_id),
            '--fields=post_title,post_name,post_status',
            '--format=json',
        )
        if rc != 0:
            continue
        try:
            page_meta = json.loads(meta)
        except json.JSONDecodeError:
            page_meta = {}
        data = _load_elementor(page_id)
        if not data:
            # Landing sin tarjetas individuales
            rows.append(
                {
                    'position': '—',
                    'source': f'WP pág. {page_id}',
                    'title_wp': page_meta.get('post_title') or page_note,
                    'slug_button_wp': '',
                    'fecha_wp': '',
                    'image_wp': '',
                    'button_url': APPS_EVENTS_BASE if page_id in (210, 2084) else '',
                    'page_slug': page_meta.get('post_name') or '',
                    'page_status': page_meta.get('post_status') or '',
                    'nota': page_note,
                    'is_event_card': False,
                }
            )
            continue

        flat = _walk_nodes(data)
        pending_title = ''
        pending_img = ''
        in_eventos_section = False
        for node in flat:
            wt = node.get('widgetType') or ''
            st = node.get('settings') or {}
            if wt == 'heading':
                t = (st.get('title') or '').strip()
                if t:
                    pending_title = t
                    if 'evento' in t.lower():
                        in_eventos_section = True
            elif wt == 'image':
                url = (st.get('image') or {}).get('url') or ''
                if url:
                    pending_img = url
            elif wt == 'button':
                btn_url = ((st.get('link') or {}).get('url') or '').strip().rstrip('\\')
                if not btn_url and not pending_img:
                    continue
                pos += 1
                slug_btn = _slug_from_url(btn_url)
                is_event = '/events/' in btn_url.lower() and slug_btn
                is_course = '/inscripcion/' in btn_url.lower()
                rows.append(
                    {
                        'position': pos,
                        'source': f'WP pág. {page_id} ({page_meta.get("post_name", "")})',
                        'title_wp': pending_title or page_meta.get('post_title') or '—',
                        'slug_button_wp': slug_btn or '—',
                        'fecha_wp': '',
                        'image_wp': pending_img[:120] if pending_img else '',
                        'button_url': btn_url,
                        'page_slug': page_meta.get('post_name') or '',
                        'page_status': page_meta.get('post_status') or '',
                        'nota': (
                            'CTA catálogo cursos (no evento)'
                            if is_course
                            else ('enlace evento Apps' if is_event else 'CTA genérico /events')
                        ),
                        'is_event_card': bool(is_event),
                    }
                )
                pending_title = pending_img = ''
    return rows


def _scan_wp_event_manager() -> list[dict]:
    out, rc = _wp(
        'post',
        'list',
        '--post_type=event_listing',
        '--post_status=any',
        '--fields=ID,post_title,post_name,post_status',
        '--format=json',
    )
    if rc != 0 or not out:
        return []
    listings = json.loads(out)
    rows: list[dict] = []
    for i, ev in enumerate(listings, 1):
        eid = ev['ID']
        start, _ = _wp('post', 'meta', 'get', str(eid), '_event_start_date')
        end, _ = _wp('post', 'meta', 'get', str(eid), '_event_end_date')
        thumb, _ = _wp('post', 'meta', 'get', str(eid), '_thumbnail_id')
        img = ''
        if thumb:
            img, _ = _wp('post', 'meta', 'get', thumb, '_wp_attached_file')
        rows.append(
            {
                'position': i,
                'source': 'WP Event Manager',
                'title_wp': ev.get('post_title') or '',
                'slug_button_wp': (ev.get('post_name') or '').strip(),
                'fecha_wp': f'{start} → {end}'.strip(' → ') if start or end else '',
                'image_wp': img[:120] if img else '',
                'button_url': f'https://internationalinstitute.us/eventos/{ev.get("post_name", "")}/',
                'page_slug': '',
                'page_status': ev.get('post_status') or '',
                'nota': 'Plugin wp-event-manager',
                'is_event_card': True,
            }
        )
    return rows


def _apps_events(organization_id: int) -> list[dict]:
    from app import create_app

    app = create_app()
    with app.app_context():
        from app import Event
        from nodeone.services.events_portal import portal_events_scoped_query

        scoped = portal_events_scoped_query(organization_id=organization_id)
        scoped_ids = {e.id for e in scoped.all()}
        all_rows = Event.query.order_by(Event.start_date.desc().nulls_last(), Event.id.asc()).all()
        out: list[dict] = []
        for e in all_rows:
            in_org = e.id in scoped_ids
            out.append(
                {
                    'id': e.id,
                    'slug': (e.slug or '').strip(),
                    'title': (e.title or '').strip(),
                    'publish_status': (e.publish_status or 'draft'),
                    'start_date': e.start_date.isoformat() if e.start_date else '',
                    'end_date': e.end_date.isoformat() if e.end_date else '',
                    'cover_image': (e.cover_image or '')[:120],
                    'base_price': float(e.base_price or 0),
                    'capacity': int(e.capacity or 0),
                    'visibility': (e.visibility or ''),
                    'format': (e.format or ''),
                    'in_org_scope': in_org,
                    'apps_url': f'{APPS_EVENTS_BASE}/{(e.slug or "").strip()}',
                }
            )
        return out


def _suggested_action(
    wp_row: dict,
    apps_by_slug: dict[str, dict],
) -> str:
    slug_wp = (wp_row.get('slug_button_wp') or '').strip().lower()
    if wp_row.get('nota', '').startswith('CTA catálogo cursos'):
        return 'D — no es evento; revisar página WP manualmente (catálogo cursos en Eventos)'
    if not wp_row.get('is_event_card') and not slug_wp:
        return 'C — solo CTA genérico a /events (Apps); sin tarjeta de evento'
    apps = apps_by_slug.get(slug_wp)
    if apps:
        if apps.get('publish_status') == 'published':
            return 'B — actualizar enlace/metadatos si difiere de Apps'
        return 'B — existe en Apps (borrador); completar y publicar'
    if slug_wp and wp_row.get('is_event_card'):
        return 'A — crear evento nuevo en Apps con slug canónico'
    return 'revisar manualmente'


def run_inventory(organization_id: int = 1) -> dict:
    wp_plugin = _scan_wp_event_manager()
    wp_pages = _scan_wp_event_pages()
    wp_rows = wp_plugin + wp_pages
    apps_rows = _apps_events(organization_id)
    apps_by_slug = {r['slug'].lower(): r for r in apps_rows if r.get('slug')}

    table: list[dict] = []
    for wp in wp_rows:
        slug_wp = (wp.get('slug_button_wp') or '').strip().lower()
        apps = apps_by_slug.get(slug_wp) if slug_wp and slug_wp != '—' else None
        table.append(
            {
                'position': wp.get('position'),
                'title_wp': wp.get('title_wp'),
                'slug_button_wp': wp.get('slug_button_wp') or '—',
                'fecha_wp': wp.get('fecha_wp') or '—',
                'image_wp': wp.get('image_wp') or '—',
                'button_url': wp.get('button_url') or '—',
                'existe_en_apps': 'sí' if apps else 'no',
                'slug_apps': apps.get('slug') if apps else '—',
                'estado_apps': apps.get('publish_status') if apps else '—',
                'accion_sugerida': _suggested_action(wp, apps_by_slug),
                'source': wp.get('source'),
                'nota': wp.get('nota'),
            }
        )

    for apps in apps_rows:
        if apps['slug'].lower() not in {(r.get('slug_button_wp') or '').lower() for r in wp_rows}:
            table.append(
                {
                    'position': '—',
                    'title_wp': f'(solo Apps) {apps["title"]}',
                    'slug_button_wp': '—',
                    'fecha_wp': f'{apps["start_date"]} → {apps["end_date"]}',
                    'image_wp': apps.get('cover_image') or '—',
                    'button_url': apps.get('apps_url'),
                    'existe_en_apps': 'sí',
                    'slug_apps': apps['slug'],
                    'estado_apps': apps['publish_status'],
                    'accion_sugerida': 'B — Apps sin tarjeta WP; decidir push/enlace manual',
                    'source': 'Apps',
                    'nota': 'in_org' if apps.get('in_org_scope') else 'fuera de org scope',
                }
            )

    return {
        'organization_id': organization_id,
        'wp_event_manager_count': len(wp_plugin),
        'wp_page_cards_count': len(wp_pages),
        'apps_events_count': len(apps_rows),
        'apps_events_in_org_scope': sum(1 for a in apps_rows if a.get('in_org_scope')),
        'public_block_wp': (
            'Pág. 210 /eventos/: landing Elementor con CTA a Apps /events (sin listado por evento). '
            'Pág. 2262 /eventos-2/: publicada pero contiene tarjetas de cursos (/inscripcion/), no eventos. '
            'Plugin wp-event-manager activo sin event_listing.'
        ),
        'apps_public': f'{APPS_EVENTS_BASE} (listado vacío si no hay event published en org)',
        'rows': table,
        'apps_detail': apps_rows,
        'notes': [
            'FASE 1 CERRADA: no hay eventos que sincronizar; no pull/apply.',
            '/eventos/ canónica → Apps /events; /eventos-2/ limpiar manualmente en WP.',
            'No migrar tarjetas curso-* de /eventos-2/; slugs futuros: evento-<nombre-corto>.',
            'Apps org 1: modelo Event (publish_status, start_date, end_date, cover_image, capacity, base_price).',
            'No existe event_type ni registration_enabled en ORM; usar format, visibility, publish_status.',
            'Crear eventos en Apps solo cuando el cliente entregue datos reales.',
        ],
    }


def _print_table(report: dict) -> None:
    print('=' * 110)
    print('FASE 1 — Inventario eventos (solo lectura, sin apply)')
    print('=' * 110)
    print(f"Org {report['organization_id']} · WP Event Manager: {report['wp_event_manager_count']} · "
          f"tarjetas/botones en páginas Eventos: {report['wp_page_cards_count']} · "
          f"Apps: {report['apps_events_count']} (en org: {report['apps_events_in_org_scope']})")
    print()
    print(report['public_block_wp'])
    print(report['apps_public'])
    print()
    hdr = (
        'pos',
        'título WP',
        'slug/botón WP',
        'fecha WP',
        'imagen WP (recorte)',
        'Apps',
        'slug Apps',
        'estado Apps',
        'acción sugerida',
    )
    print('\t'.join(hdr))
    for r in report.get('rows') or []:
        img = (r.get('image_wp') or '—')[:50]
        title = (r.get('title_wp') or '—')[:40]
        print(
            f"{r.get('position')}\t{title}\t{r.get('slug_button_wp')}\t{r.get('fecha_wp')}\t"
            f"{img}\t{r.get('existe_en_apps')}\t{r.get('slug_apps')}\t{r.get('estado_apps')}\t"
            f"{(r.get('accion_sugerida') or '')[:55]}"
        )
    print()
    for n in report.get('notes') or []:
        print('-', n)
    print('=' * 110)


def main() -> int:
    ap = argparse.ArgumentParser(description='Inventario eventos WP ↔ Apps (FASE 1)')
    ap.add_argument('--org', type=int, default=1)
    ap.add_argument('--json', action='store_true')
    args = ap.parse_args()
    report = run_inventory(args.org)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        _print_table(report)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
