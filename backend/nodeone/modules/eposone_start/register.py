"""Registro del Asistente de Inicio EPosOne."""


def register_eposone_start(app) -> None:
    from nodeone.modules.eposone_start.routes import register_eposone_start_blueprint

    register_eposone_start_blueprint(app)
