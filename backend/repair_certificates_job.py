#!/usr/bin/env python3
"""Repara formatos y plantillas de certificado (cron o ejecución manual)."""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
os.environ.setdefault('NODEONE_ROOT', str(ROOT))
sys.path.insert(0, str(ROOT / 'backend'))

from dotenv import load_dotenv

load_dotenv(ROOT.parent / '.env')

from app import create_app, db
from nodeone.services.certificate_assets import (
    STATUS_CREATED,
    STATUS_REPAIRED,
    STATUS_REUSED,
    ensure_all_event_certificate_formats,
    repair_certificates_job,
)

app = create_app()
with app.app_context():
    print('=== Reparar formatos/plantillas por organización ===')
    repair_certificates_job(db, printfn=print)
    print('=== Reparar TODOS los eventos con has_certificate ===')
    stats = ensure_all_event_certificate_formats(db, commit=True)
    print(
        f"event_formats created={stats.get(STATUS_CREATED, 0)} "
        f"repaired={stats.get(STATUS_REPAIRED, 0)} reused={stats.get(STATUS_REUSED, 0)}"
    )
    for row in stats.get('events') or []:
        print(
            f"  event #{row.get('event_id')} format=#{row.get('certificate_event_id')} "
            f"fmt={row.get('format_status')} tpl={row.get('template_status')}"
        )
