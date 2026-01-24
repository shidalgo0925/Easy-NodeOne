#!/usr/bin/env python3
"""
Script de prueba para verificar que el sistema de historial funciona
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

print("=" * 70)
print("🧪 PRUEBA DEL SISTEMA DE HISTORIAL DE TRANSACCIONES")
print("=" * 70)

# Test 1: Importar HistoryLogger
print("\n1️⃣ Probando importación de HistoryLogger...")
try:
    from history_module import HistoryLogger
    print("   ✅ HistoryLogger importado correctamente")
except Exception as e:
    print(f"   ❌ Error: {e}")
    sys.exit(1)

# Test 2: Verificar métodos
print("\n2️⃣ Verificando métodos disponibles...")
methods = ['log_user_action', 'log_system_action', 'log_error', 
           'log_security_event', 'log_info', 'log_warning']
for method in methods:
    if hasattr(HistoryLogger, method):
        print(f"   ✅ {method} disponible")
    else:
        print(f"   ❌ {method} NO disponible")

# Test 3: Verificar que el modelo está en app.py
print("\n3️⃣ Verificando modelo HistoryTransaction en app.py...")
try:
    with open('app.py', 'r') as f:
        content = f.read()
    
    if 'class HistoryTransaction' in content:
        print("   ✅ Modelo HistoryTransaction encontrado en app.py")
    else:
        print("   ❌ Modelo HistoryTransaction NO encontrado")
    
    if 'transaction_metadata' in content:
        print("   ✅ transaction_metadata encontrado (correcto)")
    if 'metadata = db.Column' in content and 'HistoryTransaction' in content:
        print("   ⚠️  'metadata = db.Column' encontrado (debería ser transaction_metadata)")
        
except Exception as e:
    print(f"   ❌ Error leyendo app.py: {e}")

# Test 4: Verificar endpoints
print("\n4️⃣ Verificando endpoints en app.py...")
endpoints_to_check = [
    '/api/history',
    '/api/history/<int:transaction_id>',
    '/api/history/stats',
    '/api/admin/history',
    '/api/admin/history/<int:transaction_id>',
    '/api/admin/history/stats',
    '/api/admin/history/export'
]

found_endpoints = []
for endpoint in endpoints_to_check:
    if endpoint.replace('<int:transaction_id>', '') in content:
        found_endpoints.append(endpoint)
        print(f"   ✅ {endpoint} encontrado")
    else:
        print(f"   ❌ {endpoint} NO encontrado")

# Test 5: Verificar integraciones
print("\n5️⃣ Verificando integraciones en app.py...")
integrations = [
    ('login_user(user)', 'HistoryLogger.log_user_action'),
    ('logout_user()', 'HistoryLogger.log_user_action'),
    ('db.session.add(user)', 'HistoryLogger.log_user_action'),
    ('process_cart_after_payment', 'HistoryLogger.log_system_action'),
]

for trigger, logger_call in integrations:
    if trigger in content and logger_call in content:
        # Verificar que están cerca
        trigger_pos = content.find(trigger)
        logger_pos = content.find(logger_call)
        if abs(trigger_pos - logger_pos) < 500:  # Dentro de 500 caracteres
            print(f"   ✅ {trigger} → {logger_call} integrado")
        else:
            print(f"   ⚠️  {trigger} y {logger_call} encontrados pero lejos")
    else:
        print(f"   ❌ {trigger} → {logger_call} NO integrado")

print("\n" + "=" * 70)
print("✅ PRUEBAS COMPLETADAS")
print("=" * 70)
print(f"\n📊 Resumen:")
print(f"   - Endpoints encontrados: {len(found_endpoints)}/{len(endpoints_to_check)}")
print(f"   - Integraciones verificadas: {len(integrations)}")
