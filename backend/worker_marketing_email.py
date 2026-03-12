#!/usr/bin/env python3
"""Procesa cola email_queue: envía hasta 100 pendientes usando EmailService."""
import sys
import json
from pathlib import Path
from datetime import datetime

backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from app import app, db, email_service, EmailQueueItem, CampaignRecipient

BATCH = 100

with app.app_context():
    if not email_service:
        print("EmailService no disponible")
        sys.exit(1)
    items = EmailQueueItem.query.filter_by(status='pending').order_by(EmailQueueItem.id).limit(BATCH).all()
    for item in items:
        item.status = 'processing'
        db.session.commit()
        try:
            payload = json.loads(item.payload) if item.payload else {}
            subject = payload.get('subject', '')
            html = payload.get('html', '')
            to_email = payload.get('to_email', '')
            if not to_email:
                item.status = 'failed'
                db.session.commit()
                continue
            sender = payload.get('from_name') or None
            reply_to = payload.get('reply_to') or None
            ok = email_service.send_email(
                subject=subject,
                recipients=[to_email],
                html_content=html,
                sender=sender,
                reply_to=reply_to,
                email_type='marketing_campaign',
                related_entity_type='campaign',
                related_entity_id=item.campaign_id,
            )
            if ok:
                item.status = 'sent'
                if item.recipient_id:
                    rec = CampaignRecipient.query.get(item.recipient_id)
                    if rec:
                        rec.sent_at = datetime.utcnow()
                        rec.status = 'sent'
            else:
                item.status = 'failed'
            db.session.commit()
        except Exception as e:
            item.status = 'failed'
            db.session.rollback()
            print(f"Error queue item {item.id}: {e}")
    print(f"Procesados {len(items)} emails")
