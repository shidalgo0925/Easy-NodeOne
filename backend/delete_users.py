#!/usr/bin/env python3
"""
Script para eliminar usuarios y todas sus transacciones relacionadas
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db, User

# IDs de usuarios a eliminar (Lista de Usuarios: 47, 44, 9, 4)
USER_IDS_TO_DELETE = [47, 44, 9, 4]

# Emails (legacy): si se quieren eliminar por email, añadir aquí
USERS_TO_DELETE_BY_EMAIL = []


def _delete_user_and_related(user):
    """Elimina un usuario y todas sus relaciones. user ya cargado."""
    from nodeone.services.user_deletion import delete_user_and_related

    user_name = f"{user.first_name} {user.last_name}"
    email = user.email
    print(f"\n📋 Eliminando usuario: {user_name} ({email}) ID: {user.id}")

    try:
        delete_user_and_related(user, db=db)
        db.session.commit()
        print(f"   ✅ Usuario {user_name} eliminado exitosamente")
        return True
    except Exception as e:
        db.session.rollback()
        print(f"   ❌ Error al eliminar usuario: {e}")
        import traceback
        traceback.print_exc()
        return False


def delete_user_by_id(user_id):
    """Elimina usuario por ID."""
    user = User.query.get(user_id)
    if not user:
        print(f"⚠️  Usuario no encontrado ID: {user_id}")
        return False
    return _delete_user_and_related(user)


def delete_user_and_transactions(email):
    """Elimina usuario por email."""
    user = User.query.filter_by(email=email).first()
    if not user:
        print(f"⚠️  Usuario no encontrado: {email}")
        return False
    return _delete_user_and_related(user)


def main():
    """Función principal"""
    to_delete_ids = USER_IDS_TO_DELETE
    to_delete_emails = USERS_TO_DELETE_BY_EMAIL
    total = len(to_delete_ids) + len(to_delete_emails)
    if total == 0:
        print("No hay usuarios configurados para eliminar (USER_IDS_TO_DELETE / USERS_TO_DELETE_BY_EMAIL).")
        return

    print("=" * 70)
    print("ELIMINACIÓN DE USUARIOS Y TRANSACCIONES")
    print("=" * 70)
    print(f"\n📋 Usuarios a eliminar: {total}")
    for uid in to_delete_ids:
        print(f"   - ID {uid}")
    for email in to_delete_emails:
        print(f"   - {email}")
    print("\n⚠️  ADVERTENCIA: Esta acción eliminará permanentemente usuarios y datos relacionados.")
    print("⚠️  Esta acción NO se puede deshacer!")

    if '--confirm' not in sys.argv:
        print("\n⚠️  Para ejecutar: python3 delete_users.py --confirm")
        return

    print("\n✅ Confirmación recibida. Procediendo...")
    print("\n" + "=" * 70)

    with app.app_context():
        deleted_count = 0
        failed_count = 0
        for uid in to_delete_ids:
            if delete_user_by_id(uid):
                deleted_count += 1
            else:
                failed_count += 1
        for email in to_delete_emails:
            if delete_user_and_transactions(email):
                deleted_count += 1
            else:
                failed_count += 1

        print("\n" + "=" * 70)
        print("RESUMEN")
        print("=" * 70)
        print(f"✅ Eliminados: {deleted_count}")
        if failed_count > 0:
            print(f"❌ Con errores: {failed_count}")
        print("\n✨ Proceso completado")


if __name__ == '__main__':
    main()
