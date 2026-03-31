"""Registro de rutas admin notifications + identity en app (endpoints legacy)."""


IDENTITY_PRESETS = {
    'azul': {'primary_color': '#2563EB', 'primary_color_dark': '#1E3A8A', 'accent_color': '#06B6D4'},
    'verde': {'primary_color': '#059669', 'primary_color_dark': '#047857', 'accent_color': '#10B981'},
    'rojo': {'primary_color': '#DC2626', 'primary_color_dark': '#B91C1C', 'accent_color': '#EF4444'},
    'violeta': {'primary_color': '#7C3AED', 'primary_color_dark': '#5B21B6', 'accent_color': '#A78BFA'},
    'indigo': {'primary_color': '#4F46E5', 'primary_color_dark': '#3730A3', 'accent_color': '#818CF8'},
    'teal': {'primary_color': '#0D9488', 'primary_color_dark': '#0F766E', 'accent_color': '#2DD4BF'},
    'cyan': {'primary_color': '#0891B2', 'primary_color_dark': '#0E7490', 'accent_color': '#22D3EE'},
    'naranja': {'primary_color': '#EA580C', 'primary_color_dark': '#C2410C', 'accent_color': '#FB923C'},
    'ambar': {'primary_color': '#D97706', 'primary_color_dark': '#B45309', 'accent_color': '#FBBF24'},
    'rosa': {'primary_color': '#DB2777', 'primary_color_dark': '#BE185D', 'accent_color': '#F472B6'},
    'slate': {'primary_color': '#475569', 'primary_color_dark': '#334155', 'accent_color': '#94A3B8'},
    'esmeralda': {'primary_color': '#10B981', 'primary_color_dark': '#059669', 'accent_color': '#34D399'},
    'coral': {'primary_color': '#E11D48', 'primary_color_dark': '#BE123C', 'accent_color': '#FB7185'},
}


def _validate_hex(value):
    if not value or not isinstance(value, str):
        return False
    v = value.strip()
    return len(v) == 7 and v[0] == '#' and all(c in '0123456789AaBbCcDdEeFf' for c in v[1:])


def register_admin_notifications_identity_routes(app):
    from datetime import datetime

    from flask import jsonify, render_template, request

    from app import admin_required, db, NotificationSettings, OrganizationSettings

    @app.route('/admin/notifications')
    @admin_required
    def admin_notifications():
        """Panel de configuración de notificaciones"""
        settings = NotificationSettings.get_all_settings()
        return render_template('admin/notifications.html', settings=settings)

    @app.route('/api/admin/notifications')
    @admin_required
    def api_notifications_list():
        """API para obtener todas las configuraciones de notificaciones"""
        settings = NotificationSettings.query.order_by(NotificationSettings.category, NotificationSettings.name).all()
        return jsonify({'settings': [s.to_dict() for s in settings]})

    @app.route('/api/admin/notifications/<int:setting_id>', methods=['PUT'])
    @admin_required
    def api_notification_update(setting_id):
        """API para actualizar una configuración de notificación"""
        setting = NotificationSettings.query.get_or_404(setting_id)
        data = request.get_json()
        if 'enabled' in data:
            setting.enabled = bool(data['enabled'])
            setting.updated_at = datetime.utcnow()
            db.session.commit()
            return jsonify(
                {
                    'success': True,
                    'message': f'Notificación "{setting.name}" {"habilitada" if setting.enabled else "deshabilitada"}',
                    'setting': setting.to_dict(),
                }
            )

        return jsonify({'success': False, 'error': 'Datos inválidos'}), 400

    @app.route('/api/admin/notifications/bulk-update', methods=['POST'])
    @admin_required
    def api_notifications_bulk_update():
        """API para actualizar múltiples configuraciones a la vez"""
        data = request.get_json()
        updates = data.get('updates', [])

        updated_count = 0
        for update in updates:
            setting_id = update.get('id')
            enabled = update.get('enabled')

            if setting_id and enabled is not None:
                setting = NotificationSettings.query.get(setting_id)
                if setting:
                    setting.enabled = bool(enabled)
                    setting.updated_at = datetime.utcnow()
                    updated_count += 1

        db.session.commit()

        return jsonify(
            {
                'success': True,
                'message': f'{updated_count} configuración(es) actualizada(s)',
                'updated': updated_count,
            }
        )

    @app.route('/admin/identity')
    @admin_required
    def admin_identity():
        """Panel de identidad visual (colores y logo por cliente)"""
        s = OrganizationSettings.get_settings_for_session()
        return render_template('admin/identity.html', settings=s.to_dict())

    @app.route('/api/admin/identity', methods=['GET', 'POST'])
    @admin_required
    def api_admin_identity():
        """GET: devolver configuración. POST: guardar (validar HEX y presets)."""
        if request.method == 'GET':
            s = OrganizationSettings.get_settings_for_session()
            return jsonify({'success': True, 'settings': s.to_dict()})
        data = request.get_json(silent=True) or {}
        preset = (data.get('preset') or 'azul').strip().lower()
        if preset in IDENTITY_PRESETS:
            p = IDENTITY_PRESETS[preset]
            s = OrganizationSettings.get_settings_for_session()
            s.primary_color = p['primary_color']
            s.primary_color_dark = p['primary_color_dark']
            s.accent_color = p['accent_color']
            s.preset = preset
        elif preset == 'custom':
            primary = (data.get('primary_color') or '').strip()
            primary_dark = (data.get('primary_color_dark') or '').strip()
            accent = (data.get('accent_color') or '').strip()
            if not all((_validate_hex(primary), _validate_hex(primary_dark), _validate_hex(accent))):
                return jsonify({'success': False, 'error': 'Colores personalizados deben ser HEX válidos (#RRGGBB).'}), 400
            s = OrganizationSettings.get_settings_for_session()
            s.primary_color = primary
            s.primary_color_dark = primary_dark
            s.accent_color = accent
            s.preset = 'custom'
        else:
            return jsonify({'success': False, 'error': 'Preset no válido. Elige un preset de la lista o custom.'}), 400
        try:
            db.session.commit()
            return jsonify({'success': True, 'settings': s.to_dict()})
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'error': str(e)}), 500
