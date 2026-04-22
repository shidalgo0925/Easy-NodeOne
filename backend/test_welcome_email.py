#!/usr/bin/env python3
"""
Script para probar el template de email de bienvenida
Genera el HTML y lo guarda en un archivo para visualizarlo
"""

import sys
import os
from datetime import datetime

# Agregar el directorio backend al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Crear contexto de aplicación Flask
from app import app, db, User, get_public_image_url
from email_templates import get_welcome_email

# Crear un usuario de prueba
class MockUser:
    def __init__(self):
        self.id = 1
        self.first_name = "Juan"
        self.last_name = "Pérez"
        self.email = "juan.perez@example.com"

def test_welcome_email():
    """Probar el template de bienvenida"""
    with app.app_context():
        # Crear usuario de prueba
        user = MockUser()
        
        print("🔄 Generando template de bienvenida...")
        print(f"   Usuario: {user.first_name} {user.last_name}")
        print(f"   Email: {user.email}")
        
        try:
            # Generar el HTML del email
            html_content = get_welcome_email(user)
            
            # Guardar en archivo para visualizar
            output_file = os.path.join(os.path.dirname(__file__), '..', 'test_welcome_email.html')
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            print(f"\n✅ Template generado exitosamente!")
            print(f"📄 Archivo guardado en: {output_file}")
            print(f"\n🌐 Para verlo, abre el archivo en tu navegador:")
            print(f"   file://{os.path.abspath(output_file)}")
            print(f"\n   O desde la terminal:")
            print(f"   xdg-open {output_file}  # Linux")
            print(f"   open {output_file}      # macOS")
            print(f"   start {output_file}     # Windows")
            
            # Mostrar URL del logo que se generó
            try:
                logo_url = get_public_image_url('emails/logos/logo-primary.png', absolute=True)
                print(f"\n🖼️  URL del logo generada: {logo_url}")
                print(f"   ⚠️  Nota: Asegúrate de que el logo esté en:")
                print(f"      static/public/emails/logos/logo-primary.png")
            except Exception as e:
                print(f"\n⚠️  Error al generar URL del logo: {e}")
            
            # Mostrar preview del HTML (primeras líneas)
            print(f"\n📋 Preview del HTML (primeras 10 líneas):")
            print("-" * 60)
            lines = html_content.split('\n')[:10]
            for i, line in enumerate(lines, 1):
                print(f"{i:2}: {line}")
            print("...")
            print("-" * 60)
            
            return True
            
        except Exception as e:
            print(f"\n❌ Error al generar template: {e}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == '__main__':
    print("=" * 60)
    print("🧪 PRUEBA DE TEMPLATE DE BIENVENIDA")
    print("=" * 60)
    print()
    
    success = test_welcome_email()
    
    print()
    print("=" * 60)
    if success:
        print("✅ Prueba completada exitosamente")
    else:
        print("❌ Prueba falló")
    print("=" * 60)


