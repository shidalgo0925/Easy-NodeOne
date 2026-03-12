#!/usr/bin/env python3
"""
Seed inicial: crea un único usuario administrador.
Uso: desde backend/ ejecutar  python seed_initial_admin.py
Pide email y contraseña por consola. No usar contraseñas en env ni en código.
El admin creado tendrá must_change_password=True y deberá cambiarla en primer login.
"""
import sys
import os

# Ejecutar desde backend/
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.chdir(os.path.dirname(os.path.abspath(__file__)))

def main():
    try:
        from getpass import getpass
    except ImportError:
        getpass = lambda p: input(p)  # fallback si no hay getpass

    from app import app, db, User

    with app.app_context():
        # Asegurar columna si existe DB antigua
        try:
            from app import ensure_must_change_password_column
            ensure_must_change_password_column()
        except Exception:
            pass

        admin = User.query.filter_by(is_admin=True).first()
        if admin:
            print('Ya existe al menos un administrador.')
            print('Si quieres otro admin, créalo desde el panel de administración.')
            return 0

        print('--- Crear primer administrador ---')
        print('No guardes la contraseña en código ni en variables de entorno.')
        email = input('Email del admin: ').strip()
        if not email:
            print('Email requerido.')
            return 1
        if User.query.filter_by(email=email).first():
            print('Ese email ya está registrado.')
            return 1
        password = getpass('Contraseña (mín. 8 caracteres): ')
        if len(password) < 8:
            print('La contraseña debe tener al menos 8 caracteres.')
            return 1
        confirm = getpass('Repetir contraseña: ')
        if password != confirm:
            print('Las contraseñas no coinciden.')
            return 1

        first_name = input('Nombre (ej. Admin) [Admin]: ').strip() or 'Admin'
        last_name = input('Apellido (ej. NodeOne) [NodeOne]: ').strip() or 'NodeOne'

        user = User(
            email=email,
            first_name=first_name,
            last_name=last_name,
            is_admin=True,
            is_active=True,
            email_verified=True,
            must_change_password=True,
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        print('Admin creado. Debe cambiar la contraseña en el primer inicio de sesión.')
        return 0

if __name__ == '__main__':
    sys.exit(main() or 0)
