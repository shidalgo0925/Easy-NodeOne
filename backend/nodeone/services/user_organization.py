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


def deactivate_membership(user_id: int, organization_id: int) -> None:
    """Marca el vínculo como inactive (no borra la fila)."""
    from models.users import UserOrganization

    try:
        uid = int(user_id)
        oid = int(organization_id)
    except (TypeError, ValueError):
        return
    if uid < 1 or oid < 1:
        return
    row = UserOrganization.query.filter_by(user_id=uid, organization_id=oid).first()
    if row is not None and row.status == 'active':
        row.status = 'inactive'


def sync_user_organization_memberships(
    user_id: int,
    organization_ids: set[int] | list[int],
    *,
    primary_organization_id: int | None = None,
) -> int:
    """
    Deja activas solo las organizaciones indicadas.
    Actualiza User.organization_id (compañía principal).
    Devuelve el id de organización principal.
    """
    from models.users import User, UserOrganization

    try:
        uid = int(user_id)
    except (TypeError, ValueError):
        return 0
    if uid < 1:
        return 0

    wanted: set[int] = set()
    for raw in organization_ids or []:
        try:
            oid = int(raw)
        except (TypeError, ValueError):
            continue
        if oid >= 1:
            wanted.add(oid)

    u = User.query.get(uid)
    current: set[int] = set()
    for row in UserOrganization.query.filter_by(user_id=uid, status='active').all():
        try:
            current.add(int(row.organization_id))
        except (TypeError, ValueError):
            continue
    if not current and u is not None:
        try:
            home = int(getattr(u, 'organization_id', None) or 0)
        except (TypeError, ValueError):
            home = 0
        if home >= 1:
            current.add(home)
            ensure_membership(uid, home)

    if not wanted:
        if u is not None:
            try:
                keep = int(getattr(u, 'organization_id', None) or 0)
            except (TypeError, ValueError):
                keep = 0
            if keep >= 1:
                wanted.add(keep)
        if not wanted and current:
            wanted.add(min(current))

    for oid in wanted - current:
        ensure_membership(uid, oid)
    for oid in current - wanted:
        deactivate_membership(uid, oid)

    primary = None
    if primary_organization_id is not None:
        try:
            primary = int(primary_organization_id)
        except (TypeError, ValueError):
            primary = None
    if primary is None or primary not in wanted:
        if u is not None:
            try:
                home = int(getattr(u, 'organization_id', None) or 0)
            except (TypeError, ValueError):
                home = 0
            if home in wanted:
                primary = home
        if primary is None or primary not in wanted:
            primary = min(wanted) if wanted else None

    if primary is not None:
        ensure_membership(uid, primary)
        if u is not None:
            u.organization_id = primary
            if hasattr(u, 'last_selected_organization_id'):
                u.last_selected_organization_id = primary
        return int(primary)
    return 0


def user_has_active_membership(user, organization_id: int) -> bool:
    try:
        oid = int(organization_id)
    except (TypeError, ValueError):
        return False
    return oid in active_organization_ids_for_user(user)


def user_can_switch_organization(user) -> bool:
    """
    True si el usuario puede cambiar de empresa sin cerrar sesión.
    Admin de plataforma: siempre. Miembro: solo si tiene 2+ organizaciones activas.
    """
    if user is None or not getattr(user, 'is_authenticated', False):
        return False
    if getattr(user, 'is_admin', False):
        return True
    return len(active_organization_ids_for_user(user)) > 1


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
