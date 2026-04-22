"""Arranque mínimo Flask + SQLAlchemy (extraído del monolito para factory futura)."""

import logging
import os
import sys

from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix

from nodeone.core.db import db


def _sqlalchemy_uri(backend_dir):
    """URI por defecto SQLite en instance/; override con SQLALCHEMY_DATABASE_URI o DATABASE_URL."""
    raw = (os.environ.get('SQLALCHEMY_DATABASE_URI') or os.environ.get('DATABASE_URL') or '').strip()
    if raw:
        if raw.startswith('postgres://'):
            raw = raw.replace('postgres://', 'postgresql://', 1)
        return raw
    db_path = os.path.join(os.path.dirname(backend_dir), 'instance', 'NodeOne.db')
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    return f'sqlite:///{db_path}'


def init_monolith_flask_app(import_name, stripe_mod):
    """
    Flask, ProxyFix, SECRET_KEY/SQLite/Mail, Stripe api_key, db.init_app, log ERROR a archivo.

    import_name: pasar __name__ del módulo que define la app (p. ej. app al cargar backend/app.py).
    stripe_mod: módulo stripe importado o None.

    Returns:
        (app, stripe_publishable_key)
    """
    app = Flask(import_name, template_folder='../templates', static_folder='../static')
    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_for=1)

    sys.modules.setdefault('app', sys.modules[import_name])

    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'nodeone-dev-secret-key-change-in-production')

    backend_dir = os.path.abspath(os.path.dirname(sys.modules[import_name].__file__))
    app.config['SQLALCHEMY_DATABASE_URI'] = _sqlalchemy_uri(backend_dir)
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    if stripe_mod:
        stripe_mod.api_key = os.getenv('STRIPE_SECRET_KEY', 'sk_test_your_stripe_secret_key_here')
        stripe_pk = os.getenv('STRIPE_PUBLISHABLE_KEY', 'pk_test_your_stripe_publishable_key_here')
    else:
        stripe_pk = None

    app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER', 'smtp.office365.com')
    app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', '587'))
    app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'True').lower() == 'true'
    app.config['MAIL_USE_SSL'] = os.getenv('MAIL_USE_SSL', 'False').lower() == 'true'
    app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME', '')
    app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD', '')
    app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER', 'noreply@example.com')

    db.init_app(app)

    logpath = os.path.join(os.path.dirname(backend_dir), 'instance', 'app_errors.log')
    os.makedirs(os.path.dirname(logpath), exist_ok=True)
    file_handler = logging.FileHandler(logpath, encoding='utf-8')
    file_handler.setLevel(logging.ERROR)
    file_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(name)s: %(message)s'))
    app.logger.addHandler(file_handler)

    return app, stripe_pk
