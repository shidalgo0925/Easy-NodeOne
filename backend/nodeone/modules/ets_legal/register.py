"""Registro del centro legal ETS."""


def register_ets_legal(app) -> None:
    from nodeone.modules.ets_legal.routes import register_ets_legal_blueprint

    register_ets_legal_blueprint(app)
