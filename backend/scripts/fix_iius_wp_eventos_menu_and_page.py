#!/usr/bin/env python3
"""Corrige Eventos WP: menú duplicado, /eventos/ real, retira página /talleres/ mal nombrada."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

WP_ROOT = Path('/var/www/wordpress')
APPS = 'https://apps.internationalinstitute.us'

# Página WP Event Manager (menú «Eventos» correcta)
EVENTOS_PAGE = 210
# Página mal nombrada: título «Eventos» pero slug /talleres/ (duplicado viejo)
MAL_NOMBRADA_PAGE = 2084
MENU_EVENTOS_MALO = 2116  # apuntaba a /talleres/
MENU_EVENTOS_OK = 298  # apuntaba a /eventos/


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


def _elementor_eventos_landing() -> list:
    intro = (
        '<p>Consultá <strong>convocatorias, webinars y actividades</strong> con fecha y cupo en el campus virtual. '
        'Para cursos, diplomados y talleres con inscripción abierta, usá el catálogo de programas.</p>'
        f'<p style="margin-top:1.25em">'
        f'<a href="{APPS}/events" style="display:inline-block;margin-right:12px;padding:12px 24px;'
        f'background:#8B60AA;color:#fff;border-radius:6px;text-decoration:none;font-weight:600">'
        f'Ver eventos en el campus</a>'
        f'<a href="{APPS}/programas" style="display:inline-block;padding:12px 24px;border:2px solid #8B60AA;'
        f'color:#8B60AA;border-radius:6px;text-decoration:none;font-weight:600">Catálogo de programas</a>'
        f'</p>'
    )
    return [
        {
            'id': 'evhero1',
            'elType': 'container',
            'settings': {'padding': {'unit': 'px', 'top': '80', 'bottom': '40', 'left': '20', 'right': '20'}},
            'elements': [
                {
                    'id': 'evh1',
                    'elType': 'widget',
                    'widgetType': 'heading',
                    'settings': {'title': 'Eventos y próximas fechas', 'header_size': 'h1'},
                    'elements': [],
                }
            ],
            'isInner': False,
        },
        {
            'id': 'evbody1',
            'elType': 'container',
            'settings': {'padding': {'unit': 'px', 'top': '0', 'bottom': '80', 'left': '20', 'right': '20'}},
            'elements': [
                {
                    'id': 'evt1',
                    'elType': 'widget',
                    'widgetType': 'text-editor',
                    'settings': {'editor': intro},
                    'elements': [],
                }
            ],
            'isInner': False,
        },
    ]


def main() -> int:
    # 1) Página /eventos/ — reemplazar listado vacío del plugin
    payload = json.dumps(_elementor_eventos_landing(), ensure_ascii=False)
    proc = subprocess.run(
        [
            'sudo',
            '-u',
            'www-data',
            'wp',
            'post',
            'meta',
            'update',
            str(EVENTOS_PAGE),
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
    _wp('post', 'update', str(EVENTOS_PAGE), '--post_content=', '--post_title=Eventos')
    print(f'Page {EVENTOS_PAGE} (/eventos/): landing → {APPS}/events')

    # 2) Menú: quitar enlace erróneo a /talleres/
    _wp('menu', 'item', 'delete', str(MENU_EVENTOS_MALO))
    print(f'Removed menu item {MENU_EVENTOS_MALO} (Eventos → /talleres/)')

    _wp(
        'menu',
        'item',
        'update',
        str(MENU_EVENTOS_OK),
        f'--url={APPS}/events',
        '--title=Eventos',
    )
    print(f'Menu item {MENU_EVENTOS_OK}: Eventos → {APPS}/events')

    # 3) Página confusa /talleres/ (título Eventos) → borrador + redirección a /eventos/
    _wp('post', 'update', str(MAL_NOMBRADA_PAGE), '--post_status=draft', '--post_title=Página obsoleta (era Eventos en /talleres)')
    print(f'Page {MAL_NOMBRADA_PAGE} (/talleres/) → draft')

    _wp('elementor', 'flush-css')
    _wp('cache', 'flush')
    print('Done.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
