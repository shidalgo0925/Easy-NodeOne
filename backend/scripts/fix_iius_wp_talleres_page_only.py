#!/usr/bin/env python3
"""Página Talleres WP (2233): quitar bloques de cursos; solo 4 talleres → /inscripcion/<slug>."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.apply_iius_wp_ver_mas_inscripcion import _load_image_to_slug, _patch_node  # noqa: E402

WP_ROOT = Path('/var/www/wordpress')
TALLERES_PAGE = 2233

CURSO_SECTION_TITLES = frozenset(
    {
        'Cursos de Negocios',
        'Cursos en Ciencia',
        'Cursos en Espiritualidad',
    }
)

# Imágenes de cursos (no deben estar en página Talleres)
CURSO_IMAGE_MARKERS = (
    'liderasgo-de-gestion-de-equipo',
    'desarrollo-de-negocio',
    'liderasgo-organizacional',
    'finanzas-personales',
    'coaching-prof',
    'ancalje',
    'ieyb',
    'pnl.png',
    'mindfulness.png',
    'espiritualidad-crecimiento',
    'renovacion-de-mente',
    'mujer-virtuosa',
)


def _wp(*args: str) -> str:
    proc = subprocess.run(
        ['sudo', '-u', 'www-data', 'wp', *args, f'--path={WP_ROOT}'],
        capture_output=True,
        text=True,
        env={'WP_CLI_CACHE_DIR': '/var/www/.wp-cli/cache'},
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr or proc.stdout)
    return proc.stdout


def _container_is_curso_block(el: dict) -> bool:
    if el.get('elType') != 'container':
        return False

    def scan(o) -> str | None:
        if isinstance(o, dict):
            st = o.get('settings') or {}
            if o.get('widgetType') == 'heading':
                title = (st.get('title') or '').strip()
                if title in CURSO_SECTION_TITLES:
                    return 'heading'
            img = (st.get('image') or {}).get('url') or ''
            low = img.lower()
            if any(m in low for m in CURSO_IMAGE_MARKERS):
                return 'image'
            for c in o.get('elements') or []:
                r = scan(c)
                if r:
                    return r
        elif isinstance(o, list):
            for x in o:
                r = scan(x)
                if r:
                    return r
        return None

    return scan(el) is not None


def _container_is_talleres_cards(el: dict) -> bool:
    if el.get('elType') != 'container':
        return False

    def scan(o) -> bool:
        if isinstance(o, dict):
            img = (o.get('settings') or {}).get('image', {}).get('url') or ''
            if 'chatgpt-image-19-may-2026' in img.lower():
                return True
            for c in o.get('elements') or []:
                if scan(c):
                    return True
        elif isinstance(o, list):
            return any(scan(x) for x in o)
        return False

    return scan(el)


def _patch_hero_copy(data: list) -> None:
    """Título e intro acordes a Talleres (no «Catálogo de Cursos»)."""
    for el in data[:2]:
        def walk(o):
            if isinstance(o, dict):
                st = o.get('settings') or {}
                if o.get('widgetType') == 'heading':
                    t = st.get('title') or ''
                    if 'Catálogo de Cursos' in t or 'Cursos y Programas' in t:
                        st['title'] = 'Catálogo de Talleres'
                if o.get('widgetType') == 'text-editor':
                    ed = st.get('editor') or ''
                    if 'cursos prácticos, talleres' in ed.lower():
                        st['editor'] = (
                            '<p>Nuestros talleres están diseñados para el aprendizaje práctico '
                            'y el desarrollo de competencias en sesiones dinámicas. '
                            'Elegí tu taller e inscribite en línea.</p>'
                        )
                for c in o.get('elements') or []:
                    walk(c)
            elif isinstance(o, list):
                for x in o:
                    walk(x)

        walk(el)


def main() -> int:
    raw = _wp('post', 'meta', 'get', str(TALLERES_PAGE), '_elementor_data')
    data = json.loads(raw)
    before = len(data)

    kept = []
    for el in data:
        if _container_is_curso_block(el):
            continue
        kept.append(el)
    data = kept
    removed = before - len(data)
    print(f'Removed {removed} curso container(s) from Talleres page')

    _patch_hero_copy(data)

    image_map = _load_image_to_slug()
    n = _patch_node(data, image_map, {}, TALLERES_PAGE)
    print(f'Rewired {n} Ver más → /inscripcion/<slug>')

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
            str(TALLERES_PAGE),
            '_elementor_data',
            payload,
            f'--path={WP_ROOT}',
        ],
        capture_output=True,
        text=True,
        env={'WP_CLI_CACHE_DIR': '/var/www/.wp-cli/cache'},
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr or proc.stdout)

    _wp('elementor', 'flush-css')
    _wp('cache', 'flush')
    print('Done.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
