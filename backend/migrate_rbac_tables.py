#!/usr/bin/env python3
"""
Migración RBAC: crea tablas role, permission, role_permission, user_role
y carga semilla de roles y permisos según matriz FASE 2.
Ejecutar desde el directorio del proyecto: python backend/migrate_rbac_tables.py

Si las tablas ya existen pero están vacías (sin filas en role), aplica solo la semilla.
"""

import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))

from sqlalchemy import MetaData, Table, Column, Integer, String, Text, DateTime, ForeignKey, select, insert, text
from sqlalchemy import inspect


def _seed_rbac_core(conn, trans, role_t, permission_t, role_permission_t):
    """Inserta permisos, roles y matriz role_permission (SA, AD, ST, TE)."""
    permissions = [
        'users.view', 'users.create', 'users.update', 'users.delete', 'users.assign_roles', 'users.suspend',
        'roles.view', 'roles.assign', 'roles.create', 'roles.update', 'roles.delete', 'permissions.view',
        'services.view', 'services.create', 'services.update', 'services.delete',
        'memberships.view', 'memberships.assign', 'memberships.suspend',
        'payments.view', 'payments.manage', 'payments.refund',
        'reports.view', 'reports.export',
        'integrations.view', 'integrations.manage', 'api.keys.create', 'api.keys.revoke',
        'system.settings.view', 'system.settings.update', 'audit.logs.view',
    ]

    for code in permissions:
        name = code.replace('.', ' ').replace('_', ' ').title()
        conn.execute(insert(permission_t).values(code=code, name=name))
    print(f"Insertados {len(permissions)} permisos.")

    roles_data = [
        ('SA', 'SuperAdministrador'),
        ('AD', 'Administrador'),
        ('ST', 'Staff / Operaciones'),
        ('TE', 'Técnico / Integraciones'),
        ('MI', 'Miembro'),
        ('IN', 'Invitado'),
    ]
    for code, name in roles_data:
        conn.execute(insert(role_t).values(code=code, name=name))
    print(f"Insertados {len(roles_data)} roles.")

    r = conn.execute(select(role_t))
    role_ids = {row[1]: row[0] for row in r}
    r = conn.execute(select(permission_t))
    perm_ids = {row[1]: row[0] for row in r}

    for code, pid in perm_ids.items():
        conn.execute(insert(role_permission_t).values(role_id=role_ids['SA'], permission_id=pid))
    print("Rol SA: todos los permisos asignados.")

    ad_exclude = {'users.delete', 'roles.delete', 'system.settings.update'}
    for code, pid in perm_ids.items():
        if code not in ad_exclude:
            conn.execute(insert(role_permission_t).values(role_id=role_ids['AD'], permission_id=pid))
    print("Rol AD: permisos asignados (sin users.delete, roles.delete, system.settings.update).")

    st_perms = {'users.view', 'users.create', 'users.update', 'services.view', 'memberships.view', 'memberships.assign', 'payments.view', 'reports.view', 'integrations.view'}
    for code in st_perms:
        if code in perm_ids:
            conn.execute(insert(role_permission_t).values(role_id=role_ids['ST'], permission_id=perm_ids[code]))
    print("Rol ST: permisos de operaciones asignados.")

    te_perms = {'users.view', 'services.view', 'integrations.view', 'integrations.manage', 'api.keys.create', 'api.keys.revoke', 'audit.logs.view'}
    for code in te_perms:
        if code in perm_ids:
            conn.execute(insert(role_permission_t).values(role_id=role_ids['TE'], permission_id=perm_ids[code]))
    print("Rol TE: permisos de integraciones asignados.")


def run_migration():
    from app import app, db

    with app.app_context():
        inspector = inspect(db.engine)
        existing = inspector.get_table_names()

        rbac_tables_ok = 'role' in existing and 'permission' in existing

        if rbac_tables_ok:
            with db.engine.connect() as c:
                nroles = c.execute(text('SELECT COUNT(*) FROM role')).scalar()
            if nroles and int(nroles) > 0:
                print("Tablas RBAC ya existen y tienen datos. Omitiendo.")
                return True
            print("Tablas RBAC existen pero sin roles; aplicando semilla...")
            metadata = MetaData()
            metadata.reflect(bind=db.engine, only=['role', 'permission', 'role_permission'])
            role_t = metadata.tables['role']
            permission_t = metadata.tables['permission']
            role_permission_t = metadata.tables['role_permission']
            conn = db.engine.connect()
            trans = conn.begin()
            try:
                _seed_rbac_core(conn, trans, role_t, permission_t, role_permission_t)
                trans.commit()
            except Exception:
                trans.rollback()
                raise
            finally:
                conn.close()
            print("Semilla RBAC completada correctamente.")
            return True

        metadata = MetaData()

        role_t = Table(
            'role', metadata,
            Column('id', Integer, primary_key=True, autoincrement=True),
            Column('code', String(20), unique=True, nullable=False),
            Column('name', String(100), nullable=False),
            Column('description', Text),
            Column('created_at', DateTime, default=datetime.utcnow),
        )

        permission_t = Table(
            'permission', metadata,
            Column('id', Integer, primary_key=True, autoincrement=True),
            Column('code', String(80), unique=True, nullable=False),
            Column('name', String(120), nullable=False),
            Column('description', Text),
            Column('created_at', DateTime, default=datetime.utcnow),
        )

        role_permission_t = Table(
            'role_permission', metadata,
            Column('role_id', Integer, ForeignKey('role.id', ondelete='CASCADE'), primary_key=True),
            Column('permission_id', Integer, ForeignKey('permission.id', ondelete='CASCADE'), primary_key=True),
        )

        user_role_t = Table(
            'user_role', metadata,
            Column('user_id', Integer, primary_key=True),
            Column('role_id', Integer, ForeignKey('role.id', ondelete='CASCADE'), primary_key=True),
            Column('assigned_at', DateTime, default=datetime.utcnow),
            Column('assigned_by_id', Integer, nullable=True),
        )

        metadata.create_all(db.engine)
        print("Tablas RBAC creadas: role, permission, role_permission, user_role")

        conn = db.engine.connect()
        trans = conn.begin()
        try:
            _seed_rbac_core(conn, trans, role_t, permission_t, role_permission_t)
            trans.commit()
        except Exception:
            trans.rollback()
            raise
        finally:
            conn.close()

        print("Migración RBAC completada correctamente.")
        return True


if __name__ == '__main__':
    try:
        ok = run_migration()
        sys.exit(0 if ok else 1)
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
