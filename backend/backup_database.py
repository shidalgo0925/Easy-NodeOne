#!/usr/bin/env python3
"""
Script para respaldar la base de datos de RelaticPanama
"""

import os
import shutil
from datetime import datetime

def backup_database():
    """Crear respaldo de la base de datos"""
    
    # Rutas
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    db_path = os.path.join(project_root, 'instance', 'relaticpanama.db')
    backups_dir = os.path.join(project_root, 'backups')
    
    # Crear directorio de backups si no existe
    os.makedirs(backups_dir, exist_ok=True)
    
    # Verificar que la base de datos existe
    if not os.path.exists(db_path):
        print(f"❌ Base de datos no encontrada en: {db_path}")
        return False
    
    # Generar nombre de respaldo con timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_filename = f'relaticpanama_backup_{timestamp}.db'
    backup_path = os.path.join(backups_dir, backup_filename)
    
    try:
        # Copiar base de datos
        shutil.copy2(db_path, backup_path)
        
        # Obtener tamaño
        size_kb = os.path.getsize(backup_path) / 1024
        
        print(f"✅ Respaldo creado exitosamente:")
        print(f"   📁 Ubicación: {backup_path}")
        print(f"   📊 Tamaño: {size_kb:.2f} KB")
        print(f"   🕐 Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Limpiar backups antiguos (mantener solo los últimos 10)
        cleanup_old_backups(backups_dir)
        
        return True
        
    except Exception as e:
        print(f"❌ Error al crear respaldo: {e}")
        return False

def cleanup_old_backups(backups_dir, keep=10):
    """Eliminar backups antiguos, mantener solo los últimos N"""
    try:
        backups = []
        for filename in os.listdir(backups_dir):
            if filename.startswith('relaticpanama_backup_') and filename.endswith('.db'):
                filepath = os.path.join(backups_dir, filename)
                backups.append((os.path.getmtime(filepath), filepath))
        
        # Ordenar por fecha (más reciente primero)
        backups.sort(reverse=True)
        
        # Eliminar backups antiguos
        if len(backups) > keep:
            for _, old_backup in backups[keep:]:
                os.remove(old_backup)
                print(f"🗑️  Backup antiguo eliminado: {os.path.basename(old_backup)}")
                
    except Exception as e:
        print(f"⚠️  Error al limpiar backups antiguos: {e}")

if __name__ == '__main__':
    print("🔄 Iniciando respaldo de base de datos...")
    backup_database()
    print("✅ Proceso de respaldo completado.")


