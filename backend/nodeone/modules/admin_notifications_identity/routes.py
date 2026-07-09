"""Registro de rutas admin notifications + identity en app (endpoints legacy)."""

from nodeone.services.company_wizard import IDENTITY_PRESETS, validate_hex_color


def register_admin_notifications_identity_routes(app):
    import re
    from datetime import datetime

    from flask import flash, jsonify, redirect, render_template, request, url_for

    from app import SaasOrganization, admin_required, db, NotificationSettings, OrganizationSettings

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
            if not all((validate_hex_color(primary), validate_hex_color(primary_dark), validate_hex_color(accent))):
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

    @app.route('/api/admin/company-fiscal-profile', methods=['GET', 'POST'])
    @admin_required
    def api_company_fiscal_profile():
        try:
            from nodeone.services.org_scope import admin_data_scope_organization_id
            from nodeone.services.saas_org_fiscal_schema import ensure_saas_organization_fiscal_columns

            ensure_saas_organization_fiscal_columns(db, db.engine)
            oid = int(admin_data_scope_organization_id())
        except Exception as e:
            return jsonify({'success': False, 'error': f'organization_context_error: {e}'}), 400

        org = SaasOrganization.query.get(oid)
        if not org:
            return jsonify({'success': False, 'error': 'organization_not_found'}), 404

        def _payload():
            return {
                'organization_id': int(org.id),
                'name': (org.name or '').strip(),
                'legal_name': (getattr(org, 'legal_name', None) or '').strip(),
                'tax_id': (getattr(org, 'tax_id', None) or '').strip(),
                'tax_regime': (getattr(org, 'tax_regime', None) or '').strip(),
                'fiscal_address': (getattr(org, 'fiscal_address', None) or '').strip(),
                'fiscal_city': (getattr(org, 'fiscal_city', None) or '').strip(),
                'fiscal_state': (getattr(org, 'fiscal_state', None) or '').strip(),
                'fiscal_country': (getattr(org, 'fiscal_country', None) or '').strip(),
                'fiscal_phone': (getattr(org, 'fiscal_phone', None) or '').strip(),
                'fiscal_email': (getattr(org, 'fiscal_email', None) or '').strip(),
            }

        if request.method == 'GET':
            return jsonify({'success': True, 'profile': _payload()})

        data = request.get_json(silent=True) or {}
        raw_email = (data.get('fiscal_email') or '').strip()
        if raw_email and not re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', raw_email):
            return jsonify({'success': False, 'error': 'Email fiscal inválido.'}), 400

        updates = {
            'legal_name': (data.get('legal_name') or '').strip() or None,
            'tax_id': (data.get('tax_id') or '').strip() or None,
            'tax_regime': (data.get('tax_regime') or '').strip() or None,
            'fiscal_address': (data.get('fiscal_address') or '').strip() or None,
            'fiscal_city': (data.get('fiscal_city') or '').strip() or None,
            'fiscal_state': (data.get('fiscal_state') or '').strip() or None,
            'fiscal_country': (data.get('fiscal_country') or '').strip() or None,
            'fiscal_phone': (data.get('fiscal_phone') or '').strip() or None,
            'fiscal_email': raw_email or None,
        }
        for k, v in updates.items():
            setattr(org, k, v)
        try:
            db.session.commit()
            return jsonify({'success': True, 'profile': _payload()})
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'error': str(e)}), 500
