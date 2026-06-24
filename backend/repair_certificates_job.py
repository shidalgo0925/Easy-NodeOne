#!/usr/bin/env python3
"""Repara formatos y plantillas de certificado (cron nocturno)."""
import sys
from pathlib import Path

backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from app import app, db
from nodeone.services.certificate_assets import repair_certificates_job

with app.app_context():
    repair_certificates_job(db, printfn=print)
