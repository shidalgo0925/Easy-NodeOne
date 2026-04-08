#!/usr/bin/env python3
"""Procesa cola email_queue: envía hasta 100 pendientes usando SMTP por organización (marketing)."""
import json
import sys
from datetime import datetime
from pathlib import Path

backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

import app as ap

BATCH = 100


def _queue_item_org_id(item):
    oi = getattr(item, 'organization_id', None)
    if oi is not None:
        return int(oi)
    if item.campaign_id:
        camp = ap.db.session.get(ap.MarketingCampaign, item.campaign_id)
        if camp is not None:
            return int(camp.organization_id or 1)
    return 1


with ap.app.app_context():
    ap.bootstrap_runtime_schema_and_email()

    enabled_orgs = {
        o.id
        for o in ap.SaasOrganization.query.all()
        if ap.has_saas_module_enabled(o.id, 'marketing_email')
    }
    if not enabled_orgs:
        print('Ninguna organización tiene marketing_email activo; cola no procesada.')
        sys.exit(0)

    if not ap.Mail or not getattr(ap, 'EmailService', None):
        print('Flask-Mail o EmailService no disponibles')
        sys.exit(1)

    raw = (
        ap.EmailQueueItem.query.filter_by(status='pending')
        .order_by(ap.EmailQueueItem.id)
        .limit(500)
        .all()
    )
    items = []
    for item in raw:
        oid = _queue_item_org_id(item)
        if oid in enabled_orgs:
            items.append(item)
        if len(items) >= BATCH:
            break

    last_cid = None
    try:
        for item in items:
            item.status = 'processing'
            ap.db.session.commit()
            try:
                payload = json.loads(item.payload) if item.payload else {}
                subject = payload.get('subject', '')
                html = payload.get('html', '')
                to_email = payload.get('to_email', '')
                if not to_email:
                    item.status = 'failed'
                    ap.db.session.commit()
                    continue
                oid_send = _queue_item_org_id(item)
                ok_smtp, cfg_id = ap.apply_marketing_smtp_for_organization(
                    oid_send, skip_if_config_id=last_cid
                )
                if ok_smtp:
                    last_cid = cfg_id
                if not ok_smtp or not ap.email_service:
                    item.status = 'failed'
                    ap.db.session.commit()
                    continue
                is_campaign = bool(item.campaign_id)
                email_type = 'marketing_campaign' if is_campaign else 'marketing_automation'
                rel_type = 'campaign' if is_campaign else 'marketing_automation'
                ok = ap.email_service.send_email(
                    subject=subject,
                    recipients=[to_email],
                    html_content=html,
                    sender=payload.get('from_name') or None,
                    reply_to=payload.get('reply_to') or None,
                    email_type=email_type,
                    related_entity_type=rel_type,
                    related_entity_id=item.campaign_id,
                )
                if ok:
                    item.status = 'sent'
                    if item.recipient_id:
                        rec = ap.CampaignRecipient.query.get(item.recipient_id)
                        if rec:
                            rec.sent_at = datetime.utcnow()
                            rec.status = 'sent'
                else:
                    item.status = 'failed'
                ap.db.session.commit()
            except Exception as e:
                item.status = 'failed'
                ap.db.session.rollback()
                print(f'Error queue item {item.id}: {e}')
    finally:
        ap.apply_email_config_from_db()

    print(f'Procesados {len(items)} emails')
