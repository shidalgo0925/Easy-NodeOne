#!/usr/bin/env python3
"""Crear tablas certificate_events y certificates y evento por defecto Certificado de Membresía."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app import app, db, CertificateEvent, Certificate

with app.app_context():
    CertificateEvent.__table__.create(db.engine, checkfirst=True)
    Certificate.__table__.create(db.engine, checkfirst=True)
    if not CertificateEvent.query.filter(CertificateEvent.name == 'Certificado de Membresía').first():
        ev = CertificateEvent(
            name='Certificado de Membresía',
            is_active=True,
            verification_enabled=True,
            code_prefix='MEM',
            membership_required_id=None,
            event_required_id=None,
        )
        db.session.add(ev)
        db.session.commit()
        print("OK certificate_events, certificates, evento Certificado de Membresía creado")
    else:
        print("OK certificate_events, certificates")
