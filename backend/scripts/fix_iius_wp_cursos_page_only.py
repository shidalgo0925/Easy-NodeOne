#!/usr/bin/env python3
"""Página Cursos WP (2006): quitar bloque Talleres y asegurar un slug /inscripcion/ por curso."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.apply_iius_wp_ver_mas_inscripcion import (  # noqa: E402
    APPS,
    _load_image_to_slug,
    _patch_node,
    _inscripcion_url,
    _slug_from_image,
)

WP_ROOT = Path('/var/www/wordpress')
CURSOS_PAGE = 2006

# PNL en cursos-detalle = Programación Neurolingüística (no neuroplasticidad)
PNL_CURSO_SLUG = 'curso-en-neuroeducacion-y-programacion-neurolinguistica-pnl'


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


def _container_is_talleres_block(el: dict) -> bool:
    """True si el contenedor es el bloque Talleres (título o tarjetas ChatGPT)."""

    def scan(o) -> bool:
        if isinstance(o, dict):
            st = o.get('settings') or {}
            if o.get('widgetType') == 'heading':
                title = (st.get('title') or '').strip()
                if title == 'Talleres':
                    return True
            img = (st.get('image') or {}).get('url') or ''
            if 'chatgpt-image-19-may-2026' in img.lower():
                return True
            for c in o.get('elements') or []:
                if scan(c):
                    return True
        elif isinstance(o, list):
            return any(scan(x) for x in o)
        return False

    return el.get('elType') == 'container' and scan(el)


def main() -> int:
    raw = _wp('post', 'meta', 'get', str(CURSOS_PAGE), '_elementor_data')
    data = json.loads(raw)
    before = len(data)
    data = [el for el in data if not _container_is_talleres_block(el)]
    removed = before - len(data)
    print(f'Removed {removed} Talleres container(s) from Cursos page')

    image_map = _load_image_to_slug()
    image_map['pnl.png'] = PNL_CURSO_SLUG
    image_map['pnl'] = PNL_CURSO_SLUG

    n = _patch_node(data, image_map, {}, CURSOS_PAGE)
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
            str(CURSOS_PAGE),
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
    print('Done. Cursos page = solo 12 cursos en 3 bloques.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
