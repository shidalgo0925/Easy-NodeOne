#!/usr/bin/env python3
"""
Asigna el rol AD (Administrador) a todos los usuarios que tienen is_admin=True,
para que tengan permisos RBAC además del flag legacy.
Ejecutar desde el directorio del proyecto: python3 backend/assign_role_ad_to_admin_users.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(__file__))


def run():
    from app import app, db, User, Role

    with app.app_context():
        ad = Role.query.filter_by(code='AD').first()
        if not ad:
            print("No se encontró el rol AD. Ejecuta antes: python3 backend/migrate_rbac_tables.py")
            return False

        admins = User.query.filter_by(is_admin=True).all()
        if not admins:
            print("No hay usuarios con is_admin=True.")
            return True

        added = 0
        for user in admins:
            if user.roles.filter_by(id=ad.id).first() is None:
                user.roles.append(ad)
                added += 1
                print(f"  Rol AD asignado a usuario {user.id} ({user.email})")

        if added:
            db.session.commit()
            print(f"Se asignó el rol AD a {added} usuario(s).")
        else:
            print("Todos los administradores ya tenían el rol AD.")
        return True


if __name__ == '__main__':
    try:
        ok = run()
        sys.exit(0 if ok else 1)
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
