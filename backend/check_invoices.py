#!/usr/bin/env python3
"""
Script para verificar facturas en la base de datos
"""

import sqlite3
from pathlib import Path

def find_database():
    """Encontrar la base de datos"""
    backend_dir = Path(__file__).parent
    project_root = backend_dir.parent
    
    possible_paths = [
        project_root / 'instance' / 'relaticpanama.db',
        backend_dir / 'instance' / 'relaticpanama.db',
        backend_dir / 'relaticpanama.db',
        project_root / 'relaticpanama.db',
    ]
    
    for path in possible_paths:
        if path.exists():
            return str(path)
    
    return None

def check_invoices():
    """Verificar facturas"""
    db_path = find_database()
    
    if not db_path:
        print("❌ No se encontró la base de datos")
        return
    
    print(f"📁 Base de datos: {db_path}\n")
    
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Buscar todas las facturas
        cursor.execute("""
            SELECT id, user_id, invoice_number, amount, total_amount, status, 
                   created_at, due_date, paid_at, description
            FROM invoice 
            ORDER BY created_at DESC
            LIMIT 20
        """)
        
        invoices = cursor.fetchall()
        
        if not invoices:
            print("❌ No se encontraron facturas en la base de datos")
            return
        
        print(f"📊 Encontradas {len(invoices)} facturas (últimas 20):\n")
        print(f"{'ID':<8} {'User ID':<10} {'Número':<25} {'Monto':<12} {'Estado':<20} {'Creado':<20}")
        print("-" * 120)
        
        for inv in invoices:
            amount = f"${inv['total_amount']:.2f}" if inv['total_amount'] else 'N/A'
            status = inv['status'] or 'unknown'
            created = inv['created_at'] or 'N/A'
            
            print(f"{inv['id']:<8} {inv['user_id']:<10} {inv['invoice_number']:<25} {amount:<12} {status:<20} {created:<20}")
        
        # Buscar pagos asociados a facturas
        print(f"\n🔍 Buscando pagos asociados a facturas...")
        cursor.execute("""
            SELECT COUNT(*) 
            FROM payment 
            WHERE invoice_id IS NOT NULL
        """)
        
        payments_with_invoice = cursor.fetchone()[0]
        print(f"   Pagos con factura asociada: {payments_with_invoice}")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    check_invoices()
