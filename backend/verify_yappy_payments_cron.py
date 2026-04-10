#!/usr/bin/env python3
"""
Script para ejecutar verificación periódica de pagos Yappy
Este script se ejecuta desde un cron job cada 5 minutos

Uso:
    python3 verify_yappy_payments_cron.py

O desde cron:
    */5 * * * * /var/www/nodeone/venv/bin/python3 /var/www/nodeone/backend/verify_yappy_payments_cron.py >> /var/www/nodeone/logs/yappy_verification.log 2>&1
"""

import sys
import os
from pathlib import Path

# Agregar el directorio del backend al path
backend_dir = Path(__file__).parent
project_dir = backend_dir.parent
sys.path.insert(0, str(backend_dir))

# Cambiar al directorio del backend
os.chdir(backend_dir)

# Intentar usar el venv si existe
venv_python = project_dir / 'venv' / 'bin' / 'python3'
if venv_python.exists():
    # Si estamos ejecutando desde el venv, ya está bien
    pass

try:
    from notification_scheduler import verify_all_payments
    from datetime import datetime
    
    print(f"\n{'='*60}")
    print(f"🔍 Verificación periódica de pagos (Yappy, PayPal, Stripe/TCR) - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")
    
    verify_all_payments()  # Verificar TODOS los métodos de pago
    
    print(f"\n✅ Verificación completada: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
except Exception as e:
    print(f"\n❌ Error en verificación periódica: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

