"""
App factory — FASE 1 (incremental).

Una sola fuente de verdad: `app.create_app()` en `app.py` (tras import del monolito).
"""


def create_app():
    from app import create_app as monolith_create_app

    return monolith_create_app()
