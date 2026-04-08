"""Configuración: overrides opcionales tras importar el monolito (create_app)."""

import os


def load_config(app):
    """
    Ajustes desde env que no requieren reordenar bootstrap.
    DB: usar SQLALCHEMY_DATABASE_URI o DATABASE_URL antes del arranque (ver nodeone.core.bootstrap).
    """
    v = os.environ.get('SESSION_COOKIE_SECURE', '').strip().lower()
    if v in ('1', 'true', 'yes'):
        app.config['SESSION_COOKIE_SECURE'] = True
    v = os.environ.get('PREFERRED_URL_SCHEME', '').strip().lower()
    if v in ('http', 'https'):
        app.config['PREFERRED_URL_SCHEME'] = v
    return app
