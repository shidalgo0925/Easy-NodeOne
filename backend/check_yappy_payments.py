#!/usr/bin/env python3
"""
Script para verificar pagos pendientes de Yappy en la base de datos
"""

import sqlite3
import os
from pathlib import Path

def find_database():
    """Encontrar la base de datos"""
    backend_dir = Path(__file__).parent
    project_root = backend_dir.parent
    
    possible_paths = [
        project_root / 'instance' / 'membership_legacy.db',
        backend_dir / 'instance' / 'membership_legacy.db',
        backend_dir / 'membership_legacy.db',
        project_root / 'membership_legacy.db',
    ]
    
    for path in possible_paths:
        if path.exists():
            return str(path)
    
    return None

def check_payments():
    """Verificar pagos de Yappy"""
    db_path = find_database()
    
    if not db_path:
        print("❌ No se encontró la base de datos")
        return
    
    print(f"📁 Base de datos: {db_path}\n")
    
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Buscar todos los pagos de Yappy
        cursor.execute("""
            SELECT id, user_id, amount, status, payment_reference, payment_method, 
                   created_at, paid_at, payment_url
            FROM payment 
            WHERE payment_method = 'yappy'
            ORDER BY created_at DESC
            LIMIT 20
        """)
        
        payments = cursor.fetchall()
        
        if not payments:
            print("❌ No se encontraron pagos de Yappy en la base de datos")
            return
        
        print(f"📊 Encontrados {len(payments)} pagos de Yappy (últimos 20):\n")
        print(f"{'ID':<8} {'User ID':<10} {'Monto':<12} {'Estado':<20} {'Referencia':<30} {'Creado':<20}")
        print("-" * 120)
        
        pending_count = 0
        for p in payments:
            status = p['status'] or 'unknown'
            reference = p['payment_reference'] or 'N/A'
            amount = f"${p['amount']/100:.2f}" if p['amount'] else 'N/A'
            created = p['created_at'] or 'N/A'
            
            if status in ['pending', 'awaiting_confirmation']:
                pending_count += 1
                print(f"{p['id']:<8} {p['user_id']:<10} {amount:<12} {status:<20} {reference:<30} {created:<20} ⚠️ PENDIENTE")
            else:
                print(f"{p['id']:<8} {p['user_id']:<10} {amount:<12} {status:<20} {reference:<30} {created:<20}")
        
        print(f"\n📋 Resumen:")
        print(f"   - Total de pagos: {len(payments)}")
        print(f"   - Pendientes: {pending_count}")
        
        # Buscar específicamente el código EBOWR-38807178
        print(f"\n🔍 Buscando código EBOWR-38807178...")
        cursor.execute("""
            SELECT id, user_id, amount, status, payment_reference, payment_url, created_at
            FROM payment 
            WHERE payment_method = 'yappy'
            AND (
                payment_reference LIKE '%EBOWR%' OR 
                payment_reference LIKE '%38807178%' OR
                payment_url LIKE '%EBOWR%' OR
                payment_url LIKE '%38807178%'
            )
        """)
        
        matching = cursor.fetchall()
        
        if matching:
            print(f"✅ Encontrados {len(matching)} pagos con código relacionado:\n")
            for p in matching:
                print(f"   Payment ID: {p['id']}")
                print(f"   User ID: {p['user_id']}")
                print(f"   Monto: ${p['amount']/100:.2f}" if p['amount'] else "   Monto: N/A")
                print(f"   Estado: {p['status']}")
                print(f"   Referencia: {p['payment_reference']}")
                print(f"   URL: {p['payment_url']}")
                print(f"   Creado: {p['created_at']}")
                print()
        else:
            print("❌ No se encontró ningún pago con código EBOWR-38807178")
            print("   El código puede estar en otro formato o el pago puede no haberse creado aún")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    check_payments()
