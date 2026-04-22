#!/usr/bin/env python3
"""
Crea tabla user_organization y rellena desde user.organization_id (compat multi-empresa).

Ejecutar desde backend/:  python3 migrate_user_organization.py
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import inspect

from app import User, app, db
from models.users import UserOrganization


def main() -> None:
    with app.app_context():
        uri = app.config.get('SQLALCHEMY_DATABASE_URI') or ''
        print('DB:', uri.replace('sqlite:///', '') if uri.startswith('sqlite:///') else uri)
        insp = inspect(db.engine)
        names = insp.get_table_names()
        if 'user_organization' not in names:
            db.create_all()
            print('Tabla user_organization creada (create_all).')
        else:
            print('Tabla user_organization ya existe.')

        n = 0
        users = User.query.all()
        for u in users:
            oid = getattr(u, 'organization_id', None)
            try:
                oi = int(oid) if oid is not None else 0
            except (TypeError, ValueError):
                oi = 0
            if oi < 1:
                continue
            exists = UserOrganization.query.filter_by(user_id=u.id, organization_id=oi).first()
            if exists:
                continue
            role = 'admin' if getattr(u, 'is_admin', False) else 'user'
            db.session.add(
                UserOrganization(
                    user_id=u.id,
                    organization_id=oi,
                    role=role,
                    status='active',
                )
            )
            n += 1
        if n:
            db.session.commit()
            print(f'Insertadas {n} fila(s) de membresía desde user.organization_id.')
        else:
            print('Sin filas nuevas que insertar.')
        print('Listo.')


if __name__ == '__main__':
    main()
