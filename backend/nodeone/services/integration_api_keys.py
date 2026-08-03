"""Auth y ciclo de vida de Integration API Keys (hash + org)."""

from __future__ import annotations

import hashlib
import os
import secrets
from datetime import datetime
from typing import Any

from models.integration_api import IntegrationApiAccessLog, IntegrationApiKey
from nodeone.core.db import db
from nodeone.modules.membership_verification.catalog import PERMISSION_API_MANAGER


def hash_api_key(raw: str) -> str:
    return hashlib.sha256((raw or '').strip().encode('utf-8')).hexdigest()


def generate_raw_api_key() -> tuple[str, str, str]:
    """Retorna (raw, prefix, hash). Raw solo se muestra una vez al crear."""
    raw = 'enk_' + secrets.token_urlsafe(32)
    prefix = raw[:12]
    return raw, prefix, hash_api_key(raw)


def extract_x_api_key(request) -> str:
    return (request.headers.get('X-API-Key') or '').strip()


def resolve_org_id_from_env() -> int | None:
    raw = (os.environ.get('MEMBER_LOOKUP_ORG_ID') or '').strip()
    if raw.isdigit():
        return int(raw)
    try:
        from utils.organization import default_organization_id

        return int(default_organization_id())
    except Exception:
        return None


def authenticate_api_key(raw_key: str) -> tuple[IntegrationApiKey | None, str | None]:
    """
    Valida X-API-Key contra BD.
    Returns (row, error_code) error_code: missing | unauthorized | not_configured
    """
    try:
        ensure_integration_api_tables()
    except Exception:
        pass

    provided = (raw_key or '').strip()
    try:
        has_any = IntegrationApiKey.query.limit(1).first() is not None
    except Exception:
        # Tabla aún no disponible
        env_key = (os.environ.get('MEMBER_LOOKUP_API_KEY') or '').strip()
        if env_key and provided and secrets.compare_digest(provided, env_key):
            return _ephemeral_env_key(), None
        if not env_key:
            return None, 'not_configured'
        return None, 'unauthorized'

    if not provided:
        env_key = (os.environ.get('MEMBER_LOOKUP_API_KEY') or '').strip()
        if not env_key and not has_any:
            return None, 'not_configured'
        return None, 'unauthorized'

    try:
        row = IntegrationApiKey.query.filter_by(key_hash=hash_api_key(provided)).first()
    except Exception:
        row = None

    if row is None:
        env_key = (os.environ.get('MEMBER_LOOKUP_API_KEY') or '').strip()
        if env_key and secrets.compare_digest(provided, env_key):
            return _ephemeral_env_key(), None
        return None, 'unauthorized'
    if (row.status or '').strip().lower() != 'active':
        return None, 'unauthorized'
    return row, None


def _ephemeral_env_key() -> IntegrationApiKey:
    """Objeto no persistido para auth vía .env (compat Sprint A)."""
    oid = resolve_org_id_from_env() or 1
    row = IntegrationApiKey(
        id=0,
        organization_id=int(oid),
        name='env:MEMBER_LOOKUP_API_KEY',
        description='Compatibilidad .env',
        key_prefix='env',
        key_hash='env',
        status='active',
    )
    return row


def touch_key_usage(row: IntegrationApiKey) -> None:
    if row is None or not getattr(row, 'id', None):
        return
    try:
        rid = int(row.id)
    except (TypeError, ValueError):
        return
    if rid < 1:
        return
    db_row = IntegrationApiKey.query.get(rid)
    if db_row is None:
        return
    db_row.last_used_at = datetime.utcnow()
    db.session.commit()


def log_access(
    *,
    organization_id: int,
    api_key_id: int | None,
    endpoint: str,
    http_status: int,
    result: str | None,
    duration_ms: int | None,
    client_ip: str | None,
) -> None:
    try:
        kid = int(api_key_id) if api_key_id and int(api_key_id) > 0 else None
    except (TypeError, ValueError):
        kid = None
    db.session.add(
        IntegrationApiAccessLog(
            organization_id=int(organization_id),
            api_key_id=kid,
            endpoint=(endpoint or '')[:200],
            http_status=int(http_status),
            result=(result or None),
            duration_ms=duration_ms,
            client_ip=(client_ip or None),
        )
    )
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()


def create_api_key(
    *,
    organization_id: int,
    name: str,
    description: str | None = None,
    created_by_user_id: int | None = None,
) -> tuple[IntegrationApiKey, str]:
    raw, prefix, khash = generate_raw_api_key()
    row = IntegrationApiKey(
        organization_id=int(organization_id),
        name=(name or 'API Key').strip()[:120],
        description=(description or '').strip()[:500] or None,
        key_prefix=prefix,
        key_hash=khash,
        status='active',
        created_by_user_id=created_by_user_id,
    )
    db.session.add(row)
    db.session.commit()
    return row, raw


def ensure_api_manager_permission() -> None:
    from models.users import Permission

    if Permission.query.filter_by(code=PERMISSION_API_MANAGER).first() is not None:
        return
    db.session.add(
        Permission(code=PERMISSION_API_MANAGER, name='API Manager (API Center)')
    )
    db.session.commit()


def ensure_integration_api_tables() -> None:
    IntegrationApiKey.__table__.create(db.engine, checkfirst=True)
    IntegrationApiAccessLog.__table__.create(db.engine, checkfirst=True)


def bootstrap_env_key_into_db_if_empty() -> dict[str, Any]:
    """Si hay MEMBER_LOOKUP_API_KEY y no hay keys, crea una fila (hash)."""
    ensure_integration_api_tables()
    if IntegrationApiKey.query.limit(1).first() is not None:
        return {'created': False, 'reason': 'keys_exist'}
    env_key = (os.environ.get('MEMBER_LOOKUP_API_KEY') or '').strip()
    if not env_key:
        return {'created': False, 'reason': 'no_env_key'}
    oid = resolve_org_id_from_env()
    if oid is None:
        return {'created': False, 'reason': 'no_org'}
    row = IntegrationApiKey(
        organization_id=int(oid),
        name='Odoo / MEMBER_LOOKUP_API_KEY',
        description='Importada desde .env al bootstrap',
        key_prefix=env_key[:12],
        key_hash=hash_api_key(env_key),
        status='active',
    )
    db.session.add(row)
    db.session.commit()
    return {'created': True, 'id': row.id}
