from datetime import datetime

from nodeone.core.db import db


class CrmStage(db.Model):
    __tablename__ = 'crm_stage'
    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(
        db.Integer,
        db.ForeignKey('saas_organization.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    name = db.Column(db.String(120), nullable=False)
    sequence = db.Column(db.Integer, nullable=False, default=10)
    probability_default = db.Column(db.Float, nullable=False, default=10.0)
    is_won = db.Column(db.Boolean, nullable=False, default=False)
    is_lost = db.Column(db.Boolean, nullable=False, default=False)
    active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('organization_id', 'name', name='uq_crm_stage_org_name'),
    )


class CrmLostReason(db.Model):
    __tablename__ = 'crm_lost_reason'
    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(
        db.Integer,
        db.ForeignKey('saas_organization.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    name = db.Column(db.String(200), nullable=False)
    active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('organization_id', 'name', name='uq_crm_lost_reason_org_name'),
    )


class CrmLead(db.Model):
    __tablename__ = 'crm_lead'
    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(
        db.Integer,
        db.ForeignKey('saas_organization.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    lead_type = db.Column(db.String(20), nullable=False, default='lead')  # lead|opportunity
    name = db.Column(db.String(255), nullable=False)
    contact_name = db.Column(db.String(255))
    company_name = db.Column(db.String(255))
    email = db.Column(db.String(255), index=True)
    phone = db.Column(db.String(80), index=True)
    stage_id = db.Column(db.Integer, db.ForeignKey('crm_stage.id', ondelete='RESTRICT'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='SET NULL'), index=True)
    expected_revenue = db.Column(db.Float, nullable=False, default=0.0)
    probability = db.Column(db.Float, nullable=False, default=0.0)
    priority = db.Column(db.String(10), nullable=False, default='low')  # low|medium|high
    source = db.Column(db.String(80), default='web')
    description = db.Column(db.Text)
    create_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    close_date = db.Column(db.DateTime)
    lost_reason_id = db.Column(db.Integer, db.ForeignKey('crm_lost_reason.id', ondelete='SET NULL'), index=True)
    active = db.Column(db.Boolean, nullable=False, default=True)

    stage = db.relationship('CrmStage')
    lost_reason = db.relationship('CrmLostReason')


class CrmTag(db.Model):
    __tablename__ = 'crm_tag'
    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(
        db.Integer,
        db.ForeignKey('saas_organization.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    name = db.Column(db.String(80), nullable=False)
    color = db.Column(db.String(20), default='blue')
    active = db.Column(db.Boolean, nullable=False, default=True)

    __table_args__ = (
        db.UniqueConstraint('organization_id', 'name', name='uq_crm_tag_org_name'),
    )


class CrmLeadTag(db.Model):
    __tablename__ = 'crm_lead_tag'
    id = db.Column(db.Integer, primary_key=True)
    lead_id = db.Column(db.Integer, db.ForeignKey('crm_lead.id', ondelete='CASCADE'), nullable=False, index=True)
    tag_id = db.Column(db.Integer, db.ForeignKey('crm_tag.id', ondelete='CASCADE'), nullable=False, index=True)

    __table_args__ = (
        db.UniqueConstraint('lead_id', 'tag_id', name='uq_crm_lead_tag'),
    )


class CrmActivity(db.Model):
    __tablename__ = 'crm_activity'
    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(
        db.Integer,
        db.ForeignKey('saas_organization.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    lead_id = db.Column(db.Integer, db.ForeignKey('crm_lead.id', ondelete='CASCADE'), nullable=False, index=True)
    type = db.Column(db.String(20), nullable=False)  # call|meeting|email|task
    summary = db.Column(db.String(255), nullable=False)
    due_date = db.Column(db.DateTime, nullable=False)
    assigned_to = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='SET NULL'), nullable=False, index=True)
    status = db.Column(db.String(20), nullable=False, default='pending')  # pending|done|canceled|overdue
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class CrmActivityType(db.Model):
    """Tipos de actividad configurables por organización (valor de crm_activity.type = code)."""

    __tablename__ = 'crm_activity_type'
    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(
        db.Integer,
        db.ForeignKey('saas_organization.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    code = db.Column(db.String(20), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    active = db.Column(db.Boolean, nullable=False, default=True)
    sequence = db.Column(db.Integer, nullable=False, default=10)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('organization_id', 'code', name='uq_crm_activity_type_org_code'),
    )


class CrmLeadLog(db.Model):
    __tablename__ = 'crm_lead_log'
    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(
        db.Integer,
        db.ForeignKey('saas_organization.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    lead_id = db.Column(db.Integer, db.ForeignKey('crm_lead.id', ondelete='CASCADE'), nullable=False, index=True)
    log_type = db.Column(db.String(20), nullable=False)  # email|call|note|system
    message = db.Column(db.Text, nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='SET NULL'), index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
