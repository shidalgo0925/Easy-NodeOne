"""Membresía usuario ↔ organización (multi-empresa)."""
from __future__ import annotations


def active_organization_ids_for_user(user) -> set[int]:
    """
    IDs de organizaciones activas para el usuario.
    Prioridad: filas en user_organization; si no hay ninguna, compat con user.organization_id.
    """
    from models.users import UserOrganization

    out: set[int] = set()
    if user is None:
        return out
    try:
        uid = int(getattr(user, 'id', 0) or 0)
    except (TypeError, ValueError):
        return out
    if uid < 1:
        return out
    for row in UserOrganization.query.filter_by(user_id=uid, status='active').all():
        try:
            out.add(int(row.organization_id))
        except (TypeError, ValueError):
            continue
    if out:
        return out
    raw = getattr(user, 'organization_id', None)
    try:
        oid = int(raw) if raw is not None else 0
    except (TypeError, ValueError):
        oid = 0
    if oid > 0:
        out.add(oid)
    return out


def ensure_membership(user_id: int, organization_id: int, role: str = 'user') -> None:
    """Crea o reactiva vínculo usuario–organización (idempotente)."""
    from nodeone.core.db import db
    from models.users import UserOrganization

    try:
        uid = int(user_id)
        oid = int(organization_id)
    except (TypeError, ValueError):
        return
    if uid < 1 or oid < 1:
        return
    row = UserOrganization.query.filter_by(user_id=uid, organization_id=oid).first()
    if row is not None:
        if row.status != 'active':
            row.status = 'active'
        if role and row.role != role:
            row.role = role
        return
    db.session.add(
        UserOrganization(
            user_id=uid,
            organization_id=oid,
            role=role or 'user',
            status='active',
        )
    )


def user_has_active_membership(user, organization_id: int) -> bool:
    try:
        oid = int(organization_id)
    except (TypeError, ValueError):
        return False
    return oid in active_organization_ids_for_user(user)


def user_ids_query_in_organization(organization_id: int):
    """
    Consulta ORM de User.id: usuarios que pertenecen a la organización
    (fila activa en user_organization o columna legacy user.organization_id).
    """
    from sqlalchemy import false as sql_false, or_

    from nodeone.core.db import db
    from models.users import User, UserOrganization

    try:
        oid = int(organization_id)
    except (TypeError, ValueError):
        return db.session.query(User.id).filter(sql_false())
    sub = db.session.query(UserOrganization.user_id).filter(
        UserOrganization.organization_id == oid,
        UserOrganization.status == 'active',
    )
    return db.session.query(User.id).filter(
        or_(User.organization_id == oid, User.id.in_(sub)),
    )


def user_in_org_clause(user_model, organization_id):
    """
    Expresión para filter()/join: filas de user_model cuya cuenta pertenece a organization_id.
    user_model: clase mapeada User (o alias) con .id y .organization_id.
    """
    from sqlalchemy import or_

    from nodeone.core.db import db
    from models.users import UserOrganization

    try:
        oid = int(organization_id)
    except (TypeError, ValueError):
        return user_model.id == 0
    sub = db.session.query(UserOrganization.user_id).filter(
        UserOrganization.organization_id == oid,
        UserOrganization.status == 'active',
    )
    return or_(user_model.organization_id == oid, user_model.id.in_(sub))
