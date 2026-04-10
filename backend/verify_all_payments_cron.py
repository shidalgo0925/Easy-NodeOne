#!/usr/bin/env python3
"""
Script cron unificado para verificar automáticamente pagos pendientes
de TODOS los métodos de pago: Yappy, PayPal y Stripe/TCR

Este script debe ejecutarse periódicamente (cada 5-15 minutos) para verificar
pagos que no fueron confirmados por webhooks.

Configuración del cron job:
    */10 * * * * cd /ruta/al/proyecto/backend && python3 verify_all_payments_cron.py >> /var/log/membership_payments.log 2>&1

O ejecutar cada 10 minutos:
    0,10,20,30,40,50 * * * * cd /ruta/al/proyecto/backend && python3 verify_all_payments_cron.py >> /var/log/membership_payments.log 2>&1
"""

import sys
import os

# Agregar el directorio del backend al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from notification_scheduler import verify_all_payments
    from datetime import datetime
    
    print(f"\n{'='*60}")
    print(f"🔍 Verificación periódica de pagos (Yappy, PayPal, Stripe/TCR) - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")
    
    verify_all_payments()  # Verificar TODOS los métodos de pago
    
    print(f"\n✅ Verificación completada: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
except Exception as e:
    print(f"\n❌ Error en verificación automática: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
