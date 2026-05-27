#!/usr/bin/env python3
"""Cablea botones «Ver más» en WordPress → landing de ventas apps (/inscripcion/<slug>)."""
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
APPS = os.environ.get('IIUS_APPS_BASE', 'https://apps.internationalinstitute.us').rstrip('/')

# Páginas catálogo marketing IIUS
WP_PAGE_IDS = (
    2006,  # Cursos / cursos-detalle
    2233,  # Talleres
    2084,  # Eventos
    214,   # Entrenamientos (bloques Cursos / Talleres / Diplomados)
)

# Enlaces de categoría (no un programa): vitrina apps
HUB_LINKS: dict[str, str] = {
    'diplomados.png': f'{APPS}/programas',
    'cursos.png': f'{APPS}/programas',
    'talleres.png': f'{APPS}/programas',
}

# Alias extra (archivos WP no en JSON base)
EXTRA_IMAGE_TO_SLUG: dict[str, str] = {
    'liderasgo-de-gestion-de-equipo': 'curso-en-liderazgo-y-gestion-de-equipos',
    'desarrollo-de-negocio': 'cursos-en-emprendimiento-y-desarrollo-de-negocios',
    'liderasgo-organizacional': 'curso-en-coaching-ejecutivo-y-liderazgo-organizacional',
    'coaching-prof': 'curso-en-coaching-profesional-integral',
    'coaching-profesional-integral': 'curso-en-coaching-profesional-integral',
    'ancalje': 'curso-tecnicas-anclaje-pnl',
    'ieyb': 'curso-en-inteligencia-emocional-y-bienestar',
    'iemo': 'curso-en-inteligencia-emocional-y-bienestar',
    'pnl': 'curso-en-neuroeducacion-y-programacion-neurolinguistica-pnl',
    'pnlarte': 'curso-tecnicas-anclaje-pnl',
    'reencuadrespnl': 'curso-tecnicas-anclaje-pnl',
    'mindfulness': 'curso-en-mindfulness-y-reduccion-del-estres',
    'espiritualidad-crecimiento': 'curso-en-espiritualidad-y-crecimiento-personal',
    'renovacion-de-mente': 'renovacion-de-la-mente',
    'mujer-virtuosa': 'la-mujer-virtuosa-de-prov-31',
    'finanzas-personales': 'curso-en-finanzas-personales-y-empresariales',
    'finanzapersonales': 'curso-en-finanzas-personales-y-empresariales',
    'lidernegocio': 'curso-en-liderazgo-y-gestion-de-equipos',
    'empredimientonegocio': 'cursos-en-emprendimiento-y-desarrollo-de-negocios',
    'coachingejecutivo': 'curso-en-coaching-ejecutivo-y-liderazgo-organizacional',
    'coachingejecutivo.png': 'curso-en-coaching-ejecutivo-y-liderazgo-organizacional',
    'creatividadvak': 'diplomado-en-creatividad-y-expresion-artistica-aplicada',
    'collagemapas': 'taller-aprendizaje-practico',
    'chatgpt-image-19-may-2026-21_51_22': 'taller-aprendizaje-practico',
    'chatgpt-image-19-may-2026-22_01_31': 'taller-liderazgo-y-comunicacion',
    'chatgpt-image-19-may-2026-21_55_28': 'diplomado-en-creatividad-y-expresion-artistica-aplicada',
    'chatgpt-image-19-may-2026-21_57_45': 'taller-desarrollo-humano',
    'nuero-liderazgo': 'neuro-liderazgo-intercultural',
    'nuero-heuristica': 'neuro-heuristica-coaching-vida',
    'neuro-decodificacion': 'neuro-descodificacion-psicogenealogia-pnl',
    'neuro-liderazgo-intercultural2': 'neuro-liderazgo-intercultural',
    'neuro-decodificacion_qr': 'neuro-descodificacion-psicogenealogia-pnl',
    'n33': 'curso-de-neuroeducacion-y-neuroplasticidad',
    'n3': 'curso-en-neuroeducacion-y-programacion-neurolinguistica-pnl',
}


def _inscripcion_url(slug: str) -> str:
    return f'{APPS}/inscripcion/{slug.strip().lower()}'


def _load_image_to_slug() -> dict[str, str]:
    data = json.loads(MEDIA_MAP_PATH.read_text(encoding='utf-8'))
    out: dict[str, str] = dict(EXTRA_IMAGE_TO_SLUG)
    for slug, url in (data.get('programs') or {}).items():
        fname = (url or '').rsplit('/', 1)[-1].lower()
        if fname:
            out[fname] = slug
        stem = re.sub(r'\.[a-z0-9]+$', '', fname, flags=re.I)
        if stem:
            out[stem] = slug
    # Misma imagen WP: curso de negocios (no el taller homónimo)
    out['liderasgo-organizacional.png'] = 'curso-en-coaching-ejecutivo-y-liderazgo-organizacional'
    out['liderasgo-organizacional'] = 'curso-en-coaching-ejecutivo-y-liderazgo-organizacional'
    return out


