#!/usr/bin/env python3
"""Crear tablas de marketing (segment, template, campaign, campaign_recipients, automation_flows, email_queue)."""
import sys
from pathlib import Path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from app import app, db
from app import (
    MarketingSegment, MarketingTemplate, MarketingCampaign,
    CampaignRecipient, AutomationFlow, EmailQueueItem
)

with app.app_context():
    try:
        db.create_all()
        print("Marketing tables ensured.")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
