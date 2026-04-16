"""Admin: respaldos de base de datos SQLite."""

import os
import shutil
import traceback
from datetime import datetime

from flask import Blueprint, jsonify, render_template, send_file

admin_backup_bp = Blueprint('admin_backup', __name__)


def _project_root():
    """Raíz del repo (backend/nodeone/modules/admin_backup → 4 niveles arriba)."""
    return os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))


def _system_settings_required(f):
    """Misma regla que el ítem «Respaldos» en base.html (system.settings.view)."""
    import app as M

    return M.require_permission('system.settings.view')(f)


@admin_backup_bp.route('/admin/backup')
@_system_settings_required
def admin_backup():
    """Panel de respaldo de base de datos"""
    project_root = _project_root()
    backups_dir = os.path.join(project_root, 'backups')
    backups = []

    if os.path.exists(backups_dir):
        for filename in sorted(os.listdir(backups_dir), reverse=True):
            if filename.startswith('nodeone_backup_') and filename.endswith('.db'):
                filepath = os.path.join(backups_dir, filename)
                file_stat = os.stat(filepath)
                backups.append({
                    'filename': filename,
                    'size': file_stat.st_size,
                    'size_mb': round(file_stat.st_size / (1024 * 1024), 2),
                    'created_at': datetime.fromtimestamp(file_stat.st_mtime),
                    'path': filepath
                })

    return render_template('admin/backup.html', backups=backups)


@admin_backup_bp.route('/admin/backup/create', methods=['POST'])
@_system_settings_required
def create_backup():
    """Crear respaldo de base de datos y devolverlo para descarga"""
    try:
        project_root = _project_root()
        db_path = os.path.join(project_root, 'instance', 'membership_legacy.db')
        backups_dir = os.path.join(project_root, 'backups')

        os.makedirs(backups_dir, exist_ok=True)

        if not os.path.exists(db_path):
            return jsonify({'success': False, 'error': 'Base de datos no encontrada'}), 404

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_filename = f'nodeone_backup_{timestamp}.db'
        backup_path = os.path.join(backups_dir, backup_filename)

        shutil.copy2(db_path, backup_path)

        print(f"✅ Respaldo creado por admin: {backup_filename}")

        return send_file(
            backup_path,
            as_attachment=True,
            download_name=backup_filename,
            mimetype='application/x-sqlite3'
        )

    except Exception as e:
        print(f"❌ Error al crear respaldo: {e}")
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_backup_bp.route('/admin/backup/download/<filename>')
@_system_settings_required
def download_backup(filename):
    """Descargar un respaldo existente"""
    try:
        if not filename.startswith('nodeone_backup_') or not filename.endswith('.db'):
            return jsonify({'success': False, 'error': 'Nombre de archivo inválido'}), 400

        project_root = _project_root()
        backup_path = os.path.join(project_root, 'backups', filename)

        if not os.path.exists(backup_path):
            return jsonify({'success': False, 'error': 'Respaldo no encontrado'}), 404

        return send_file(
            backup_path,
            as_attachment=True,
            download_name=filename,
            mimetype='application/x-sqlite3'
        )

    except Exception as e:
        print(f"❌ Error al descargar respaldo: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_backup_bp.route('/admin/backup/delete/<filename>', methods=['POST'])
@_system_settings_required
def delete_backup(filename):
    """Eliminar un respaldo"""
    try:
        if not filename.startswith('nodeone_backup_') or not filename.endswith('.db'):
            return jsonify({'success': False, 'error': 'Nombre de archivo inválido'}), 400

        project_root = _project_root()
        backup_path = os.path.join(project_root, 'backups', filename)

        if not os.path.exists(backup_path):
            return jsonify({'success': False, 'error': 'Respaldo no encontrado'}), 404

        os.remove(backup_path)

        return jsonify({'success': True, 'message': 'Respaldo eliminado exitosamente'})

    except Exception as e:
        print(f"❌ Error al eliminar respaldo: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_backup_bp.route('/admin/backup/restore/<filename>', methods=['POST'])
@_system_settings_required
def restore_backup(filename):
    """Restaurar base de datos desde un respaldo"""
    try:
        if not filename.startswith('nodeone_backup_') or not filename.endswith('.db'):
            return jsonify({'success': False, 'error': 'Nombre de archivo inválido'}), 400

        project_root = _project_root()
        backup_path = os.path.join(project_root, 'backups', filename)
        db_path = os.path.join(project_root, 'instance', 'membership_legacy.db')

        if not os.path.exists(backup_path):
            return jsonify({'success': False, 'error': 'Respaldo no encontrado'}), 404

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        safety_backup = os.path.join(project_root, 'backups', f'safety_backup_before_restore_{timestamp}.db')

        if os.path.exists(db_path):
            shutil.copy2(db_path, safety_backup)
            print(f"✅ Respaldo de seguridad creado: {safety_backup}")

        shutil.copy2(backup_path, db_path)

        print(f"✅ Base de datos restaurada desde: {filename}")

        return jsonify({
            'success': True,
            'message': f'Base de datos restaurada exitosamente desde {filename}. Se creó un respaldo de seguridad antes de la restauración.'
        })

    except Exception as e:
        print(f"❌ Error al restaurar respaldo: {e}")
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500
