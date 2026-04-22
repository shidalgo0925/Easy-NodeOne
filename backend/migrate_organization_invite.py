#!/usr/bin/env python3
"""Crea tabla organization_invite si no existe."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import inspect

from app import app, db
from models.organization_invite import OrganizationInvite


def main() -> None:
    with app.app_context():
        uri = app.config.get('SQLALCHEMY_DATABASE_URI') or ''
        print('DB:', uri.replace('sqlite:///', '') if uri.startswith('sqlite:///') else uri)
        insp = inspect(db.engine)
        if 'organization_invite' not in insp.get_table_names():
            OrganizationInvite.__table__.create(db.engine, checkfirst=True)
            print('Tabla organization_invite creada.')
        else:
            print('Tabla organization_invite ya existe.')


if __name__ == '__main__':
    main()
