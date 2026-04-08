"""Admin: respaldos de base de datos SQLite."""

import os
import shutil
import traceback
from datetime import datetime
from functools import wraps

from flask import Blueprint, flash, jsonify, redirect, render_template, send_file, url_for
from flask_login import current_user, login_required

admin_backup_bp = Blueprint('admin_backup', __name__)


def _project_root():
    """Raíz del repo (backend/nodeone/modules/admin_backup → 4 niveles arriba)."""
    return os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))


def _admin_required_lazy(f):
    """Igual que app.admin_required; importa app en request (evita ciclo)."""
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        import app as M

        if bool(getattr(current_user, 'must_change_password', False)):
            flash('Debes cambiar tu contraseña antes de continuar.', 'warning')
            return redirect(url_for('auth.change_password'))
        if not current_user.is_admin and not M._user_has_any_admin_permission(current_user):
            flash('No tienes permisos para acceder a esta página.', 'error')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)

    return decorated_function


@admin_backup_bp.route('/admin/backup')
@_admin_required_lazy
def admin_backup():
    """Panel de respaldo de base de datos"""
    project_root = _project_root()
    backups_dir = os.path.join(project_root, 'backups')
    backups = []

    if os.path.exists(backups_dir):
        for filename in sorted(os.listdir(backups_dir), reverse=True):
            if filename.startswith('relaticpanama_backup_') and filename.endswith('.db'):
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
@_admin_required_lazy
def create_backup():
    """Crear respaldo de base de datos y devolverlo para descarga"""
    try:
        project_root = _project_root()
        db_path = os.path.join(project_root, 'instance', 'relaticpanama.db')
        backups_dir = os.path.join(project_root, 'backups')

        os.makedirs(backups_dir, exist_ok=True)

        if not os.path.exists(db_path):
            return jsonify({'success': False, 'error': 'Base de datos no encontrada'}), 404

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_filename = f'relaticpanama_backup_{timestamp}.db'
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
@_admin_required_lazy
def download_backup(filename):
    """Descargar un respaldo existente"""
    try:
        if not filename.startswith('relaticpanama_backup_') or not filename.endswith('.db'):
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
@_admin_required_lazy
def delete_backup(filename):
    """Eliminar un respaldo"""
    try:
        if not filename.startswith('relaticpanama_backup_') or not filename.endswith('.db'):
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
@_admin_required_lazy
def restore_backup(filename):
    """Restaurar base de datos desde un respaldo"""
    try:
        if not filename.startswith('relaticpanama_backup_') or not filename.endswith('.db'):
            return jsonify({'success': False, 'error': 'Nombre de archivo inválido'}), 400

        project_root = _project_root()
        backup_path = os.path.join(project_root, 'backups', filename)
        db_path = os.path.join(project_root, 'instance', 'relaticpanama.db')

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
