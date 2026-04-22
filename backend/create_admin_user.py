#!/usr/bin/env python3
"""
Crea el usuario administrador de plataforma y lo deja como superusuario (is_admin + rol SA).

Requisitos:
  - Debe existir al menos una fila en saas_organization (p. ej. id=1).
  - Semilla RBAC: se llama a migrate_rbac_tables.run_migration() salvo --no-seed.

Contraseña (en este orden):
  1) Variable de entorno INITIAL_ADMIN_PASSWORD
  2) Si hay TTY: getpass interactivo
  3) Si no hay TTY ni env: error (no generamos contraseña en código por defecto).

Uso:
  cd backend
  INITIAL_ADMIN_PASSWORD='tu_clave_segura' ../venv/bin/python3 create_admin_user.py
  ../venv/bin/python3 create_admin_user.py --email admin@example.com

Opciones:
  --first-name, --last-name, --organization-id (default 1)
  --must-change-password  obliga cambio en primer login (recomendado en prod)
  --no-must-change        permite entrar sin cambiar contraseña (solo dev)
  --no-seed               no ejecutar migrate_rbac_tables
  --force                 si el email ya existe: actualiza contraseña y re-aplica SA/is_admin
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))


def _promote_existing(u, only_sa: bool) -> None:
    from app import db, Role
    from sqlalchemy import text as sql_text

    sa = Role.query.filter_by(code="SA").first()
    if not sa:
        raise RuntimeError("No existe rol SA. Quitá --no-seed o ejecutá migrate_rbac_tables.")

    u.is_admin = True
    u.is_active = True
    u.email_verified = True
    if only_sa:
        db.session.execute(sql_text("DELETE FROM user_role WHERE user_id = :uid"), {"uid": u.id})
    if u.roles.filter_by(id=sa.id).first() is None:
        u.roles.append(sa)


def main() -> int:
    parser = argparse.ArgumentParser(description="Crear usuario admin + superusuario SA (Easy NodeOne).")
    parser.add_argument("--email", default="shidalgo@easytech.services")
    parser.add_argument("--first-name", default="Seul")
    parser.add_argument("--last-name", default="Hidalgo")
    parser.add_argument("--organization-id", type=int, default=1)
    parser.add_argument("--must-change-password", action="store_true", help="Obligar cambio en primer login.")
    parser.add_argument("--no-must-change", action="store_true", help="No obligar cambio (solo dev).")
    parser.add_argument("--no-seed", action="store_true")
    parser.add_argument("--force", action="store_true", help="Email ya existe: actualizar y promover.")
    parser.add_argument("--only-sa", action="store_true", help="Al promover, dejar solo rol SA.")
    args = parser.parse_args()

    email = (args.email or "").strip().lower()
    if not email:
        print("Email vacío.", file=sys.stderr)
        return 1

    password = (os.environ.get("INITIAL_ADMIN_PASSWORD") or "").strip()
    if not password:
        try:
            from getpass import getpass
        except ImportError:
            getpass = lambda p: input(p)
        if sys.stdin.isatty():
            p1 = getpass("Contraseña (mín. 8): ")
            p2 = getpass("Repetir: ")
            if p1 != p2:
                print("Las contraseñas no coinciden.", file=sys.stderr)
                return 1
            password = p1
    if len(password) < 8:
        print(
            "Contraseña requerida (mín. 8). Ej.: INITIAL_ADMIN_PASSWORD='...' ../venv/bin/python3 create_admin_user.py",
            file=sys.stderr,
        )
        return 1

    must_change = True
    if args.no_must_change:
        must_change = False
    if args.must_change_password:
        must_change = True

    from app import app, db, User

    with app.app_context():
        try:
            from app import ensure_must_change_password_column

            ensure_must_change_password_column()
        except Exception:
            pass

        if not args.no_seed:
            from migrate_rbac_tables import run_migration

            run_migration()

        u = User.query.filter(db.func.lower(User.email) == email).first()
        if u and not args.force:
            print(f"Ya existe el usuario {email}. Usá --force para actualizar contraseña y permisos SA.")
            return 1

        if u and args.force:
            u.set_password(password)
            u.must_change_password = must_change
            _promote_existing(u, args.only_sa)
            db.session.commit()
            print(f"OK actualizado: {email} (is_admin + SA). must_change_password={must_change}")
            return 0

        from sqlalchemy import text as sql_text

        oid = args.organization_id
        row = db.session.execute(
            sql_text("SELECT 1 FROM saas_organization WHERE id = :id"), {"id": oid}
        ).fetchone()
        if not row:
            print(f"No existe saas_organization id={oid}. Creá una org o usá --organization-id válido.", file=sys.stderr)
            return 1

        user = User(
            email=email,
            first_name=(args.first_name or "Admin").strip() or "Admin",
            last_name=(args.last_name or "NodeOne").strip() or "NodeOne",
            is_admin=True,
            is_active=True,
            email_verified=True,
            must_change_password=must_change,
            organization_id=oid,
        )
        user.set_password(password)
        db.session.add(user)
        db.session.flush()
        _promote_existing(user, args.only_sa)
        db.session.commit()
        print(f"OK creado: {email} org_id={oid} is_admin=True rol SA must_change_password={must_change}")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
