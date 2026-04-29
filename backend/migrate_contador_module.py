#!/usr/bin/env python3
"""Crea tablas del módulo Contador y semilla RBAC (permisos + roles CAD/CSU/COP)."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import insert

from app import app, db  # noqa: E402
from models.contador import (  # noqa: E402
    ContadorCaptureLog,
    ContadorCountLine,
    ContadorExportLog,
    ContadorProductTemplate,
    ContadorProductVariant,
    ContadorSession,
)
from models.users import Permission, Role, role_permission_table, user_role_table  # noqa: E402


PERMS = [
    ('contador.admin', 'Contador administrador'),
    ('contador.review', 'Contador revisión'),
    ('contador.capture', 'Contador captura'),
]

ROLES_CONTADOR = [
    ('CAD', 'Contador administrador'),
    ('CSU', 'Contador supervisor'),
    ('COP', 'Contador operador'),
]


def _ensure_permission(code: str, name: str) -> int:
    p = Permission.query.filter_by(code=code).first()
    if p:
        return int(p.id)
    db.session.add(Permission(code=code, name=name))
    db.session.flush()
    return int(Permission.query.filter_by(code=code).first().id)


def _ensure_role(code: str, name: str) -> int:
    r = Role.query.filter_by(code=code).first()
    if r:
        return int(r.id)
    db.session.add(Role(code=code, name=name))
    db.session.flush()
    return int(Role.query.filter_by(code=code).first().id)


def _link_role_perm(role_id: int, perm_id: int) -> None:
    from sqlalchemy import and_

    ex = (
        db.session.query(role_permission_table)
        .filter(
            and_(
                role_permission_table.c.role_id == role_id,
                role_permission_table.c.permission_id == perm_id,
            )
        )
        .first()
    )
    if ex is None:
        db.session.execute(
            insert(role_permission_table).values(role_id=role_id, permission_id=perm_id)
        )


def main():
    with app.app_context():
        for model in (
            ContadorProductTemplate,
            ContadorProductVariant,
            ContadorSession,
            ContadorCountLine,
            ContadorCaptureLog,
            ContadorExportLog,
        ):
            model.__table__.create(db.engine, checkfirst=True)
        print('✅ Tablas contador creadas')

        perm_ids = {}
        for code, name in PERMS:
            pid = _ensure_permission(code, name)
            perm_ids[code] = pid
        db.session.commit()
        print('✅ Permisos contador')

        r_cad = _ensure_role('CAD', ROLES_CONTADOR[0][1])
        r_csu = _ensure_role('CSU', ROLES_CONTADOR[1][1])
        r_cop = _ensure_role('COP', ROLES_CONTADOR[2][1])
        db.session.commit()

        # CAD: todos
        for code in perm_ids:
            _link_role_perm(r_cad, perm_ids[code])
        # CSU: revisión
        _link_role_perm(r_csu, perm_ids['contador.review'])
        # COP: captura
        _link_role_perm(r_cop, perm_ids['contador.capture'])
        db.session.commit()
        print('✅ Roles CAD/CSU/COP vinculados')

        # SA: todos los permisos contador
        sa = Role.query.filter_by(code='SA').first()
        if sa:
            for code in perm_ids:
                _link_role_perm(int(sa.id), perm_ids[code])
            db.session.commit()
            print('✅ Rol SA: permisos contador añadidos')
        else:
            print('⚠️ Rol SA no encontrado; asigná permisos a mano si aplica')

        print('Listo. Asigná roles CAD/CSU/COP a usuarios en /admin/users o vía user_role.')


if __name__ == '__main__':
    main()
