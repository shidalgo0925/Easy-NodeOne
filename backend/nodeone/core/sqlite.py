"""Resolución de ruta de fichero SQLite desde la URI de SQLAlchemy (desacoplado del monolito)."""

import os

from sqlalchemy.engine.url import make_url


def sqlite_path_from_flask_app(flask_app):
    """
    Ruta absoluta al .db si la config usa SQLite; None en otro caso.
    Usa flask_app.root_path para URIs relativas (equivalente a dirname(app.py)).
    """
    uri = (flask_app.config.get('SQLALCHEMY_DATABASE_URI') or '') or ''
    if not uri.startswith('sqlite'):
        return None
    u = make_url(uri)
    p = u.database
    if not p:
        return None
    if os.path.isabs(p):
        return p
    return os.path.abspath(os.path.join(flask_app.root_path, p))
