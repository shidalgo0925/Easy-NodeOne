#!/usr/bin/env python3
"""Actualiza enlaces «Ver más» en WordPress (Elementor) → checkout apps IIUS.

Uso (en servidor con WP en /var/www/wordpress):
  python3 scripts/apply_iius_wp_ver_mas_checkout.py --dry-run
  python3 scripts/apply_iius_wp_ver_mas_checkout.py --apply

Mapeo imagen → slug: backend/data/iius_wp_media_urls.json
URLs checkout: /checkout/programa/<slug>/full (plan contado por defecto).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
WP_ROOT = Path(os.environ.get('IIUS_WP_ROOT', '/var/www/wordpress'))
MEDIA_MAP_PATH = BACKEND / 'data' / 'iius_wp_media_urls.json'
APPS_BASE = os.environ.get('IIUS_APPS_BASE', 'https://apps.internationalinstitute.us').rstrip('/')

# Páginas Elementor del catálogo marketing IIUS
WP_PAGE_IDS = (
    2006,  # cursos-detalle
    2233,  # talleres-2
    214,   # entrenamientos
    212,   # diplomados disponibles
    1929,  # entrenamientos-copia-1 / diplomados
)

OLD_PREFIXES = (
    f'{APPS_BASE}/programs/',
    f'{APPS_BASE}/inscripcion/',
    'https://internationalinstitute.us/diplomados/',
    'https://internationalinstitute.us/diplomados',
)


def _checkout_url(slug: str, plan: str = 'full') -> str:
    return f'{APPS_BASE}/checkout/programa/{slug.strip().lower()}/{plan.strip().lower()}'


def _load_image_to_slug() -> dict[str, str]:
    data = json.loads(MEDIA_MAP_PATH.read_text(encoding='utf-8'))
    out: dict[str, str] = {}
    for slug, url in (data.get('programs') or {}).items():
        fname = (url or '').rsplit('/', 1)[-1].lower()
        if fname:
            out[fname] = slug
        # claves parciales (sin extensión / typos WP)
        stem = re.sub(r'\.[a-z0-9]+$', '', fname, flags=re.I)
        if stem:
            out[stem] = slug
    # alias archivos en elementor cursos-detalle
    out['liderasgo-de-gestion-de-equipo'] = 'curso-en-liderazgo-y-gestion-de-equipos'
    out['desarrollo-de-negocio'] = 'cursos-en-emprendimiento-y-desarrollo-de-negocios'
    # Misma imagen WP para curso de negocios y taller; prioridad curso en cursos-detalle
    out['liderasgo-organizacional.png'] = 'curso-en-coaching-ejecutivo-y-liderazgo-organizacional'
    out['liderasgo-organizacional'] = 'curso-en-coaching-ejecutivo-y-liderazgo-organizacional'
    out['coaching-prof'] = 'curso-en-coaching-profesional-integral'
    out['ancalje'] = 'curso-tecnicas-anclaje-pnl'
    out['ieyb'] = 'curso-en-inteligencia-emocional-y-bienestar'
    out['pnl.png'] = 'curso-en-neuroeducacion-y-programacion-neurolinguistica-pnl'
    out['talleres.png'] = 'taller-aprendizaje-practico'
    out['creatividadvak'] = 'diplomado-en-creatividad-y-expresion-artistica-aplicada'
    out['eldr.jpeg'] = 'taller-desarrollo-humano'
    out['neuro-liderazgo-intercultural2'] = 'neuro-liderazgo-intercultural'
    out['neuro-decodificacion'] = 'neuro-descodificacion-psicogenealogia-pnl'
    out['nuero-liderazgo'] = 'neuro-liderazgo-intercultural'
    out['nuero-heuristica'] = 'neuro-heuristica-coaching-vida'
    out['neuro-teologia'] = 'neuro-teologia-coaching-cristiano-transgeneracional'
    out['diplomado_internacional_de_neuro-teologia'] = 'neuro-teologia-coaching-cristiano-transgeneracional'
    out['neuro-heuristica'] = 'neuro-heuristica-coaching-vida'
    # Talleres (página WP usa imágenes ChatGPT mayo 2026, orden del bloque)
    out['chatgpt-image-19-may-2026-21_51_22'] = 'taller-aprendizaje-practico'
    out['chatgpt-image-19-may-2026-22_01_31'] = 'taller-liderazgo-y-comunicacion'
    out['chatgpt-image-19-may-2026-21_55_28'] = 'diplomado-en-creatividad-y-expresion-artistica-aplicada'
    out['chatgpt-image-19-may-2026-21_57_45'] = 'taller-desarrollo-humano'
    return out


def _slug_from_url(url: str, image_map: dict[str, str]) -> str | None:
    if not url:
        return None
    low = url.lower()
    # Coincidencia por nombre de archivo (más fiable que substring suelta)
    fname = low.rsplit('/', 1)[-1]
    if fname in image_map:
        return image_map[fname]
    stem = re.sub(r'\.[a-z0-9]+$', '', fname, flags=re.I)
    if stem in image_map:
        return image_map[stem]
    for key, slug in sorted(image_map.items(), key=lambda x: -len(x[0])):
        if key in low:
            return slug
    m = re.search(r'/programs/([a-z0-9-]+)', low)
    if m:
        return m.group(1)
    m = re.search(r'(?:^|/)inscripcion/([a-z0-9-]+)', low)
    if m:
        return m.group(1)
    m = re.search(r'/checkout/programa/([a-z0-9-]+)/', low)
    if m:
        return m.group(1)
    return None


def _is_payment_link(url: str) -> bool:
    if not url or not isinstance(url, str):
        return False
    low = url.lower()
    if any(low.startswith(p.lower()) or p.lower() in low for p in OLD_PREFIXES):
        return True
    if '/checkout/programa/' in low:
        return True
    if low.startswith('/inscripcion/') or '/inscripcion/' in low:
        return True
    return False


def _replace_inscripcion_strings(node, image_map: dict[str, str]) -> int:
    """Sustituye URLs /inscripcion/<slug> embebidas en cualquier string del JSON."""
    changes = 0
    if isinstance(node, dict):
        for k, v in list(node.items()):
            if isinstance(v, str) and '/inscripcion/' in v:
                slug = _slug_from_url(v, image_map)
                if slug:
                    new = _checkout_url(slug)
                    if v != new:
                        node[k] = new
                        changes += 1
            else:
                changes += _replace_inscripcion_strings(v, image_map)
    elif isinstance(node, list):
        for i, item in enumerate(node):
            if isinstance(item, str) and '/inscripcion/' in item:
                slug = _slug_from_url(item, image_map)
                if slug:
                    new = _checkout_url(slug)
                    if item != new:
                        node[i] = new
                        changes += 1
            else:
                changes += _replace_inscripcion_strings(item, image_map)
    return changes


def _patch_elementor_node(node, image_map: dict[str, str], state: dict) -> int:
    """Recorre árbol Elementor; devuelve cantidad de enlaces reemplazados."""
    changes = 0
    if isinstance(node, dict):
        settings = node.get('settings') or {}
        wt = node.get('widgetType')
        if wt == 'image':
            img_url = (settings.get('image') or {}).get('url') or ''
            slug = _slug_from_url(img_url, image_map)
            if slug:
                state['slug'] = slug
        for key in ('link', 'url'):
            if key == 'url' and wt not in ('button', 'call-to-action', 'image'):
                pass
            elif key == 'link' and isinstance(settings.get('link'), dict):
                link = settings['link']
                url = link.get('url') or ''
                if _is_payment_link(url) or (url and 'diplomados' in url.lower()):
                    slug = state.get('slug') or _slug_from_url(url, image_map)
                    if slug:
                        new_url = _checkout_url(slug)
                        if url != new_url:
                            link['url'] = new_url
                            changes += 1
        # url suelta en algunos widgets
        if isinstance(settings.get('url'), str) and _is_payment_link(settings['url']):
            slug = state.get('slug') or _slug_from_url(settings['url'], image_map)
            if slug:
                new_url = _checkout_url(slug)
                if settings['url'] != new_url:
                    settings['url'] = new_url
                    changes += 1
        for ch in node.get('elements') or []:
            changes += _patch_elementor_node(ch, image_map, state)
    elif isinstance(node, list):
        for item in node:
            changes += _patch_elementor_node(item, image_map, state)
    return changes


def _wp_cli(*args: str) -> str:
    cmd = ['sudo', '-u', 'www-data', 'wp', *args, f'--path={WP_ROOT}']
    env = os.environ.copy()
    env['WP_CLI_CACHE_DIR'] = '/var/www/.wp-cli/cache'
    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"wp {' '.join(args)} failed: {proc.stderr or proc.stdout}")
    return proc.stdout


def _load_elementor(page_id: int) -> list:
    raw = _wp_cli('post', 'meta', 'get', str(page_id), '_elementor_data')
    return json.loads(raw)


def _save_elementor(page_id: int, data: list) -> None:
    payload = json.dumps(data, ensure_ascii=False)
    # wp post meta update con JSON escapado
    proc = subprocess.run(
        [
            'sudo',
            '-u',
            'www-data',
            'wp',
            'post',
            'meta',
            'update',
            str(page_id),
            '_elementor_data',
            payload,
            f'--path={WP_ROOT}',
        ],
        capture_output=True,
        text=True,
        env={**os.environ, 'WP_CLI_CACHE_DIR': '/var/www/.wp-cli/cache'},
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr or proc.stdout)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', action='store_true', help='Escribir en WordPress (sin esto: solo simulación)')
    parser.add_argument('--page-id', type=int, action='append', dest='page_ids')
    args = parser.parse_args()
    apply = bool(args.apply)
    page_ids = args.page_ids or list(WP_PAGE_IDS)

    if not MEDIA_MAP_PATH.is_file():
        print(f'Missing {MEDIA_MAP_PATH}', file=sys.stderr)
        return 1
    if not WP_ROOT.is_dir():
        print(f'WP root not found: {WP_ROOT}', file=sys.stderr)
        return 1

    image_map = _load_image_to_slug()
    total = 0
    for pid in page_ids:
        try:
            data = _load_elementor(pid)
        except Exception as e:
            print(f'Page {pid}: skip ({e})')
            continue
        n = _patch_elementor_node(data, image_map, {})
        n += _replace_inscripcion_strings(data, image_map)
        title = _wp_cli('post', 'get', str(pid), '--field=post_title').strip()
        print(f'Page {pid} ({title}): {n} link(s) → checkout')
        if apply and n:
            _save_elementor(pid, data)
            _wp_cli('elementor', 'flush-css')
        total += n

    if apply:
        print(f'Applied {total} updates.')
    else:
        print(f'Dry-run: {total} would change. Re-run with --apply')
    return 0


if __name__ == '__main__':
    sys.exit(main())
