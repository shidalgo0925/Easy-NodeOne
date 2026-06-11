#!/usr/bin/env python3
"""Crear tabla ecalendar_settings."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models.ecalendar import ECalendarSettings

with app.app_context():
    ECalendarSettings.__table__.create(db.engine, checkfirst=True)
    print('OK: ecalendar_settings')
