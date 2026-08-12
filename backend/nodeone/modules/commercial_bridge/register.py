"""Registro del módulo commercial_bridge (ESB ↔ EN1)."""


def register_commercial_bridge_module(app) -> None:
    from nodeone.modules.commercial_bridge.routes import register_commercial_bridge

    register_commercial_bridge(app)
