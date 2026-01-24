#!/usr/bin/env python3
"""
Script para confirmar manualmente un pago pendiente de Yappy
Útil cuando la API de Yappy no responde o el pago necesita confirmación manual
"""

import sys
import os
from pathlib import Path
from datetime import datetime

# Agregar el directorio del backend al path
backend_dir = Path(__file__).parent
project_dir = backend_dir.parent
sys.path.insert(0, str(backend_dir))

os.chdir(backend_dir)

try:
    import sqlite3
    
    def find_database():
        """Encontrar la base de datos"""
        possible_paths = [
            project_dir / 'instance' / 'relaticpanama.db',
            backend_dir / 'instance' / 'relaticpanama.db',
            backend_dir / 'relaticpanama.db',
            project_dir / 'relaticpanama.db',
        ]
        
        for path in possible_paths:
            if path.exists():
                return str(path)
        
        return None
    
    def confirm_payment_manually(payment_id=None, payment_reference=None, yappy_transaction_id=None):
        """Confirmar un pago manualmente"""
        db_path = find_database()
        
        if not db_path:
            print("❌ No se encontró la base de datos")
            return False
        
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Buscar el pago
        query = "SELECT * FROM payment WHERE "
        params = []
        
        if payment_id:
            query += "id = ?"
            params.append(payment_id)
        elif yappy_transaction_id:
            query += "yappy_transaction_id = ? OR payment_reference = ?"
            params.extend([yappy_transaction_id, yappy_transaction_id])
        elif payment_reference:
            query += "payment_reference = ?"
            params.append(payment_reference)
        else:
            print("❌ Debes proporcionar payment_id, payment_reference o yappy_transaction_id")
            conn.close()
            return False
        
        cursor.execute(query, params)
        payment = cursor.fetchone()
        
        if not payment:
            print(f"❌ Pago no encontrado")
            conn.close()
            return False
        
        if payment['status'] == 'succeeded':
            print(f"✅ El pago {payment['id']} ya está confirmado")
            conn.close()
            return True
        
        print(f"\n📊 Pago encontrado:")
        print(f"   Payment ID: {payment['id']}")
        print(f"   Usuario: {payment['user_id']}")
        print(f"   Monto: ${payment['amount']/100:.2f}")
        print(f"   Estado actual: {payment['status']}")
        print(f"   Referencia: {payment['payment_reference']}")
        print(f"   Yappy Transaction ID: {payment['yappy_transaction_id'] or 'N/A'}")
        
        # Confirmar el pago
        print(f"\n🔄 Confirmando pago...")
        
        try:
            # Actualizar estado
            cursor.execute("""
                UPDATE payment 
                SET status = 'succeeded',
                    paid_at = ?,
                    updated_at = ?
                WHERE id = ?
            """, (datetime.utcnow().isoformat(), datetime.utcnow().isoformat(), payment['id']))
            
            conn.commit()
            
            print(f"✅ Pago {payment['id']} confirmado manualmente")
            print(f"   Estado: pending → succeeded")
            print(f"   Fecha de pago: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}")
            
            # Verificar si hay items en el carrito que necesiten procesarse
            cursor.execute("""
                SELECT COUNT(*) as count FROM cart_item 
                WHERE cart_id IN (SELECT id FROM cart WHERE user_id = ?)
            """, (payment['user_id'],))
            cart_items = cursor.fetchone()['count']
            
            if cart_items > 0:
                print(f"\n⚠️ Hay {cart_items} items en el carrito que necesitan procesarse")
                print(f"   Ejecuta el procesamiento del carrito desde la aplicación Flask")
                print(f"   O usa: python3 process_cart_for_payment.py {payment['id']}")
            
            # Verificar suscripciones
            cursor.execute("""
                SELECT COUNT(*) as count FROM subscription WHERE payment_id = ?
            """, (payment['id'],))
            subscriptions = cursor.fetchone()['count']
            
            if subscriptions > 0:
                print(f"✅ Ya hay {subscriptions} suscripción(es) creada(s) para este pago")
            else:
                print(f"⚠️ No hay suscripciones creadas. El carrito necesita procesarse.")
            
            conn.close()
            return True
            
        except Exception as e:
            print(f"❌ Error confirmando pago: {e}")
            import traceback
            traceback.print_exc()
            conn.rollback()
            conn.close()
            return False
    
    # Ejecutar confirmación
    if __name__ == '__main__':
        import sys
        
        if len(sys.argv) > 1:
            # Si se pasa un argumento, puede ser payment_id o código
            arg = sys.argv[1]
            if arg.isdigit():
                confirm_payment_manually(payment_id=int(arg))
            elif arg.startswith('EBOWR-') or arg.startswith('YAPPY-'):
                confirm_payment_manually(yappy_transaction_id=arg)
            else:
                confirm_payment_manually(payment_reference=arg)
        else:
            # Confirmar el pago específico mencionado
            print("🔍 Confirmando pago EBOWR-38807178 / YAPPY-D298C08DE0C03D74\n")
            confirm_payment_manually(yappy_transaction_id='EBOWR-38807178')

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
