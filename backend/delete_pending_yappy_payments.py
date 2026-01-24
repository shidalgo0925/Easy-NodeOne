#!/usr/bin/env python3
"""
Script para eliminar todos los pagos pendientes de Yappy
"""

import sqlite3
import os
from pathlib import Path
from datetime import datetime

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

def delete_pending_payments():
    """Eliminar pagos pendientes de Yappy"""
    db_path = find_database()
    
    if not db_path:
        print("❌ No se encontró la base de datos")
        return False
    
    print(f"📁 Base de datos: {db_path}\n")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Primero contar los pagos pendientes
        cursor.execute("""
            SELECT COUNT(*) 
            FROM payment 
            WHERE payment_method = 'yappy'
            AND status IN ('pending', 'awaiting_confirmation')
        """)
        
        count = cursor.fetchone()[0]
        
        if count == 0:
            print("✅ No hay pagos pendientes de Yappy para eliminar")
            conn.close()
            return True
        
        print(f"⚠️ Se encontraron {count} pagos pendientes de Yappy")
        print("📋 Lista de pagos que se eliminarán:\n")
        
        # Mostrar los pagos que se van a eliminar
        cursor.execute("""
            SELECT id, user_id, amount, status, payment_reference, created_at
            FROM payment 
            WHERE payment_method = 'yappy'
            AND status IN ('pending', 'awaiting_confirmation')
            ORDER BY created_at DESC
        """)
        
        payments = cursor.fetchall()
        
        for p in payments:
            amount = f"${p[2]/100:.2f}" if p[2] else 'N/A'
            print(f"   - Payment ID: {p[0]}, User: {p[1]}, Monto: {amount}, Referencia: {p[4]}, Creado: {p[5]}")
        
        print(f"\n⚠️ ¿Estás seguro de que quieres eliminar estos {count} pagos?")
        print("   Escribe 'SI' para confirmar: ", end='')
        
        # En modo no interactivo, proceder directamente
        confirmation = 'SI'
        
        if confirmation == 'SI':
            # Eliminar los pagos pendientes
            cursor.execute("""
                DELETE FROM payment 
                WHERE payment_method = 'yappy'
                AND status IN ('pending', 'awaiting_confirmation')
            """)
            
            deleted_count = cursor.rowcount
            conn.commit()
            
            print(f"\n✅ Se eliminaron {deleted_count} pagos pendientes de Yappy")
            
            # Verificar que se eliminaron
            cursor.execute("""
                SELECT COUNT(*) 
                FROM payment 
                WHERE payment_method = 'yappy'
                AND status IN ('pending', 'awaiting_confirmation')
            """)
            
            remaining = cursor.fetchone()[0]
            
            if remaining == 0:
                print("✅ Confirmado: No quedan pagos pendientes de Yappy")
            else:
                print(f"⚠️ Aún quedan {remaining} pagos pendientes")
            
            conn.close()
            return True
        else:
            print("\n❌ Operación cancelada")
            conn.close()
            return False
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        return False

if __name__ == '__main__':
    import sys
    # En modo no interactivo, proceder directamente
    success = delete_pending_payments()
    sys.exit(0 if success else 1)
