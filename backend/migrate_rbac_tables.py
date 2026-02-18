#!/usr/bin/env python3
"""
Migración RBAC: crea tablas role, permission, role_permission, user_role
y carga semilla de roles y permisos según matriz FASE 2.
Ejecutar desde el directorio del proyecto: python backend/migrate_rbac_tables.py
"""

import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))

from sqlalchemy import MetaData, Table, Column, Integer, String, Text, DateTime, ForeignKey, select, insert
from sqlalchemy import inspect

def run_migration():
    from app import app, db

    with app.app_context():
        inspector = inspect(db.engine)
        existing = inspector.get_table_names()

        if 'role' in existing and 'permission' in existing:
            print("Tablas RBAC ya existen. Omitiendo creación.")
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

        # user_id y assigned_by_id referencian user.id (tabla en otro metadata); sin FK en esta migración
        user_role_t = Table(
            'user_role', metadata,
            Column('user_id', Integer, primary_key=True),
            Column('role_id', Integer, ForeignKey('role.id', ondelete='CASCADE'), primary_key=True),
            Column('assigned_at', DateTime, default=datetime.utcnow),
            Column('assigned_by_id', Integer, nullable=True),
        )

        metadata.create_all(db.engine)
        print("Tablas RBAC creadas: role, permission, role_permission, user_role")

        # Semilla: permisos
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

        conn = db.engine.connect()
        trans = conn.begin()

        try:
            for code in permissions:
                name = code.replace('.', ' ').replace('_', ' ').title()
                conn.execute(insert(permission_t).values(code=code, name=name))
            print(f"Insertados {len(permissions)} permisos.")

            # Semilla: roles
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

            # Obtener IDs de roles y permisos
            r = conn.execute(select(role_t))
            role_ids = {row[1]: row[0] for row in r}  # code -> id
            r = conn.execute(select(permission_t))
            perm_ids = {row[1]: row[0] for row in r}  # code -> id

            # SA: todos los permisos
            for code, pid in perm_ids.items():
                conn.execute(insert(role_permission_t).values(role_id=role_ids['SA'], permission_id=pid))
            print("Rol SA: todos los permisos asignados.")

            # AD: todos excepto users.delete, roles.delete, system.settings.update
            ad_exclude = {'users.delete', 'roles.delete', 'system.settings.update'}
            for code, pid in perm_ids.items():
                if code not in ad_exclude:
                    conn.execute(insert(role_permission_t).values(role_id=role_ids['AD'], permission_id=pid))
            print("Rol AD: permisos asignados (sin users.delete, roles.delete, system.settings.update).")

            # ST: subset operaciones
            st_perms = {'users.view', 'users.create', 'users.update', 'services.view', 'memberships.view', 'memberships.assign', 'payments.view', 'reports.view', 'integrations.view'}
            for code in st_perms:
                if code in perm_ids:
                    conn.execute(insert(role_permission_t).values(role_id=role_ids['ST'], permission_id=perm_ids[code]))
            print("Rol ST: permisos de operaciones asignados.")

            # TE: integrations, api.keys, audit.logs
            te_perms = {'users.view', 'services.view', 'integrations.view', 'integrations.manage', 'api.keys.create', 'api.keys.revoke', 'audit.logs.view'}
            for code in te_perms:
                if code in perm_ids:
                    conn.execute(insert(role_permission_t).values(role_id=role_ids['TE'], permission_id=perm_ids[code]))
            print("Rol TE: permisos de integraciones asignados.")

            # MI e IN: sin permisos admin (acceso a recursos propios vía lógica de negocio)
            trans.commit()
        except Exception as e:
            trans.rollback()
            raise e
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
