#!/usr/bin/env python3
"""
Script de prueba para verificar un pago pendiente de Yappy
Usa el sistema mejorado de verificación
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timedelta

# Agregar el directorio del backend al path
backend_dir = Path(__file__).parent
project_dir = backend_dir.parent
sys.path.insert(0, str(backend_dir))

# Cambiar al directorio del backend
os.chdir(backend_dir)

try:
    # Importar solo lo necesario para evitar problemas con dependencias faltantes
    import sqlite3
    from payment_processors import get_payment_processor
    
    def find_database():
        """Encontrar la base de datos"""
        possible_paths = [
            project_dir / 'instance' / 'membership_legacy.db',
            backend_dir / 'instance' / 'membership_legacy.db',
            backend_dir / 'membership_legacy.db',
            project_dir / 'membership_legacy.db',
        ]
        
        for path in possible_paths:
            if path.exists():
                return str(path)
        
        return None
    
    def test_verification():
        """Probar verificación de pagos pendientes"""
        db_path = find_database()
        
        if not db_path:
            print("❌ No se encontró la base de datos")
            return
        
        print(f"📁 Base de datos: {db_path}\n")
        
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Buscar pagos pendientes de Yappy
        cursor.execute("""
            SELECT id, user_id, amount, status, payment_reference, payment_method, 
                   created_at, yappy_transaction_id
            FROM payment 
            WHERE payment_method = 'yappy'
            AND status IN ('pending', 'awaiting_confirmation')
            ORDER BY created_at DESC
            LIMIT 5
        """)
        
        payments = cursor.fetchall()
        
        if not payments:
            print("❌ No se encontraron pagos pendientes de Yappy")
            conn.close()
            return
        
        print(f"📊 Encontrados {len(payments)} pagos pendientes de Yappy:\n")
        
        # Obtener procesador de pagos (sin configuración, usará variables de entorno)
        print("⚠️ Usando configuración desde variables de entorno")
        processor = get_payment_processor('yappy', None)
        
        for p in payments:
            print(f"{'='*60}")
            print(f"🔍 Verificando Payment ID: {p['id']}")
            print(f"   Usuario: {p['user_id']}")
            print(f"   Monto: ${p['amount']/100:.2f}")
            print(f"   Estado: {p['status']}")
            print(f"   Referencia interna: {p['payment_reference']}")
            print(f"   Yappy Transaction ID: {p['yappy_transaction_id'] or 'No disponible'}")
            print(f"   Creado: {p['created_at']}")
            
            # Calcular tiempo transcurrido
            if p['created_at']:
                try:
                    created = datetime.fromisoformat(p['created_at'].replace('Z', '+00:00'))
                    time_elapsed = (datetime.utcnow() - created.replace(tzinfo=None)).total_seconds() / 60
                    print(f"   Tiempo transcurrido: {int(time_elapsed)} minutos")
                except:
                    print(f"   Tiempo transcurrido: N/A")
            
            print()
            
            # Intentar verificar
            reference_to_check = p['yappy_transaction_id'] or p['payment_reference']
            
            if p['yappy_transaction_id']:
                print(f"   ✅ Usando yappy_transaction_id: {p['yappy_transaction_id']}")
            else:
                print(f"   ⚠️ No hay yappy_transaction_id, usando referencia interna: {p['payment_reference']}")
                print(f"   💡 Esto puede fallar si Yappy no conoce nuestra referencia interna")
            
            print(f"   🔄 Consultando API de Yappy...")
            
            try:
                success, status, yappy_data = processor.verify_payment(reference_to_check)
                
                if success:
                    print(f"   ✅ Verificación exitosa")
                    print(f"   📊 Estado desde Yappy: {status}")
                    
                    if yappy_data:
                        if yappy_data.get('needs_transaction_id'):
                            print(f"   ⚠️ PROBLEMA DETECTADO: Se requiere código de transacción de Yappy (EBOWR-XXXXXXXX)")
                            print(f"   💡 El usuario debe ingresar el código en la interfaz")
                        else:
                            transaction_id = yappy_data.get('transaction_id')
                            yappy_status = yappy_data.get('yappy_status', 'N/A')
                            amount = yappy_data.get('amount', 0)
                            
                            print(f"   📋 Datos de Yappy:")
                            print(f"      - Transaction ID: {transaction_id or 'N/A'}")
                            print(f"      - Estado Yappy: {yappy_status}")
                            print(f"      - Monto: ${amount/100:.2f}" if amount else "      - Monto: N/A")
                            
                            if status == 'succeeded':
                                print(f"   ✅ PAGO CONFIRMADO - El sistema debería actualizar el estado automáticamente")
                            elif status == 'pending':
                                print(f"   ⏳ Pago aún pendiente en Yappy")
                            else:
                                print(f"   📝 Estado: {status}")
                else:
                    print(f"   ❌ Error en verificación: {yappy_data.get('note', 'Error desconocido') if isinstance(yappy_data, dict) else 'Error desconocido'}")
                    
            except Exception as e:
                print(f"   ❌ Error al verificar: {e}")
                import traceback
                traceback.print_exc()
            
            print()
        
        conn.close()
        
        print(f"{'='*60}")
        print(f"✅ Prueba completada")
        print(f"{'='*60}\n")
        
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

if __name__ == '__main__':
    test_verification()
