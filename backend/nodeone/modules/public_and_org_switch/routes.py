"""Registro de rutas publicas y cambio de organizacion (legacy endpoints)."""


def register_public_and_org_switch_routes(app):
    from flask import flash, jsonify, redirect, render_template, request, session, url_for
    from flask_login import current_user, login_required

    from app import (
        admin_required,
        default_organization_id,
        get_user_home_organization_id,
        ORG_HOME,
        ORG_NONE,
        SaasOrganization,
        single_tenant_default_only,
        user_has_access_to_organization,
    )

    @app.route('/set-organization', methods=['POST'])
    @login_required
    def set_organization():
        """Cambiar organizacion activa (sesion). JSON: { organization_id: int | ORG_HOME }."""
        if single_tenant_default_only() and not getattr(current_user, 'is_admin', False):
            return jsonify({'error': 'Modo solo organización por defecto; cambio de empresa deshabilitado.'}), 403
        if not request.is_json:
            return jsonify({'error': 'Se requiere JSON'}), 400
        body = request.get_json(silent=True) or {}
        raw = body.get('organization_id')
        if raw in (ORG_HOME, ORG_NONE) or raw is None:
            home = get_user_home_organization_id()
            session['organization_id'] = home
            app.logger.info('User %s switched to home organization %s', current_user.id, home)
            return jsonify({'success': True, 'organization_id': home})
        try:
            cand = int(raw)
        except (TypeError, ValueError):
            return jsonify({'error': 'organization_id invalido'}), 400
        org = SaasOrganization.query.get(cand)
        if org is None:
            return jsonify({'error': 'Organization not found'}), 404
        if not getattr(org, 'is_active', True):
            return jsonify({'error': 'Organizacion no disponible'}), 403
        if not user_has_access_to_organization(current_user, cand):
            return jsonify({'error': 'Unauthorized'}), 403
        session['organization_id'] = cand
        app.logger.info('User %s switched to organization %s', current_user.id, cand)
        return jsonify({'success': True, 'organization_id': cand})

    @app.route('/admin/switch-organization', methods=['GET', 'POST'])
    @admin_required
    def admin_switch_organization():
        """Compatibilidad: mismo criterio que POST /set-organization (formulario GET/POST)."""
        if single_tenant_default_only() and not getattr(current_user, 'is_admin', False):
            session['organization_id'] = default_organization_id()
            flash('Modo solo organización por defecto: el cambio de empresa está deshabilitado.', 'info')
            return redirect(request.referrer or url_for('dashboard'))
        if request.method == 'GET':
            q = (request.args.get('organization_id') or '').strip()
            if not q:
                flash(
                    'Para cambiar la empresa de trabajo usá el menú lateral: bloque «Empresa», elegí la empresa activa y pulsá Aplicar.',
                    'info',
                )
                return redirect(url_for('dashboard'))
            raw = q
        else:
            raw = (request.form.get('organization_id') or '').strip()
        if raw in (ORG_HOME, ORG_NONE):
            session['organization_id'] = get_user_home_organization_id()
            app.logger.info('User %s switched to home organization (form)', current_user.id)
            flash('Empresa activa: organización asignada a tu usuario.', 'info')
            return redirect(request.referrer or url_for('dashboard'))
        try:
            cand = int(raw)
        except (TypeError, ValueError):
            flash('Organización no válida.', 'error')
            return redirect(request.referrer or url_for('dashboard'))
        org = SaasOrganization.query.get(cand)
        if org is None:
            flash('Organización no encontrada.', 'error')
            return redirect(request.referrer or url_for('dashboard'))
        if not getattr(org, 'is_active', True):
            flash('Organización no disponible.', 'error')
            return redirect(request.referrer or url_for('dashboard'))
        if not user_has_access_to_organization(current_user, cand):
            flash('No tienes acceso a esa organización.', 'error')
            return redirect(request.referrer or url_for('dashboard'))
        session['organization_id'] = cand
        app.logger.info('User %s switched to organization %s (form)', current_user.id, cand)
        flash('Empresa activa actualizada.', 'success')
        return redirect(request.referrer or url_for('dashboard'))

    @app.route('/')
    def index():
        """Redirige a login (sin landing)."""
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))
        return redirect(url_for('auth.login'))

    @app.route('/promocion')
    def promocion():
        """Pagina de promocion de servicios - Standalone"""
        return render_template('promocion.html')
