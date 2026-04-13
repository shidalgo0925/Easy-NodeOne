"""Versión de la aplicación mostrada en UI (p. ej. perfil).

Prioridad:
1. Variable de entorno NODEONE_APP_VERSION (por silo, sin tocar archivos).
2. Archivo VERSION en la raíz del proyecto (hermano de backend/), versionado en Git.
3. Fallback 'dev' si no existe ninguno.
"""
from __future__ import annotations

import os

_cached_file: str | None = None


def get_app_version() -> str:
    env = (os.environ.get('NODEONE_APP_VERSION') or '').strip()
    if env:
        return env
    global _cached_file
    if _cached_file is not None:
        return _cached_file
    try:
        path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), '..', '..', '..', 'VERSION')
        )
        with open(path, encoding='utf-8') as f:
            _cached_file = (f.read() or '').strip() or 'dev'
    except OSError:
        _cached_file = 'dev'
    return _cached_file
