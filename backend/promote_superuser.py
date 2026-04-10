#!/usr/bin/env python3
"""
Promueve un usuario a superusuario de plataforma (Easy NodeOne).

Qué hace:
  1) Asegura semilla RBAC (roles SA/AD/… y permisos) si la tabla `role` está vacía
     (reutiliza migrate_rbac_tables.run_migration).
  2) Marca el usuario: is_admin=True, email_verified=True, is_active=True.
  3) Asigna el rol SA (SuperAdministrador), que en la semilla tiene todos los permisos.
  4) Opcionalmente quita otros roles RBAC del usuario para evitar confusiones (--only-sa).

Por qué no ves opciones en /admin/users (botones XLS, Roles en menú, iconos de roles/membresía):
  - En plantillas se usa has_permission('roles.view'), 'roles.assign', 'reports.export', etc.
  - Sin filas en user_role + role_permission, esas secciones quedan ocultas.
  - Tras cambiar roles en BD, cerrá sesión e iniciá de nuevo (o borrá cookies de sesión).

Uso (desde el directorio backend, con el venv del proyecto):
  ../venv/bin/python3 promote_superuser.py
  ../venv/bin/python3 promote_superuser.py otro@correo.com
  ../venv/bin/python3 promote_superuser.py --dry-run
  ../venv/bin/python3 promote_superuser.py --only-sa

No modifica contraseñas.
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))


def main() -> int:
    parser = argparse.ArgumentParser(description="Promover usuario a superadmin (is_admin + rol SA).")
    parser.add_argument(
        "email",
        nargs="?",
        default="shidalgo@easytech.services",
        help="Email del usuario (default: shidalgo@easytech.services)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Solo mostrar qué haría, sin commit.")
    parser.add_argument(
        "--no-seed",
        action="store_true",
        help="No llamar a migrate_rbac_tables (asumí roles/permisos ya cargados).",
    )
    parser.add_argument(
        "--only-sa",
        action="store_true",
        help="Quitar otros roles RBAC del usuario y dejar solo SA.",
    )
    args = parser.parse_args()

    email = (args.email or "").strip().lower()
    if not email:
        print("Email vacío.", file=sys.stderr)
        return 1

    from app import app, db, User, Role
    from sqlalchemy import text as sql_text

    with app.app_context():
        if not args.no_seed:
            from migrate_rbac_tables import run_migration

            run_migration()

        u = User.query.filter(db.func.lower(User.email) == email).first()
        if not u:
            print(f"No existe usuario con email: {email}", file=sys.stderr)
            return 1

        sa = Role.query.filter_by(code="SA").first()
        if not sa:
            print("No existe rol SA. Ejecutá migrate_rbac_tables sin --no-seed.", file=sys.stderr)
            return 1

        if args.dry_run:
            print(f"[dry-run] Usuario: id={u.id} email={u.email}")
            print(f"[dry-run] is_admin actual={u.is_admin} roles={[r.code for r in u.roles.all()]}")
            print(f"[dry-run] Aplicaría: is_admin=True, email_verified=True, rol SA")
            return 0

        u.is_admin = True
        u.is_active = True
        u.email_verified = True

        if args.only_sa:
            db.session.execute(sql_text("DELETE FROM user_role WHERE user_id = :uid"), {"uid": u.id})

        if u.roles.filter_by(id=sa.id).first() is None:
            u.roles.append(sa)

        db.session.commit()

        # Verificación (mismos permisos que usa el UI de usuarios)
        checks = ("users.view", "roles.view", "roles.assign", "reports.export", "memberships.assign")
        print(f"OK usuario id={u.id} {u.email}")
        print(f"   is_admin={u.is_admin} roles={[r.code for r in u.roles.all()]}")
        print("   Permisos (muestra):")
        for c in checks:
            print(f"     has_permission({c!r}) = {u.has_permission(c)}")
        print("\nCerrá sesión en el navegador y volvé a entrar para ver todo el menú y botones.")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
