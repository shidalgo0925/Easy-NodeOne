#!/usr/bin/env python3
"""
Crear tabla ecalendar_settings en la BD de APPDEV.

Debe usar la misma config que easynodeone-dev.service:
  EnvironmentFile=/opt/easynodeone/dev/.env
  User=nodeone
  WorkingDirectory=/opt/easynodeone/dev/app

Ejecutar:
  sudo -u nodeone bash -lc 'set -a && source /opt/easynodeone/dev/.env && set +a && \
    cd /opt/easynodeone/dev/app/backend && /opt/easynodeone/dev/venv/bin/python3 migrate_ecalendar_settings.py'
"""
from __future__ import annotations

import os
import sys

# Evitar que app.py cargue dev/app/.env (SQLite local) antes que el .env del servicio.
os.environ.setdefault('NODEONE_SKIP_DOTENV_APP', '1')

_DEV_ENV = '/opt/easynodeone/dev/.env'
if os.path.isfile(_DEV_ENV):
    try:
        from dotenv import load_dotenv

        load_dotenv(_DEV_ENV, override=True)
    except ImportError:
        pass

if not (os.environ.get('DATABASE_URL') or '').strip():
    print('ERROR: DATABASE_URL no definida. Cargá /opt/easynodeone/dev/.env (mismo que systemd).')
    sys.exit(1)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models.ecalendar import ECalendarSettings
from sqlalchemy import inspect, text

with app.app_context():
    uri = (app.config.get('SQLALCHEMY_DATABASE_URI') or '').strip()
    engine_url = str(db.engine.url)

    if uri.startswith('sqlite:'):
        print('ERROR: el script apunta a SQLite:', uri)
        print('APPDEV usa PostgreSQL vía /opt/easynodeone/dev/.env — revisá DATABASE_URL.')
        print('Ejecutá como: sudo -u nodeone con source /opt/easynodeone/dev/.env')
        sys.exit(1)

    print('DB engine:', engine_url.split('@')[-1] if '@' in engine_url else engine_url[:80])
    print('UID:', os.getuid(), 'user:', os.environ.get('USER', '?'))

    ECalendarSettings.__table__.create(db.engine, checkfirst=True)

    insp = inspect(db.engine)
    if not insp.has_table('ecalendar_settings'):
        print('ERROR: tabla ecalendar_settings no existe tras CREATE.')
        sys.exit(1)

    row = db.session.execute(text('SELECT COUNT(*) FROM ecalendar_settings')).scalar()
    print('OK: ecalendar_settings existe, filas:', row)
