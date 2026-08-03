"""Registro del módulo API Center."""


def register_api_center_module(app) -> None:
    from nodeone.modules.api_center.routes import register_api_center

    register_api_center(app)
