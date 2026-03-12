#!/usr/bin/env python3
"""Procesa campañas programadas (status=scheduled, scheduled_at <= now). Ejecutar por cron cada 5-15 min.
   Uso: python backend/process_scheduled_campaigns.py"""
import sys
from pathlib import Path
from datetime import datetime

backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from app import app, db, MarketingCampaign
from _app.modules.marketing.service import start_campaign

with app.app_context():
    now = datetime.utcnow()
    pending = MarketingCampaign.query.filter(
        MarketingCampaign.status == 'scheduled',
        MarketingCampaign.scheduled_at.isnot(None),
        MarketingCampaign.scheduled_at <= now
    ).all()
    for c in pending:
        _, err = start_campaign(c.id)
        if err:
            print(f"Campaña {c.id} ({c.name}): {err}")
        else:
            print(f"Campaña {c.id} ({c.name}): enviada")
    print(f"Listo. {len(pending)} campañas procesadas.")
