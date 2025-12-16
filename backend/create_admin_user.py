#!/usr/bin/env python3
"""
Script para crear un usuario administrador
"""

import sys
import os

# Agregar el directorio del backend al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db, User
from werkzeug.security import generate_password_hash

def create_admin_user():
    """Crear usuario administrador"""
    with app.app_context():
        # Verificar si ya existe un admin
        existing_admin = User.query.filter_by(is_admin=True).first()
        if existing_admin:
            print(f"⚠️ Ya existe un usuario administrador: {existing_admin.email}")
            response = input("¿Deseas crear otro? (s/n): ")
            if response.lower() != 's':
                return
        
        # Solicitar datos
        print("\n🔐 Crear Usuario Administrador\n")
        email = input("Email: ").strip().lower()
        
        # Verificar si el email ya existe
        if User.query.filter_by(email=email).first():
            print(f"❌ El email {email} ya está registrado")
            return
        
        password = input("Contraseña: ").strip()
        if len(password) < 6:
            print("❌ La contraseña debe tener al menos 6 caracteres")
            return
        
        first_name = input("Nombre: ").strip()
        last_name = input("Apellido: ").strip()
        phone = input("Teléfono (opcional): ").strip() or None
        country = input("País (opcional, default: Panamá): ").strip() or "Panamá"
        
        # Crear usuario
        admin_user = User(
            email=email,
            password_hash=generate_password_hash(password),
            first_name=first_name,
            last_name=last_name,
            phone=phone,
            country=country,
            is_admin=True,
            is_active=True,
            email_verified=True  # Administrador verificado por defecto
        )
        
        try:
            db.session.add(admin_user)
            db.session.commit()
            print(f"\n✅ Usuario administrador creado exitosamente!")
            print(f"   Email: {email}")
            print(f"   Nombre: {first_name} {last_name}")
            print(f"\n🔑 Puedes iniciar sesión con estas credenciales")
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error al crear usuario: {e}")
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    create_admin_user()


