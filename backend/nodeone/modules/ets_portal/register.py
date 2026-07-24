"""Registro del blueprint Portal ETS."""

from __future__ import annotations


def register_ets_portal(app) -> None:
    from nodeone.modules.ets_portal.routes import register_ets_portal_blueprint

    register_ets_portal_blueprint(app)
