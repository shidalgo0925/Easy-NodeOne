#!/usr/bin/env python3
"""Página Eventos WP (2084, slug /talleres/): quitar catálogo duplicado; CTA a campus apps."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

WP_ROOT = Path('/var/www/wordpress')
EVENTOS_PAGE = 2084
APPS = 'https://apps.internationalinstitute.us'

CURSO_SECTION_TITLES = frozenset(
    {
        'Cursos de Negocios',
        'Cursos en Ciencia',
        'Cursos en Espiritualidad',
        'Talleres',
    }
)

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
    'chatgpt-image-19-may-2026',
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


def _container_is_catalog_duplicate(el: dict) -> bool:
    """Bloques copiados del catálogo (cursos/talleres), no eventos reales."""
    if el.get('elType') != 'container':
        return False

    def scan(o) -> bool:
        if isinstance(o, dict):
            st = o.get('settings') or {}
            if o.get('widgetType') == 'heading':
                title = (st.get('title') or '').strip()
                if title in CURSO_SECTION_TITLES:
                    return True
            img = (st.get('image') or {}).get('url') or ''
            low = img.lower()
            if any(m in low for m in CURSO_IMAGE_MARKERS):
                return True
            for c in o.get('elements') or []:
                if scan(c):
                    return True
        elif isinstance(o, list):
            return any(scan(x) for x in o)
        return False

    return scan(el)


def _patch_hero_and_intro(data: list) -> None:
    intro_html = (
        '<p>En esta sección encontrarás <strong>convocatorias, webinars y actividades</strong> '
        'con fecha y cupo limitado. Los cursos y diplomados con inscripción abierta están en el catálogo formativo.</p>'
        f'<p style="margin-top:1.25em">'
        f'<a class="elementor-button elementor-size-md" href="{APPS}/events" '
        f'style="display:inline-block;margin-right:12px;padding:12px 24px;background:#8B60AA;color:#fff;'
        f'border-radius:6px;text-decoration:none;font-weight:600">Ver eventos en el campus</a>'
        f'<a class="elementor-button elementor-button-link elementor-size-md" href="{APPS}/programas" '
        f'style="display:inline-block;padding:12px 24px;border:2px solid #8B60AA;color:#8B60AA;'
        f'border-radius:6px;text-decoration:none;font-weight:600">Catálogo de programas</a>'
        f'</p>'
    )

    for el in data[:2]:
        def walk(o):
            if isinstance(o, dict):
                st = o.get('settings') or {}
                if o.get('widgetType') == 'heading':
                    st['title'] = 'Eventos y próximas fechas'
                if o.get('widgetType') == 'text-editor':
                    st['editor'] = intro_html
                for c in o.get('elements') or []:
                    walk(c)
            elif isinstance(o, list):
                for x in o:
                    walk(x)

        walk(el)


def main() -> int:
    raw = _wp('post', 'meta', 'get', str(EVENTOS_PAGE), '_elementor_data')
    data = json.loads(raw)
    before = len(data)
    data = [el for el in data if not _container_is_catalog_duplicate(el)]
    removed = before - len(data)
    print(f'Removed {removed} catalog duplicate container(s)')

    _patch_hero_and_intro(data)

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

    _wp('elementor', 'flush-css')
    _wp('cache', 'flush')
    print(f'Eventos page: {len(data)} block(s), CTA → {APPS}/events y {APPS}/programas')
    return 0


if __name__ == '__main__':
    sys.exit(main())
