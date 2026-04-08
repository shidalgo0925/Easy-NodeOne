#!/usr/bin/env python3
"""Añade organization_id a email_queue y rellena desde marketing_campaigns."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import inspect, text

from app import SaasOrganization, app, db

with app.app_context():
    insp = inspect(db.engine)
    cols = [c['name'] for c in insp.get_columns('email_queue')]
    if 'organization_id' not in cols:
        try:
            db.session.execute(text('ALTER TABLE email_queue ADD COLUMN organization_id INTEGER'))
            db.session.commit()
            print('Columna organization_id añadida a email_queue.')
        except Exception as e:
            print('Error ALTER email_queue:', e)
            sys.exit(1)
    else:
        print('email_queue.organization_id ya existe.')

    try:
        db.session.execute(
            text(
                """
                UPDATE email_queue
                SET organization_id = (
                    SELECT organization_id FROM marketing_campaigns
                    WHERE marketing_campaigns.id = email_queue.campaign_id
                )
                WHERE campaign_id IS NOT NULL
                  AND (organization_id IS NULL OR organization_id = 0)
                """
            )
        )
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print('Nota UPDATE desde campaigns:', e)

    first = SaasOrganization.query.order_by(SaasOrganization.id.asc()).first()
    fid = int(first.id) if first else 1
    try:
        r = db.session.execute(
            text('UPDATE email_queue SET organization_id = :fid WHERE organization_id IS NULL'),
            {'fid': fid},
        )
        db.session.commit()
        if getattr(r, 'rowcount', None):
            print(f'Filas sin org rellenadas con organization_id={fid}: {r.rowcount}')
    except Exception as e:
        db.session.rollback()
        print('Nota UPDATE fallback:', e)
