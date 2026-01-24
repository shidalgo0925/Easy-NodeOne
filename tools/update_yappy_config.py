#!/usr/bin/env python3
"""
Script para actualizar la configuración de Yappy en la base de datos
"""

import sys
import os

# Agregar el directorio backend al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from app import app, db, PaymentConfig

def update_yappy_config():
    """Actualizar configuración de Yappy"""
    
    # Valores proporcionados
    yappy_api_key = "YP_D8BEE668-7E43-3723-A328-345C8093C3AA"  # Decodificado del base64
    yappy_merchant_id = "LSKPY-99584596"
    yappy_api_url = "https://api.yappy.im"  # URL por defecto
    
    with app.app_context():
        # Buscar configuración existente
        config = PaymentConfig.query.filter_by(is_active=True).first()
        
        if not config:
            # Si no existe, crear una nueva
            print("⚠️ No hay configuración activa. Creando nueva configuración...")
            config = PaymentConfig(
                yappy_api_key=yappy_api_key,
                yappy_merchant_id=yappy_merchant_id,
                yappy_api_url=yappy_api_url,
                use_environment_variables=False,  # Usar valores de BD
                is_active=True
            )
            db.session.add(config)
        else:
            # Actualizar configuración existente
            print(f"✅ Configuración encontrada (ID: {config.id}). Actualizando valores de Yappy...")
            config.yappy_api_key = yappy_api_key
            config.yappy_merchant_id = yappy_merchant_id
            config.yappy_api_url = yappy_api_url
            config.use_environment_variables = False  # Asegurar que use valores de BD
            config.is_active = True
        
        # Guardar cambios
        try:
            db.session.commit()
            print("✅ Configuración de Yappy actualizada exitosamente!")
            print(f"\n📋 Valores guardados:")
            print(f"   API Key: {yappy_api_key}")
            print(f"   Merchant ID: {yappy_merchant_id}")
            print(f"   API URL: {yappy_api_url}")
            print(f"   Usar variables de entorno: No (usa valores de BD)")
            
            # Verificar que se guardó correctamente
            saved_config = PaymentConfig.query.get(config.id)
            if saved_config:
                print(f"\n✅ Verificación: Configuración guardada correctamente (ID: {saved_config.id})")
            else:
                print("\n⚠️ Advertencia: No se pudo verificar la configuración guardada")
                
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error al guardar configuración: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    return True

if __name__ == '__main__':
    print("🔧 Actualizando configuración de Yappy...\n")
    success = update_yappy_config()
    if success:
        print("\n✅ Proceso completado exitosamente!")
        sys.exit(0)
    else:
        print("\n❌ Error en el proceso")
        sys.exit(1)


