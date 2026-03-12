# Acceso a datos marketing
from app import db
from app import (
    MarketingSegment, MarketingTemplate, MarketingCampaign,
    CampaignRecipient, AutomationFlow, EmailQueueItem, User
)


def get_segment_by_id(segment_id):
    return MarketingSegment.query.get(segment_id)


def get_template_by_id(template_id):
    return MarketingTemplate.query.get(template_id)


def get_campaign_by_id(campaign_id):
    return MarketingCampaign.query.get(campaign_id)


def get_recipient_by_tracking_id(tracking_id):
    return CampaignRecipient.query.filter_by(tracking_id=tracking_id).first()


def get_pending_queue_items(limit=100):
    return EmailQueueItem.query.filter_by(status='pending').order_by(EmailQueueItem.id).limit(limit).all()


def get_active_automation_flows_by_trigger(trigger_event):
    return AutomationFlow.query.filter_by(trigger_event=trigger_event, active=True).all()
