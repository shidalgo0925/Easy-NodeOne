#!/usr/bin/env python3
"""
Script de verificación del sistema de emails.
Uso: python verify_email_system.py [--org-id ID]
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from app import (
        app,
        db,
        EmailConfig,
        NotificationSettings,
        EMAIL_TEMPLATES_AVAILABLE,
        get_welcome_email,
        NotificationEngine,
    )
    from email_service import EmailService
    from flask_mail import Mail
except ImportError as e:
    print(f"❌ Error al importar módulos: {e}")
    print("   Asegúrate de tener todas las dependencias instaladas")
    sys.exit(1)

def check_email_config(organization_id=None):
    """Verificar configuración de email"""
    print('\n' + '=' * 60)
    print('1. VERIFICANDO CONFIGURACIÓN DE EMAIL')
    if organization_id is not None:
        print(f'   (organization_id solicitado: {organization_id})')
    print('=' * 60)

    email_config = EmailConfig.get_active_config(organization_id=organization_id)
    if email_config:
        print('✅ Configuración de email encontrada en BD:')
        print(f'   organization_id (fila): {getattr(email_config, "organization_id", None)}')
        print(f'   Servidor: {email_config.mail_server}')
        print(f"   Puerto: {email_config.mail_port}")
        print(f"   TLS: {email_config.mail_use_tls}")
        print(f"   SSL: {email_config.mail_use_ssl}")
        print(f"   Remitente: {email_config.mail_default_sender}")
        print(f"   Usa variables de entorno: {email_config.use_environment_variables}")
        if not email_config.use_environment_variables:
            print(f"   Usuario: {email_config.mail_username or '(no configurado)'}")
            print(f"   Contraseña: {'***' if email_config.mail_password else '(no configurada)'}")
    else:
        print("⚠️ No hay configuración de email en BD")
        print("   Se usarán valores por defecto o variables de entorno")
    
    # Verificar configuración de Flask
    print("\n📧 Configuración actual de Flask:")
    print(f"   MAIL_SERVER: {app.config.get('MAIL_SERVER', 'no configurado')}")
    print(f"   MAIL_PORT: {app.config.get('MAIL_PORT', 'no configurado')}")
    print(f"   MAIL_USE_TLS: {app.config.get('MAIL_USE_TLS', 'no configurado')}")
    print(f"   MAIL_USERNAME: {app.config.get('MAIL_USERNAME', 'no configurado')}")
    print(f"   MAIL_PASSWORD: {'***' if app.config.get('MAIL_PASSWORD') else 'no configurado'}")
    print(f"   MAIL_DEFAULT_SENDER: {app.config.get('MAIL_DEFAULT_SENDER', 'no configurado')}")

def check_notification_settings():
    """Verificar configuración de notificaciones"""
    print("\n" + "="*60)
    print("2. VERIFICANDO CONFIGURACIÓN DE NOTIFICACIONES")
    print("="*60)
    
    welcome_setting = NotificationSettings.query.filter_by(notification_type='welcome').first()
    if welcome_setting:
        if welcome_setting.enabled:
            print("✅ Notificación 'welcome' está HABILITADA")
        else:
            print("❌ Notificación 'welcome' está DESHABILITADA")
            print("   ⚠️ Esto impedirá el envío de emails de bienvenida")
    else:
        print("⚠️ No se encontró configuración para 'welcome'")
        print("   Se usará el valor por defecto: HABILITADA")
        enabled = NotificationEngine._is_notification_enabled('welcome')
        print(f"   Estado actual: {'HABILITADA' if enabled else 'DESHABILITADA'}")

def check_email_service():
    """Verificar servicio de email"""
    import app as ap

    print('\n' + '=' * 60)
    print('3. VERIFICANDO SERVICIO DE EMAIL')
    print('=' * 60)

    svc = ap.email_service
    print(f'EMAIL_TEMPLATES_AVAILABLE (render plantillas): {EMAIL_TEMPLATES_AVAILABLE}')
    print(f'email_service: {svc}')

    if EMAIL_TEMPLATES_AVAILABLE:
        print('✅ Templates de email disponibles para render')
    else:
        print('❌ Templates de email NO disponibles')
        print('   ⚠️ No se podrán renderizar emails HTML desde plantillas DB/archivos')

    if svc:
        print('✅ EmailService inicializado (envío SMTP)')
        print(f'   Tipo: {type(svc)}')
    else:
        print('❌ EmailService NO inicializado')
        print('   ⚠️ No se podrá enviar por SMTP hasta configurar Mail + servicio')

def check_welcome_email_template():
    """Verificar template de bienvenida"""
    print("\n" + "="*60)
    print("4. VERIFICANDO TEMPLATE DE BIENVENIDA")
    print("="*60)
    
    class MockUser:
        def __init__(self):
            self.id = 1
            self.first_name = "Test"
            self.last_name = "Usuario"
            self.email = "test@example.com"
    
    try:
        user = MockUser()
        with app.app_context():
            html = get_welcome_email(user)
            if html and len(html) > 100:
                print("✅ Template de bienvenida se genera correctamente")
                print(f"   Tamaño del HTML: {len(html)} caracteres")
                # Verificar que contiene elementos clave
                if "Bienvenido" in html or "bienvenida" in html.lower():
                    print("✅ Template contiene contenido de bienvenida")
                if user.first_name in html:
                    print("✅ Template incluye nombre del usuario")
            else:
                print("⚠️ Template generado pero parece vacío o muy corto")
    except Exception as e:
        print(f"❌ Error al generar template de bienvenida: {e}")
        import traceback
        traceback.print_exc()

def check_database_tables():
    """Verificar tablas de base de datos"""
    print("\n" + "="*60)
    print("5. VERIFICANDO TABLAS DE BASE DE DATOS")
    print("="*60)
    
    try:
        # Verificar EmailLog
        from app import EmailLog
        count = EmailLog.query.count()
        print(f"✅ Tabla EmailLog existe - {count} registros")
        
        # Verificar NotificationSettings
        count = NotificationSettings.query.count()
        print(f"✅ Tabla NotificationSettings existe - {count} configuraciones")
        
        # Verificar EmailConfig
        count = EmailConfig.query.count()
        print(f"✅ Tabla EmailConfig existe - {count} configuraciones")
        
    except Exception as e:
        print(f"❌ Error al verificar tablas: {e}")

def check_file_structure():
    """Verificar estructura de archivos"""
    print("\n" + "="*60)
    print("6. VERIFICANDO ESTRUCTURA DE ARCHIVOS")
    print("="*60)
    
    # Verificar template de bienvenida
    template_path = os.path.join(os.path.dirname(__file__), '..', 'templates', 'emails', 'sistema', 'bienvenida.html')
    if os.path.exists(template_path):
        print("✅ Template de bienvenida existe")
    else:
        print(f"❌ Template de bienvenida NO existe en: {template_path}")
    
    # Verificar logo
    logo_path_png = os.path.join(os.path.dirname(__file__), '..', 'static', 'public', 'emails', 'logos', 'logo-relatic.png')
    logo_path_svg = os.path.join(os.path.dirname(__file__), '..', 'static', 'images', 'logo-relatic.svg')
    
    if os.path.exists(logo_path_png):
        print("✅ Logo PNG encontrado en nueva ubicación")
    elif os.path.exists(logo_path_svg):
        print("⚠️ Logo SVG encontrado en ubicación antigua (se usará como fallback)")
    else:
        print("⚠️ No se encontró logo (emails se enviarán sin logo)")

def main():
    """Ejecutar todas las verificaciones"""
    parser = argparse.ArgumentParser(description='Verificación sistema de emails')
    parser.add_argument(
        '--org-id',
        type=int,
        default=None,
        help='Aplicar SMTP transaccional de este tenant antes de las comprobaciones',
    )
    args = parser.parse_args()

    print('\n' + '=' * 60)
    print('VERIFICACIÓN DEL SISTEMA DE EMAILS')
    if args.org_id is not None:
        print(f'  (--org-id {args.org_id})')
    print('=' * 60)

    import app as ap

    with app.app_context():
        db.create_all()

        try:
            if args.org_id is not None:
                ap.apply_transactional_smtp_for_organization(int(args.org_id))
            else:
                from app import apply_email_config_from_db

                apply_email_config_from_db()

            check_email_config(organization_id=args.org_id)
            check_notification_settings()
            check_email_service()
            check_welcome_email_template()
            check_database_tables()
            check_file_structure()

            print('\n' + '=' * 60)
            print('RESUMEN')
            print('=' * 60)
            print('\n✅ Verificación completada')
            print('\nSi encuentras problemas:')
            print('1. Verifica la configuración SMTP en /admin/email')
            print("2. Verifica que la notificación 'welcome' esté habilitada en /admin/notifications")
            print('3. Revisa los logs del servidor para más detalles')
            print('\n')
        finally:
            ap.apply_email_config_from_db()

if __name__ == '__main__':
    main()

