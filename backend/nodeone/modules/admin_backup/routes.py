"""Admin: respaldos de base de datos (PostgreSQL del silo o SQLite legacy local)."""

import os
import shutil
import traceback
from datetime import datetime

from flask import Blueprint, jsonify, render_template, send_file

from nodeone.services.admin_database_backup import (
    create_postgresql_backup,
    create_sqlite_backup,
    is_postgresql_backend,
    list_all_backups,
    mimetype_for_filename,
    resolve_admin_backup_path,
    resolve_server_backup_path,
    sqlite_db_path,
)

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
    """Panel de respaldo de base de datos."""
    project_root = _project_root()
    admin_backups, server_backups, meta = list_all_backups(project_root)
    return render_template(
        'admin/backup.html',
        backups=admin_backups,
        server_backups=server_backups,
        backup_meta=meta,
    )


@admin_backup_bp.route('/admin/backup/create', methods=['POST'])
@_system_settings_required
def create_backup():
    """Crear respaldo y devolverlo para descarga."""
    try:
        project_root = _project_root()
        if is_postgresql_backend():
            backup_path, backup_filename = create_postgresql_backup(project_root)
            mimetype = mimetype_for_filename(backup_filename)
        else:
            backup_path, backup_filename = create_sqlite_backup(project_root)
            mimetype = mimetype_for_filename(backup_filename)

        print(f'✅ Respaldo creado por admin: {backup_filename}')

        return send_file(
            backup_path,
            as_attachment=True,
            download_name=backup_filename,
            mimetype=mimetype,
        )

    except FileNotFoundError:
        return jsonify({'success': False, 'error': 'Base de datos no encontrada'}), 404
    except Exception as e:
        print(f'❌ Error al crear respaldo: {e}')
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_backup_bp.route('/admin/backup/download/<filename>')
@_system_settings_required
def download_backup(filename):
    """Descargar un respaldo creado desde el panel."""
    try:
        project_root = _project_root()
        backup_path = resolve_admin_backup_path(project_root, filename)
        if not backup_path:
            return jsonify({'success': False, 'error': 'Respaldo no encontrado'}), 404

        return send_file(
            backup_path,
            as_attachment=True,
            download_name=filename,
            mimetype=mimetype_for_filename(filename),
        )

    except Exception as e:
        print(f'❌ Error al descargar respaldo: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_backup_bp.route('/admin/backup/download-server/<filename>')
@_system_settings_required
def download_server_backup(filename):
    """Descargar respaldo automático del servidor (solo lectura)."""
    try:
        backup_path = resolve_server_backup_path(filename)
        if not backup_path:
            return jsonify({'success': False, 'error': 'Respaldo no encontrado'}), 404

        return send_file(
            backup_path,
            as_attachment=True,
            download_name=filename,
            mimetype=mimetype_for_filename(filename),
        )

    except Exception as e:
        print(f'❌ Error al descargar respaldo del servidor: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_backup_bp.route('/admin/backup/delete/<filename>', methods=['POST'])
@_system_settings_required
def delete_backup(filename):
    """Eliminar un respaldo creado desde el panel."""
    try:
        project_root = _project_root()
        backup_path = resolve_admin_backup_path(project_root, filename)
        if not backup_path:
            return jsonify({'success': False, 'error': 'Respaldo no encontrado'}), 404

        os.remove(backup_path)
        return jsonify({'success': True, 'message': 'Respaldo eliminado exitosamente'})

    except Exception as e:
        print(f'❌ Error al eliminar respaldo: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_backup_bp.route('/admin/backup/restore/<filename>', methods=['POST'])
@_system_settings_required
def restore_backup(filename):
    """Restaurar base de datos desde un respaldo SQLite legacy."""
    try:
        if is_postgresql_backend():
            return jsonify({
                'success': False,
                'error': (
                    'La restauración de PostgreSQL no está disponible desde el panel. '
                    'Contacte al equipo de operaciones o use pg_restore en el servidor.'
                ),
            }), 400

        if not filename.startswith('nodeone_backup_') or not filename.endswith('.db'):
            return jsonify({'success': False, 'error': 'Nombre de archivo inválido'}), 400

        project_root = _project_root()
        backup_path = resolve_admin_backup_path(project_root, filename)
        db_path = sqlite_db_path(project_root)

        if not backup_path:
            return jsonify({'success': False, 'error': 'Respaldo no encontrado'}), 404

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        safety_backup = os.path.join(
            project_root, 'backups', f'safety_backup_before_restore_{timestamp}.db'
        )

        if os.path.exists(db_path):
            shutil.copy2(db_path, safety_backup)
            print(f'✅ Respaldo de seguridad creado: {safety_backup}')

        shutil.copy2(backup_path, db_path)

        print(f'✅ Base de datos restaurada desde: {filename}')

        return jsonify({
            'success': True,
            'message': (
                f'Base de datos restaurada exitosamente desde {filename}. '
                'Se creó un respaldo de seguridad antes de la restauración.'
            ),
        })

    except Exception as e:
        print(f'❌ Error al restaurar respaldo: {e}')
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500
