#!/usr/bin/env python3
"""
Script de migración para inicializar templates de correo editables
Crea registros de EmailTemplate basados en los templates por defecto
"""

import sys
import os

# Agregar el directorio backend al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db, EmailTemplate
from datetime import datetime

# Definición de todos los templates del sistema
EMAIL_TEMPLATES = [
    {
        'template_key': 'welcome',
        'name': 'Email de Bienvenida',
        'subject': 'Bienvenido a RelaticPanama',
        'category': 'system',
        'variables': '{"user": ["first_name", "last_name", "email"]}'
    },
    {
        'template_key': 'membership_payment',
        'name': 'Confirmación de Pago de Membresía',
        'subject': 'Confirmación de Pago - RelaticPanama',
        'category': 'membership',
        'variables': '{"user": ["first_name", "last_name", "email"], "payment": ["membership_type", "amount", "created_at"], "subscription": ["end_date"]}'
    },
    {
        'template_key': 'membership_expiring',
        'name': 'Membresía por Expirar',
        'subject': 'Tu Membresía Expirará en {days_left} Días - RelaticPanama',
        'category': 'membership',
        'variables': '{"user": ["first_name", "last_name", "email"], "subscription": ["membership_type", "end_date"], "days_left": "number"}'
    },
    {
        'template_key': 'membership_expired',
        'name': 'Membresía Expirada',
        'subject': 'Tu Membresía Ha Expirado - RelaticPanama',
        'category': 'membership',
        'variables': '{"user": ["first_name", "last_name", "email"], "subscription": ["membership_type", "end_date"]}'
    },
    {
        'template_key': 'membership_renewed',
        'name': 'Membresía Renovada',
        'subject': 'Membresía Renovada - RelaticPanama',
        'category': 'membership',
        'variables': '{"user": ["first_name", "last_name", "email"], "subscription": ["membership_type", "start_date", "end_date"]}'
    },
    {
        'template_key': 'event_registration',
        'name': 'Confirmación de Registro a Evento',
        'subject': 'Registro Confirmado: {event.title}',
        'category': 'event',
        'variables': '{"user": ["first_name", "last_name", "email"], "event": ["title", "start_date", "start_time"], "registration": ["registration_status", "final_price"]}'
    },
    {
        'template_key': 'event_cancellation',
        'name': 'Cancelación de Registro a Evento',
        'subject': 'Cancelación de Registro: {event.title}',
        'category': 'event',
        'variables': '{"user": ["first_name", "last_name", "email"], "event": ["title"]}'
    },
    {
        'template_key': 'event_update',
        'name': 'Actualización de Evento',
        'subject': 'Actualización: {event.title}',
        'category': 'event',
        'variables': '{"user": ["first_name", "last_name", "email"], "event": ["title", "id"], "changes": "array"}'
    },
    {
        'template_key': 'appointment_confirmation',
        'name': 'Confirmación de Cita',
        'subject': 'Cita Confirmada - RelaticPanama',
        'category': 'appointment',
        'variables': '{"user": ["first_name", "last_name", "email"], "advisor": ["first_name", "last_name"], "appointment": ["appointment_date", "appointment_time", "duration", "appointment_type", "status"]}'
    },
    {
        'template_key': 'appointment_reminder',
        'name': 'Recordatorio de Cita',
        'subject': 'Recordatorio: Cita en {hours_before} horas - RelaticPanama',
        'category': 'appointment',
        'variables': '{"user": ["first_name", "last_name", "email"], "advisor": ["first_name", "last_name"], "appointment": ["appointment_date", "appointment_time", "duration"], "hours_before": "number"}'
    },
    {
        'template_key': 'password_reset',
        'name': 'Restablecimiento de Contraseña',
        'subject': 'Restablecer Contraseña - RelaticPanama',
        'category': 'system',
        'variables': '{"user": ["first_name", "last_name", "email"], "reset_token": "string", "reset_url": "string"}'
    }
]


def initialize_email_templates():
    """Inicializar todos los templates de correo"""
    with app.app_context():
        try:
            # Asegurar que las tablas existan
            db.create_all()
            print("✅ Tablas verificadas/creadas")
            
            created_count = 0
            updated_count = 0
            
            for template_data in EMAIL_TEMPLATES:
                # Verificar si ya existe
                existing = EmailTemplate.query.filter_by(
                    template_key=template_data['template_key']
                ).first()
                
                if existing:
                    # Actualizar si es necesario
                    existing.name = template_data['name']
                    existing.subject = template_data['subject']
                    existing.category = template_data['category']
                    existing.variables = template_data.get('variables', '{}')
                    updated_count += 1
                    print(f"✓ Actualizado: {template_data['name']}")
                else:
                    # Crear nuevo template (sin contenido HTML, usa el por defecto)
                    template = EmailTemplate(
                        template_key=template_data['template_key'],
                        name=template_data['name'],
                        subject=template_data['subject'],
                        html_content='',  # Vacío = usa template por defecto
                        text_content=None,
                        category=template_data['category'],
                        is_custom=False,  # Por defecto usa el template del código
                        variables=template_data.get('variables', '{}')
                    )
                    db.session.add(template)
                    created_count += 1
                    print(f"✓ Creado: {template_data['name']}")
            
            db.session.commit()
            
            print(f"\n{'='*60}")
            print(f"✅ Migración completada:")
            print(f"   - Templates creados: {created_count}")
            print(f"   - Templates actualizados: {updated_count}")
            print(f"   - Total de templates: {len(EMAIL_TEMPLATES)}")
            print(f"{'='*60}\n")
            print("ℹ️  Nota: Los templates están configurados para usar las versiones")
            print("   por defecto del código. Puedes personalizarlos desde /admin/email")
            
            return True
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error en la migración: {e}")
            import traceback
            traceback.print_exc()
            return False


if __name__ == '__main__':
    print(f"\n{'='*60}")
    print("Inicializando templates de correo...")
    print(f"{'='*60}\n")
    
    success = initialize_email_templates()
    
    if success:
        print("✅ Migración exitosa. Los templates están listos.")
        print("   Puedes editarlos desde: /admin/email")
    else:
        print("❌ Error en la migración. Revisa los logs.")
        sys.exit(1)

