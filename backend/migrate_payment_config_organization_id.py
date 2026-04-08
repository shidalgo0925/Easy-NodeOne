#!/usr/bin/env python3
"""Añade organization_id a payment_config y rellena NULL con la primera org (SQLite u otros)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import inspect, text

from app import PaymentConfig, SaasOrganization, app, db

with app.app_context():
    uri = app.config.get('SQLALCHEMY_DATABASE_URI') or ''
    print('DB:', uri.replace('sqlite:///', '') if uri.startswith('sqlite:///') else uri)
    insp = inspect(db.engine)
    cols = [c['name'] for c in insp.get_columns('payment_config')]
    if 'organization_id' not in cols:
        try:
            db.session.execute(text('ALTER TABLE payment_config ADD COLUMN organization_id INTEGER'))
            db.session.commit()
            print('Columna organization_id añadida.')
        except Exception as e:
            print('Error ALTER payment_config:', e)
            sys.exit(1)
    else:
        print('Columna organization_id ya existe.')

    first = SaasOrganization.query.order_by(SaasOrganization.id.asc()).first()
    if first:
        n = PaymentConfig.query.filter(PaymentConfig.organization_id.is_(None)).update(
            {'organization_id': int(first.id)}, synchronize_session=False
        )
        if n:
            db.session.commit()
            print(f'Actualizadas {n} fila(s) con organization_id={first.id}.')
        else:
            print('Sin filas payment_config con organization_id NULL.')
    else:
        print('No hay saas_organization; no se rellena organization_id.')
