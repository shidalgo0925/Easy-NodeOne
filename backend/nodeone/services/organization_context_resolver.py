"""ADR-029 — Organization Context Resolver V2 (pending post-/start + orden)."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

PENDING_TTL_DAYS = 7


def ensure_pending_initial_organization_columns() -> None:
    """DDL idempotente: user.pending_initial_organization_id / _at."""
    from sqlalchemy import text

    from nodeone.core.db import db

    bind = db.session.get_bind()
    dialect = (bind.dialect.name if bind is not None else '').lower()
    try:
        if dialect == 'sqlite':
            rows = db.session.execute(text('PRAGMA table_info("user")')).fetchall()
            cols = {str(r[1]) for r in rows}
        else:
            rows = db.session.execute(
                text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_name = 'user'"
                )
            ).fetchall()
            cols = {str(r[0]) for r in rows}
        if 'pending_initial_organization_id' not in cols:
            if dialect == 'sqlite':
                db.session.execute(
                    text('ALTER TABLE "user" ADD COLUMN pending_initial_organization_id INTEGER')
                )
            else:
                db.session.execute(
                    text(
                        'ALTER TABLE "user" ADD COLUMN pending_initial_organization_id INTEGER '
                        'REFERENCES saas_organization(id) ON DELETE SET NULL'
                    )
                )
        if 'pending_initial_organization_at' not in cols:
            db.session.execute(
                text('ALTER TABLE "user" ADD COLUMN pending_initial_organization_at TIMESTAMP')
            )
        db.session.commit()
    except Exception:
        db.session.rollback()


def set_pending_initial_organization(user_id: int, organization_id: int) -> None:
    """Marca org creada en /start para el primer login (ADR-029)."""
    from models.users import User
    from nodeone.core.db import db

    ensure_pending_initial_organization_columns()
    u = User.query.get(int(user_id))
    if u is None:
        return
    u.pending_initial_organization_id = int(organization_id)
    u.pending_initial_organization_at = datetime.utcnow()
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()


def peek_pending_initial_organization(user: Any) -> int | None:
    """Devuelve org_id pendiente vigente o None (no consume)."""
    if user is None:
        return None
    try:
        oid = getattr(user, 'pending_initial_organization_id', None)
        oid = int(oid) if oid is not None else None
    except (TypeError, ValueError):
        return None
    if not oid or oid < 1:
        return None
    at = getattr(user, 'pending_initial_organization_at', None)
    if at is not None:
        try:
            if datetime.utcnow() - at > timedelta(days=PENDING_TTL_DAYS):
                return None
        except Exception:
            pass
    return oid


def consume_pending_initial_organization(user: Any) -> int | None:
    """Lee y limpia pending si está vigente. Retorna org_id o None."""
    from models.users import User
    from nodeone.core.db import db

    oid = peek_pending_initial_organization(user)
    if oid is None:
        # Limpiar expirados
        try:
            uid = int(getattr(user, 'id', 0) or 0)
            if uid and getattr(user, 'pending_initial_organization_id', None):
                u = User.query.get(uid)
                if u is not None:
                    u.pending_initial_organization_id = None
                    u.pending_initial_organization_at = None
                    db.session.commit()
        except Exception:
            db.session.rollback()
        return None

    try:
        uid = int(getattr(user, 'id', 0) or 0)
        u = User.query.get(uid) if uid else None
        if u is not None:
            u.pending_initial_organization_id = None
            u.pending_initial_organization_at = None
            db.session.commit()
        # Mantener objeto en memoria coherente
        try:
            user.pending_initial_organization_id = None
            user.pending_initial_organization_at = None
        except Exception:
            pass
    except Exception:
        db.session.rollback()
        return None
    return oid
