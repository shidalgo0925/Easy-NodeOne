#!/usr/bin/env python3
"""
FASE 5: Añade el permiso roles.assign si no existe y lo asigna a SA y AD.
Ejecutar desde el directorio del proyecto: python backend/add_roles_assign_permission.py
"""
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

def run():
    from app import app, db
    from app import Permission, Role, role_permission_table

    with app.app_context():
        perm = Permission.query.filter_by(code='roles.assign').first()
        if not perm:
            perm = Permission(code='roles.assign', name='Assign roles')
            db.session.add(perm)
            db.session.flush()
            print("Permiso roles.assign creado.")
        else:
            print("Permiso roles.assign ya existe.")

        sa = Role.query.filter_by(code='SA').first()
        ad = Role.query.filter_by(code='AD').first()
        if not sa or not ad:
            print("Roles SA o AD no encontrados. Abortando.")
            return False

        for role in (sa, ad):
            exists = db.session.execute(
                db.select(role_permission_table).where(
                    role_permission_table.c.role_id == role.id,
                    role_permission_table.c.permission_id == perm.id
                )
            ).first()
            if not exists:
                db.session.execute(
                    role_permission_table.insert().values(
                        role_id=role.id,
                        permission_id=perm.id
                    )
                )
                print(f"roles.assign asignado al rol {role.code}.")
        db.session.commit()
        print("Listo.")
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
