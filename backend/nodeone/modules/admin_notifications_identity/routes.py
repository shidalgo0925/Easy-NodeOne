"""Registro de rutas admin notifications + identity en app (endpoints legacy)."""

def register_admin_notifications_identity_routes(app):
    from datetime import datetime

    from flask import flash, jsonify, redirect, render_template, request, url_for

    from app import SaasOrganization, admin_required, db, NotificationSettings

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
            try:
                from nodeone.services.notification_settings_sync import (
                    sync_notification_type_to_communication_rules,
                )

                sync_notification_type_to_communication_rules(
                    setting.notification_type, setting.enabled
                )
            except Exception:
                pass
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
        sync_pairs = []
        for update in updates:
            setting_id = update.get('id')
            enabled = update.get('enabled')

            if setting_id and enabled is not None:
                setting = NotificationSettings.query.get(setting_id)
                if setting:
                    setting.enabled = bool(enabled)
                    setting.updated_at = datetime.utcnow()
                    updated_count += 1
                    sync_pairs.append((setting.notification_type, setting.enabled))

        db.session.commit()

        try:
            from nodeone.services.notification_settings_sync import (
                sync_notification_type_to_communication_rules,
            )

            for nt, en in sync_pairs:
                sync_notification_type_to_communication_rules(nt, en)
        except Exception:
            pass

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
        """Redirige al wizard unificado de empresa (paso branding)."""
        return redirect(url_for('admin_company_setup', step='branding'))

    @app.route('/admin/company', methods=['GET', 'POST'])
    @admin_required
    def admin_company_setup():
        """Wizard de empresa para el tenant activo (fiscal + branding)."""
        from nodeone.services.company_wizard import (
            enrich_company_wizard_context,
            fiscal_payload_from_form,
            identity_settings_dict,
            resolve_initial_wizard_step,
            save_identity_from_form,
        )
        from nodeone.services.org_scope import admin_data_scope_organization_id
        from nodeone.services.saas_org_fiscal_schema import ensure_saas_organization_fiscal_columns

        ensure_saas_organization_fiscal_columns(db, db.engine)
        oid = int(admin_data_scope_organization_id())
        org = SaasOrganization.query.get_or_404(oid)
        step_arg = request.args.get('step') if request.method == 'GET' else request.form.get('wizard_step')

        if request.method == 'POST':
            fiscal = fiscal_payload_from_form(request.form)
            for key, value in fiscal.items():
                setattr(org, key, value)
            id_err = save_identity_from_form(request.form, oid)
            if id_err:
                flash(id_err, 'error')
                ctx = enrich_company_wizard_context(
                    {
                        'wizard_mode': 'tenant',
                        'org': org,
                        'form': request.form,
                        'google_oauth': None,
                        'identity_settings': identity_settings_dict(oid),
                        'initial_step': resolve_initial_wizard_step(mode='tenant', step_arg=step_arg),
                        'show_onboarding_rail': False,
                    }
                )
                return render_template('admin/company_wizard.html', **ctx)
            try:
                db.session.commit()
                flash('Configuración de empresa guardada.', 'success')
                return redirect(url_for('admin_company_setup', step='opciones'))
            except Exception as exc:
                db.session.rollback()
                flash('No se pudo guardar: %s' % (exc,), 'error')

        ctx = enrich_company_wizard_context(
            {
                'wizard_mode': 'tenant',
                'org': org,
                'form': None,
                'google_oauth': None,
                'identity_settings': identity_settings_dict(oid),
                'initial_step': resolve_initial_wizard_step(mode='tenant', step_arg=step_arg),
                'show_onboarding_rail': False,
            }
        )
        return render_template('admin/company_wizard.html', **ctx)
