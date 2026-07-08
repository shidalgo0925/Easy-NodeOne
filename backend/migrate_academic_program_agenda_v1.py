#!/usr/bin/env python3
"""Columnas V1 coaching + agenda (requires_agenda, matrícula, slot 60 min IIUS)."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from sqlalchemy import inspect, text


def _add_column_if_missing(table: str, column: str, ddl: str) -> None:
    insp = inspect(db.engine)
    cols = {c['name'] for c in insp.get_columns(table)}
    if column not in cols:
        db.session.execute(text(f'ALTER TABLE {table} ADD COLUMN {ddl}'))
        print(f'  + {table}.{column}')


with app.app_context():
    _add_column_if_missing(
        'academic_program',
        'requires_agenda',
        'requires_agenda BOOLEAN NOT NULL DEFAULT FALSE',
    )
    _add_column_if_missing(
        'academic_program',
        'ecalendar_product_id',
        'ecalendar_product_id VARCHAR(64)',
    )
    _add_column_if_missing(
        'academic_program_enrollment',
        'agenda_status',
        "agenda_status VARCHAR(32) NOT NULL DEFAULT 'not_required'",
    )
    _add_column_if_missing(
        'academic_program_enrollment',
        'scheduled_at',
        'scheduled_at TIMESTAMP',
    )
    _add_column_if_missing(
        'academic_program_enrollment',
        'google_event_id',
        'google_event_id VARCHAR(256)',
    )
    db.session.commit()

    from models.academic_program import AcademicProgram
    from models.ecalendar import ECalendarSettings

    updates = (
        ('coaching-individual', True, 'coaching_personal'),
        ('coaching-ejecutivo', True, 'coaching_ejecutivo'),
    )
    for slug, req, pid in updates:
        row = AcademicProgram.query.filter_by(organization_id=1, slug=slug).first()
        if row:
            row.requires_agenda = req
            row.ecalendar_product_id = pid
            print(f'  program {slug}: requires_agenda={req} product={pid}')

    ecal = ECalendarSettings.query.filter_by(organization_id=1).first()
    if ecal and int(getattr(ecal, 'slot_minutes', 0) or 0) != 60:
        ecal.slot_minutes = 60
        print('  ecalendar org 1: slot_minutes=60')

    db.session.commit()
    print('OK migrate_academic_program_agenda_v1')
