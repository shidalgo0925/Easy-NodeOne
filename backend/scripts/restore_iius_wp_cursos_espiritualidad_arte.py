#!/usr/bin/env python3
"""Restaura /cursos-detalle/ (WP 2006): Espiritualidad desde rev. 2264 + bloque Talleres/arte."""
from __future__ import annotations

import copy
import json
import secrets
import subprocess
import sys
from pathlib import Path

WP_ROOT = Path('/var/www/wordpress')
CURSOS_PAGE = 2006
REVISION_OK = 2264  # 12 cursos + Espiritualidad correcta (sin duplicar)


def _wp(*args: str) -> str:
    proc = subprocess.run(
        ['/usr/local/bin/wp', *args, f'--path={WP_ROOT}'],
        capture_output=True,
        text=True,
        env={'PATH': '/usr/local/bin:/usr/bin:/bin', 'WP_CLI_CACHE_DIR': '/var/www/.wp-cli/cache'},
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr or proc.stdout)
    return proc.stdout


def _fix_heading_talleres(node: dict) -> None:
    if node.get('widgetType') == 'heading':
        node.setdefault('settings', {})['title'] = 'Talleres'
    for ch in node.get('elements') or []:
        if isinstance(ch, dict):
            _fix_heading_talleres(ch)


_APPS_BASE = 'https://apps.internationalinstitute.us'
_TALLER_IMAGE_TO_SLUG = {
    'collagemapas': 'taller-aprendizaje-practico',
    'talleres': 'taller-aprendizaje-practico',
    'chatgpt-image-19-may-2026-21_51_22': 'taller-aprendizaje-practico',
    'liderasgo-organizacional': 'taller-liderazgo-y-comunicacion',
    'chatgpt-image-19-may-2026-22_01_31': 'taller-liderazgo-y-comunicacion',
    'creatividadvak': 'diplomado-en-creatividad-y-expresion-artistica-aplicada',
    'chatgpt-image-19-may-2026-21_55_28': 'diplomado-en-creatividad-y-expresion-artistica-aplicada',
    'chatgpt-image-19-may-2026-21_57_45': 'taller-desarrollo-humano',
}


def _slug_from_image(url: str) -> str | None:
    import re

    fname = url.rsplit('/', 1)[-1].lower()
    stem = re.sub(r'\.[a-z0-9]+$', '', fname)
    if stem in _TALLER_IMAGE_TO_SLUG:
        return _TALLER_IMAGE_TO_SLUG[stem]
    for key, slug in sorted(_TALLER_IMAGE_TO_SLUG.items(), key=lambda x: -len(x[0])):
        if len(key) >= 5 and key in fname:
            return slug
    return None


def _wire_talleres_buttons(node: dict, pending_image: list) -> None:
    """Recablea botones del bloque Talleres por imagen (no usar liderasgo-organizacional.png)."""
    wt = node.get('widgetType') or ''
    st = node.setdefault('settings', {}) if wt else {}
    if wt == 'image':
        url = (st.get('image') or {}).get('url') or ''
        if url and 'uploads' in url:
            pending_image[:] = [url]
        return
    if wt == 'button' and pending_image:
        slug = _slug_from_image(pending_image[0])
        if slug:
            link = st.get('link')
            if not isinstance(link, dict):
                link = {}
                st['link'] = link
            link['url'] = f'{_APPS_BASE}/inscripcion/{slug}'
        pending_image.clear()
    for ch in node.get('elements') or []:
        if isinstance(ch, dict):
            _wire_talleres_buttons(ch, pending_image)


def main() -> int:
    base = json.loads(_wp('post', 'meta', 'get', str(REVISION_OK), '_elementor_data'))
    current = json.loads(_wp('post', 'meta', 'get', str(CURSOS_PAGE), '_elementor_data'))

    arte_grid = None
    for el in current:
        if el.get('id') == '24dff4aa':
            arte_grid = el
            break
    if arte_grid is None:
        for el in current:
            s = json.dumps(el)
            if 'diplomado-en-creatividad-y-expresion-artistica-aplicada' in s:
                arte_grid = el
                break

    title_tpl = next(el for el in base if el.get('id') == 'da376a0')

    data = list(base)
    if arte_grid:
        band = copy.deepcopy(title_tpl)
        band['id'] = secrets.token_hex(4)
        _fix_heading_talleres(band)
        grid = copy.deepcopy(arte_grid)
        grid['id'] = secrets.token_hex(4)
        _wire_talleres_buttons(grid, [])
        data.extend([band, grid])
        print('Espiritualidad: rev. 2264 · Talleres/arte: grid recuperado')
    else:
        print('Espiritualidad: rev. 2264 · Talleres/arte: no se encontró grid (solo 12 cursos)')

    payload = json.dumps(data, ensure_ascii=False)
    proc = subprocess.run(
        [
            '/usr/local/bin/wp',
            'post',
            'meta',
            'update',
            str(CURSOS_PAGE),
            '_elementor_data',
            payload,
            f'--path={WP_ROOT}',
        ],
        capture_output=True,
        text=True,
        env={'PATH': '/usr/local/bin:/usr/bin:/bin', 'WP_CLI_CACHE_DIR': '/var/www/.wp-cli/cache'},
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr or proc.stdout)

    _wp('elementor', 'flush-css')
    _wp('cache', 'flush')
    print(f'Página {CURSOS_PAGE} restaurada. Ctrl+F5 en /cursos-detalle/')
    return 0


if __name__ == '__main__':
    sys.exit(main())
