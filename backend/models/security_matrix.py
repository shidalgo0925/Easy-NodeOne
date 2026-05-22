"""Matriz de permisos Odoo (security_matrix_manager) — multi-tenant."""

from __future__ import annotations

from datetime import datetime

from nodeone.core.db import db

IMPORT_STATUSES = (
    'draft',
    'validated',
    'approved',
    'rejected',
    'executed',
    'failed',
)


class SecurityMatrixCatalogSnapshot(db.Model):
    __tablename__ = 'security_matrix_catalog_snapshot'

    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(
        db.Integer, db.ForeignKey('saas_organization.id', ondelete='CASCADE'), nullable=False, index=True
    )
    payload_json = db.Column(db.Text, nullable=False)
    database_name = db.Column(db.String(120), nullable=False, default='')
    odoo_version = db.Column(db.String(40), nullable=False, default='')
    user_count = db.Column(db.Integer, nullable=False, default=0)
    group_count = db.Column(db.Integer, nullable=False, default=0)
    membership_count = db.Column(db.Integer, nullable=False, default=0)
    synced_by_user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='SET NULL'), nullable=True)
    synced_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)

    imports = db.relationship('SecurityMatrixImport', backref='catalog_snapshot', lazy='dynamic')


class SecurityMatrixImport(db.Model):
    __tablename__ = 'security_matrix_import'

    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(
        db.Integer, db.ForeignKey('saas_organization.id', ondelete='CASCADE'), nullable=False, index=True
    )
    catalog_snapshot_id = db.Column(
        db.Integer,
        db.ForeignKey('security_matrix_catalog_snapshot.id', ondelete='SET NULL'),
        nullable=True,
        index=True,
    )
    filename = db.Column(db.String(255), nullable=False, default='')
    uploaded_by_user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='SET NULL'), nullable=True)
    status = db.Column(db.String(20), nullable=False, default='draft', index=True)
    has_critical_errors = db.Column(db.Boolean, nullable=False, default=False)
    validation_summary_json = db.Column(db.Text, nullable=True)
    ai_summary_json = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    approved_by_user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='SET NULL'), nullable=True)
    approved_at = db.Column(db.DateTime, nullable=True)
    executed_at = db.Column(db.DateTime, nullable=True)
    rejected_at = db.Column(db.DateTime, nullable=True)
    rejected_by_user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='SET NULL'), nullable=True)

    rows = db.relationship(
        'SecurityMatrixRow',
        backref='import_record',
        lazy='dynamic',
        cascade='all, delete-orphan',
    )
    previews = db.relationship(
        'SecurityMatrixChangePreview',
        backref='import_record',
        lazy='dynamic',
        cascade='all, delete-orphan',
    )


class SecurityMatrixRow(db.Model):
    __tablename__ = 'security_matrix_row'

    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(
        db.Integer, db.ForeignKey('saas_organization.id', ondelete='CASCADE'), nullable=False, index=True
    )
    import_id = db.Column(
        db.Integer,
        db.ForeignKey('security_matrix_import.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    sheet_name = db.Column(db.String(64), nullable=False, default='')
    row_number = db.Column(db.Integer, nullable=False, default=0)
    area = db.Column(db.String(200), nullable=False, default='')
    module = db.Column(db.String(200), nullable=False, default='')
    screen = db.Column(db.String(200), nullable=False, default='')
    odoo_group = db.Column(db.String(200), nullable=False, default='')
    username = db.Column(db.String(200), nullable=False, default='')
    permission_read = db.Column(db.Boolean, nullable=True)
    permission_create = db.Column(db.Boolean, nullable=True)
    permission_write = db.Column(db.Boolean, nullable=True)
    permission_unlink = db.Column(db.Boolean, nullable=True)
    risk_level = db.Column(db.String(20), nullable=False, default='')
    validation_status = db.Column(db.String(20), nullable=False, default='pending')
    validation_errors_json = db.Column(db.Text, nullable=True)
    raw_json = db.Column(db.Text, nullable=True)


class SecurityMatrixChangePreview(db.Model):
    __tablename__ = 'security_matrix_change_preview'

    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(
        db.Integer, db.ForeignKey('saas_organization.id', ondelete='CASCADE'), nullable=False, index=True
    )
    import_id = db.Column(
        db.Integer,
        db.ForeignKey('security_matrix_import.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    odoo_user = db.Column(db.String(200), nullable=False, default='')
    odoo_group = db.Column(db.String(200), nullable=False, default='')
    group_xml_id = db.Column(db.String(200), nullable=False, default='')
    action = db.Column(db.String(10), nullable=False, default='add')
    risk_level = db.Column(db.String(20), nullable=False, default='medium')
    reason = db.Column(db.Text, nullable=True)
    approved = db.Column(db.Boolean, nullable=False, default=False)
    executed = db.Column(db.Boolean, nullable=False, default=False)
    execution_result_json = db.Column(db.Text, nullable=True)