def _slug_from_image(url: str, image_map: dict[str, str]) -> str | None:
    if not url:
        return None
    low = url.lower()
    fname = low.rsplit('/', 1)[-1]
    if fname in image_map:
        return image_map[fname]
    stem = re.sub(r'\.[a-z0-9]+$', '', fname, flags=re.I)
    if stem in image_map:
        return image_map[stem]
    for key, slug in sorted(image_map.items(), key=lambda x: -len(x[0])):
        if len(key) >= 5 and key in low:
            return slug
    return None


def _should_rewire(url: str) -> bool:
    if not url or not isinstance(url, str):
        return False
    low = url.lower().strip()
    if low.startswith('#') or low.startswith('mailto:'):
        return False
    if 'internationalinstitute.us/diplomados' in low:
        return True
    if '/programs/' in low:
        return True
    if '/checkout/programa/' in low:
        return True
    if low.startswith('/inscripcion/'):
        return True
    if f'{APPS.lower()}/inscripcion/' in low and low.count('/inscripcion/') == 1:
        # ya correcto
        return False
    if f'{APPS.lower()}/programas' in low and 'inscripcion' not in low:
        return False  # hub ok
    return False


def _skip_image_for_page(page_id: int, image_url: str) -> bool:
    """En cursos-detalle no cablear tarjetas taller (imágenes ChatGPT duplicadas)."""
    if page_id != 2006:
        return False
    fname = (image_url or '').rsplit('/', 1)[-1].lower()
    return fname.startswith('chatgpt-image-')


def _patch_node(node, image_map: dict[str, str], state: dict, page_id: int = 0) -> int:
    changes = 0
    if isinstance(node, dict):
        st = node.get('settings') or {}
        wt = node.get('widgetType')
        if wt == 'image':
            u = (st.get('image') or {}).get('url') or ''
            state.pop('hub', None)
            if u and not _skip_image_for_page(page_id, u):
                state['img'] = u
                fname = u.rsplit('/', 1)[-1].lower()
                if fname in HUB_LINKS:
                    state['hub'] = HUB_LINKS[fname]
            else:
                state.pop('img', None)
        if isinstance(st.get('link'), dict):
            link = st['link']
            url = (link.get('url') or '').strip()
            if not url or url.startswith('#') or url.startswith('mailto:'):
                pass
            else:
                new_url = None
                img = state.get('img') or ''
                if _skip_image_for_page(page_id, img):
                    pass
                elif state.get('hub'):
                    new_url = state['hub']
                else:
                    slug = _slug_from_image(img, image_map)
                    if slug:
                        new_url = _inscripcion_url(slug)
                if new_url and url != new_url:
                    link['url'] = new_url
                    changes += 1
        for ch in node.get('elements') or []:
            changes += _patch_node(ch, image_map, state, page_id)
    elif isinstance(node, list):
        for item in node:
            changes += _patch_node(item, image_map, state, page_id)
    return changes


def _wp(*args: str) -> str:
    proc = subprocess.run(
        ['sudo', '-u', 'www-data', 'wp', *args, f'--path={WP_ROOT}'],
        capture_output=True,
        text=True,
        env={**os.environ, 'WP_CLI_CACHE_DIR': '/var/www/.wp-cli/cache'},
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr or proc.stdout)
    return proc.stdout


def _process_page(page_id: int, image_map: dict[str, str], apply: bool) -> int:
    raw = _wp('post', 'meta', 'get', str(page_id), '_elementor_data')
    data = json.loads(raw)
    n = _patch_node(data, image_map, {}, page_id)
    title = _wp('post', 'get', str(page_id), '--field=post_title').strip()
    print(f'Page {page_id} ({title}): {n} enlace(s) → /inscripcion/ o /programas')
    if apply and n:
        payload = json.dumps(data, ensure_ascii=False)
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
        )
        if proc.returncode != 0:
            raise RuntimeError(proc.stderr or proc.stdout)
    return n


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--page-id', type=int, action='append')
    args = parser.parse_args()
    if not MEDIA_MAP_PATH.is_file():
        print(f'Missing {MEDIA_MAP_PATH}', file=sys.stderr)
        return 1
    image_map = _load_image_to_slug()
    total = 0
    page_ids = args.page_id or list(WP_PAGE_IDS)
    for pid in page_ids:
        try:
            total += _process_page(pid, image_map, args.apply)
        except Exception as e:
            print(f'Page {pid}: ERROR {e}', file=sys.stderr)
    if args.apply:
        _wp('elementor', 'flush-css')
        print(f'Applied {total} updates.')
    else:
        print(f'Dry-run: {total} would change. Use --apply')
    return 0


if __name__ == '__main__':
    sys.exit(main())
