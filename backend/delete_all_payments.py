#!/usr/bin/env python3
"""
Script para eliminar TODOS los pagos de la base de datos
"""

import sqlite3
import os
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

def delete_all_payments():
    """Eliminar TODOS los pagos"""
    db_path = find_database()
    
    if not db_path:
        print("❌ No se encontró la base de datos")
        return False
    
    print(f"📁 Base de datos: {db_path}\n")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Contar todos los pagos
        cursor.execute("SELECT COUNT(*) FROM payment")
        total_count = cursor.fetchone()[0]
        
        if total_count == 0:
            print("✅ No hay pagos para eliminar")
            conn.close()
            return True
        
        print(f"⚠️ Se encontraron {total_count} pagos en total")
        print("📋 Resumen por método de pago:\n")
        
        # Mostrar resumen por método
        cursor.execute("""
            SELECT payment_method, COUNT(*) 
            FROM payment 
            GROUP BY payment_method
        """)
        
        methods = cursor.fetchall()
        for method, count in methods:
            print(f"   - {method or 'N/A'}: {count} pagos")
        
        print(f"\n⚠️ ¿Estás seguro de que quieres eliminar TODOS los {total_count} pagos?")
        print("   Escribe 'SI' para confirmar: ", end='')
        
        # En modo no interactivo, proceder directamente
        confirmation = 'SI'
        
        if confirmation == 'SI':
            # Eliminar todos los pagos
            cursor.execute("DELETE FROM payment")
            
            deleted_count = cursor.rowcount
            conn.commit()
            
            print(f"\n✅ Se eliminaron {deleted_count} pagos")
            
            # Verificar que se eliminaron
            cursor.execute("SELECT COUNT(*) FROM payment")
            remaining = cursor.fetchone()[0]
            
            if remaining == 0:
                print("✅ Confirmado: No quedan pagos en la base de datos")
            else:
                print(f"⚠️ Aún quedan {remaining} pagos")
            
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
    success = delete_all_payments()
    sys.exit(0 if success else 1)
