#!/usr/bin/env python3
"""Añade organization_id a marketing_campaigns si falta (campañas multi-tenant)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import inspect, text

from app import SaasOrganization, app, db

with app.app_context():
    insp = inspect(db.engine)
    cols = [c['name'] for c in insp.get_columns('marketing_campaigns')]
    if 'organization_id' not in cols:
        try:
            db.session.execute(
                text('ALTER TABLE marketing_campaigns ADD COLUMN organization_id INTEGER DEFAULT 1')
            )
            db.session.commit()
            print('Columna organization_id añadida a marketing_campaigns.')
        except Exception as e:
            print('Error ALTER:', e)
            sys.exit(1)
    else:
        print('marketing_campaigns.organization_id ya existe.')

    first = SaasOrganization.query.order_by(SaasOrganization.id.asc()).first()
    fid = int(first.id) if first else 1
    try:
        r = db.session.execute(
            text('UPDATE marketing_campaigns SET organization_id = :fid WHERE organization_id IS NULL'),
            {'fid': fid},
        )
        db.session.commit()
        if r.rowcount:
            print(f'Actualizadas {r.rowcount} fila(s) con organization_id={fid}.')
    except Exception as e:
        db.session.rollback()
        print('Nota UPDATE:', e)
