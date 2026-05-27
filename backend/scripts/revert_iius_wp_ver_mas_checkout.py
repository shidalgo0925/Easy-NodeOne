#!/usr/bin/env python3
"""Revierte enlaces checkout en Elementor → estado previo (revisiones WP)."""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

WP_ROOT = Path(os.environ.get('IIUS_WP_ROOT', '/var/www/wordpress'))
APPS = 'https://apps.internationalinstitute.us'

# revision_id con Elementor antes del cableado a checkout (2026-05-22)
RESTORE_FROM_REVISION: dict[int, int] = {
    2006: 2223,  # cursos-detalle → programs/ + diplomados/
    2233: 2234,  # talleres → programs/ + diplomados/
    2084: 2085,  # eventos
}

# diplomados disponibles: volver a /inscripcion/<slug>
DIPLOMADO_PAGE = 212
DIPLOMADO_SLUGS = (
    'neuro-liderazgo-intercultural',
    'neuro-descodificacion-psicogenealogia-pnl',
    'neuro-teologia-coaching-cristiano-transgeneracional',
    'neuro-heuristica-coaching-vida',
)


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


def _get_elementor(page_or_rev_id: int) -> str:
    return _wp('post', 'meta', 'get', str(page_or_rev_id), '_elementor_data')


def _set_elementor(page_id: int, data: str) -> None:
    proc = subprocess.run(
        ['sudo', '-u', 'www-data', 'wp', 'post', 'meta', 'update', str(page_id), '_elementor_data', data, f'--path={WP_ROOT}'],
        capture_output=True,
        text=True,
        env={**os.environ, 'WP_CLI_CACHE_DIR': '/var/www/.wp-cli/cache'},
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr or proc.stdout)


def _revert_diplomados_inscripcion(raw: str) -> tuple[str, int]:
    n = 0
    out = raw
    for slug in DIPLOMADO_SLUGS:
        old = f'{APPS}/checkout/programa/{slug}/full'
        new = f'{APPS}/inscripcion/{slug}'
        if old in out:
            out = out.replace(old, new)
            n += out.count(new) - raw.count(new) if False else 1
        rel_old = f'/checkout/programa/{slug}/full'
        rel_new = f'/inscripcion/{slug}'
        if rel_old in out:
            out = out.replace(rel_old, rel_new)
            n += 1
    # contar reemplazos reales
    n = len(re.findall(rf'{re.escape(APPS)}/inscripcion/', out)) - len(
        re.findall(rf'{re.escape(APPS)}/inscripcion/', raw)
    )
    return out, max(0, n)


def _revert_page_214_elementor(data: list) -> int:
    """Entrenamientos: Cursos/Talleres → programs/…; Diplomados → /diplomados/."""
    changes = 0
    legacy_prog = f'{APPS}/programs/curso-en-coaching-profesional-integral'
    legacy_dipl = 'https://internationalinstitute.us/diplomados/'
    state: dict = {}

    def walk(node):
        nonlocal changes
        if isinstance(node, dict):
            st = node.get('settings') or {}
            if node.get('widgetType') == 'image':
                u = (st.get('image') or {}).get('url') or ''
                state['img'] = u.rsplit('/', 1)[-1].lower()
            if isinstance(st.get('link'), dict):
                url = (st['link'].get('url') or '').strip()
                want = legacy_dipl if state.get('img') == 'diplomados.png' else legacy_prog
                if url and url != want:
                    st['link']['url'] = want
                    changes += 1
            for ch in node.get('elements') or []:
                walk(ch)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(data)
    return changes


def main() -> int:
    for page_id, rev_id in RESTORE_FROM_REVISION.items():
        data = _get_elementor(rev_id)
        _set_elementor(page_id, data)
        chk = data.count('checkout/programa')
        print(f'Page {page_id} ← revision {rev_id} (checkout refs in backup: {chk})')

    raw212 = _get_elementor(DIPLOMADO_PAGE)
    new212, _ = _revert_diplomados_inscripcion(raw212)
    if new212 != raw212:
        _set_elementor(DIPLOMADO_PAGE, new212)
        print(f'Page {DIPLOMADO_PAGE}: diplomados → /inscripcion/')

    raw214 = _get_elementor(214)
    data214 = json.loads(raw214)
    n214 = _revert_page_214_elementor(data214)
    if n214:
        _set_elementor(214, json.dumps(data214, ensure_ascii=False))
        print(f'Page 214: {n214} enlace(s) → programs/ + diplomados/')

    _wp('elementor', 'flush-css')
    print('Revert WP done.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
