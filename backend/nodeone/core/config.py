"""Configuración: overrides opcionales tras importar el monolito (create_app)."""

import os


def load_config(app):
    """
    Ajustes desde env que no requieren reordenar bootstrap.
    DB: usar SQLALCHEMY_DATABASE_URI o DATABASE_URL antes del arranque (ver nodeone.core.bootstrap).
    """
    base = (os.environ.get('BASE_URL') or '').strip()
    base_l = base.lower()

    # OAuth (Authlib): el state vive en la sesión firmada; al volver de Google el navegador debe
    # enviar la misma cookie. Tras HTTPS + proxy, conviene Secure explícito y SameSite coherente.
    sec_env = (os.environ.get('SESSION_COOKIE_SECURE') or '').strip().lower()
    if sec_env in ('0', 'false', 'no'):
        app.config['SESSION_COOKIE_SECURE'] = False
    elif sec_env in ('1', 'true', 'yes'):
        app.config['SESSION_COOKIE_SECURE'] = True
    elif base_l.startswith('https://'):
        app.config['SESSION_COOKIE_SECURE'] = True

    ss = (os.environ.get('SESSION_COOKIE_SAMESITE') or '').strip()
    if ss:
        s = ss.lower()
        if s == 'none':
            app.config['SESSION_COOKIE_SAMESITE'] = 'None'
            app.config['SESSION_COOKIE_SECURE'] = True
        elif s == 'lax':
            app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
        elif s == 'strict':
            app.config['SESSION_COOKIE_SAMESITE'] = 'Strict'
    elif base_l.startswith('https://'):
        app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

    pref = (os.environ.get('PREFERRED_URL_SCHEME') or '').strip().lower()
    if pref in ('http', 'https'):
        app.config['PREFERRED_URL_SCHEME'] = pref
    elif base_l.startswith('https://'):
        app.config['PREFERRED_URL_SCHEME'] = 'https'

    return app
