"""Permiso RBAC analytics.view: creación idempotente y asignación a roles operativos."""

from __future__ import annotations

PERM_CODE = 'analytics.view'
PERM_NAME = 'Analítica y tableros KPI'
# Mismos perfiles que suelen ver reportes operativos (semilla ST + administradores).
ROLE_CODES_WITH_ANALYTICS = ('SA', 'AD', 'ST')


def ensure_analytics_view_permission(db, printfn=print) -> None:
    """
    Inserta `analytics.view` si no existe y lo enlaza a SA, AD y ST.
    Idempotente (seguro en cada arranque / bootstrap).
    """
    from sqlalchemy import insert, select

    from models.associations import role_permission_table
    from models.users import Permission, Role

    p = Permission.query.filter_by(code=PERM_CODE).first()
    if p is None:
        p = Permission(code=PERM_CODE, name=PERM_NAME)
        db.session.add(p)
        db.session.commit()
        printfn(f'✅ Permiso {PERM_CODE} creado')
    pid = p.id

    for rcode in ROLE_CODES_WITH_ANALYTICS:
        role = Role.query.filter_by(code=rcode).first()
        if not role:
            continue
        existing = {
            row[0]
            for row in db.session.execute(
                select(role_permission_table.c.permission_id).where(role_permission_table.c.role_id == role.id)
            )
        }
        if pid not in existing:
            db.session.execute(insert(role_permission_table).values(role_id=role.id, permission_id=pid))
            printfn(f'📋 Rol {rcode}: asignado {PERM_CODE}')
    db.session.commit()
