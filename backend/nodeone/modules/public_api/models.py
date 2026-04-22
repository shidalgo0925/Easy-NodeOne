"""Tablas auxiliares para API pública del landing (idempotencia, rate limit)."""

from datetime import datetime

from nodeone.core.db import db


class LandingPublicIdempotency(db.Model):
    """Evita doble alta cuando el cliente reenvía el mismo Idempotency-Key."""

    __tablename__ = 'landing_public_idempotency'

    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(db.Integer, nullable=False, index=True)
    idempotency_key = db.Column(db.String(128), nullable=False)
    response_status = db.Column(db.Integer, nullable=False)
    response_body = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('organization_id', 'idempotency_key', name='uq_landing_idem_org_key'),
    )


class LandingApiRateBucket(db.Model):
    """Contador por IP y minuto UTC (compatible con varios workers Gunicorn)."""

    __tablename__ = 'landing_api_rate_bucket'

    id = db.Column(db.Integer, primary_key=True)
    ip_address = db.Column(db.String(64), nullable=False)
    bucket_minute = db.Column(db.String(12), nullable=False)  # YYYYMMDDHHMM
    kind = db.Column(db.String(8), nullable=False, default='post')  # get | post
    hit_count = db.Column(db.Integer, nullable=False, default=0)

    __table_args__ = (
        db.UniqueConstraint(
            'ip_address', 'bucket_minute', 'kind', name='uq_landing_rate_ip_bucket_kind'
        ),
    )
