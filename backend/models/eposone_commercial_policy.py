"""Políticas comerciales EPosOne — identidad, versiones y asignaciones (infra V6)."""

from __future__ import annotations

from datetime import datetime

from nodeone.core.db import db


class EposoneCommercialPolicy(db.Model):
    __tablename__ = 'eposone_commercial_policy'

    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(
        db.Integer,
        db.ForeignKey('saas_organization.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    policy_type = db.Column(db.String(32), nullable=False)
    code = db.Column(db.String(64), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    active = db.Column(db.Boolean, nullable=False, default=True)
    valid_from = db.Column(db.DateTime, nullable=True)
    valid_to = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    __table_args__ = (
        db.UniqueConstraint(
            'organization_id',
            'policy_type',
            'code',
            name='uq_eposone_commercial_policy_org_type_code',
        ),
    )


class EposoneCommercialPolicyVersion(db.Model):
    __tablename__ = 'eposone_commercial_policy_version'

    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(
        db.Integer,
        db.ForeignKey('saas_organization.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    policy_id = db.Column(
        db.Integer,
        db.ForeignKey('eposone_commercial_policy.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    version_number = db.Column(db.Integer, nullable=False)
    payload_json = db.Column(db.Text, nullable=False, default='{}')
    # draft | active | obsolete | archived
    publication_status = db.Column(db.String(16), nullable=False, default='draft')
    # True solo para la versión active publicada (atajo de consulta).
    is_current = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    created_by_user_id = db.Column(db.Integer, nullable=True)
    published_at = db.Column(db.DateTime, nullable=True)

    __table_args__ = (
        db.UniqueConstraint(
            'policy_id',
            'version_number',
            name='uq_eposone_commercial_policy_version',
        ),
    )


class EposoneCommercialPolicyAssignment(db.Model):
    __tablename__ = 'eposone_commercial_policy_assignment'

    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(
        db.Integer,
        db.ForeignKey('saas_organization.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    policy_type = db.Column(db.String(32), nullable=False)
    policy_id = db.Column(
        db.Integer,
        db.ForeignKey('eposone_commercial_policy.id', ondelete='CASCADE'),
        nullable=False,
    )
    policy_version_id = db.Column(
        db.Integer,
        db.ForeignKey('eposone_commercial_policy_version.id', ondelete='SET NULL'),
        nullable=True,
    )
    scope_type = db.Column(db.String(32), nullable=False)
    scope_ref = db.Column(db.String(128), nullable=False)
    active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    __table_args__ = (
        db.UniqueConstraint(
            'organization_id',
            'policy_type',
            'scope_type',
            'scope_ref',
            name='uq_eposone_commercial_policy_assignment_scope',
        ),
    )


class EposoneCommercialPoliciesSyncState(db.Model):
    __tablename__ = 'eposone_commercial_policies_sync_state'

    organization_id = db.Column(
        db.Integer,
        db.ForeignKey('saas_organization.id', ondelete='CASCADE'),
        primary_key=True,
    )
    policies_version = db.Column(db.BigInteger, nullable=False, default=0)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
