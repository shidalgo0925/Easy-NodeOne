"""
Semilla idempotente: superadministrador de plataforma (rol SA).

- Asegura tablas/semilla RBAC (migrate_rbac_tables).
- Si existe el usuario PLATFORM_SA_EMAIL: is_admin, activo, verificado, rol SA.
- El rol SA no se asigna desde la API web (solo bootstrap o promote_superuser.py).

PLATFORM_SA_EMAIL:
  - Si la variable no está definida → se usa shidalgo@easytech.services
  - Si está definida y vacía → no hace nada (deshabilitar semilla)
  - Si tiene valor → ese correo
"""

from __future__ import annotations

import os


def _platform_sa_email() -> str | None:
    if 'PLATFORM_SA_EMAIL' in os.environ:
        raw = (os.environ.get('PLATFORM_SA_EMAIL') or '').strip()
        if not raw:
            return None
        return raw.lower()
    return 'shidalgo@easytech.services'


def ensure_platform_sa_user(printfn=print) -> None:
    from migrate_rbac_tables import run_migration
    from app import db, User, Role

    email = _platform_sa_email()
    if email is None:
        printfn('PLATFORM_SA_EMAIL deshabilitado (vacío); omitiendo ensure_platform_sa_user.')
        return

    run_migration()

    sa = Role.query.filter_by(code='SA').first()
    if not sa:
        printfn('ensure_platform_sa_user: no hay rol SA tras run_migration; omitiendo.')
        return

    u = User.query.filter(db.func.lower(User.email) == email).first()
    if not u:
        printfn(
            f'ensure_platform_sa_user: usuario {email} no existe aún; '
            'crear con registro, create_admin_user.py o seed_initial_admin.py; '
            'en el próximo arranque se aplicará SA automáticamente.'
        )
        return

    changed = False
    if not u.is_admin:
        u.is_admin = True
        changed = True
    if not u.is_active:
        u.is_active = True
        changed = True
    if not u.email_verified:
        u.email_verified = True
        changed = True

    has_sa = u.roles.filter_by(id=sa.id).first() is not None
    if not has_sa:
        u.roles.append(sa)
        changed = True

    if changed:
        db.session.commit()
        printfn(f'ensure_platform_sa_user: actualizado {email} (is_admin + rol SA).')
    else:
        printfn(f'ensure_platform_sa_user: {email} ya tenía SA e is_admin.')
