"""Registro de blueprints del módulo Contactos."""

from __future__ import annotations

import os


def register_contacts_blueprints(app) -> None:
    if os.environ.get('NODEONE_SKIP_CONTACTS_MODULE', '').strip().lower() in ('1', 'true', 'yes'):
        return
    from nodeone.services.contacts_module import is_contacts_globally_allowed

    if not is_contacts_globally_allowed():
        return
    try:
        from nodeone.modules.contacts.admin.routes import contacts_admin_bp
        from nodeone.modules.contacts.api.routes import contacts_api_bp
        from saas_features import register_simple_saas_guard

        if 'contacts_admin' not in app.blueprints:
            register_simple_saas_guard(contacts_admin_bp, 'contacts')
            app.register_blueprint(contacts_admin_bp)
        if 'contacts_api' not in app.blueprints:
            register_simple_saas_guard(contacts_api_bp, 'contacts')
            app.register_blueprint(contacts_api_bp)
    except ImportError as e:
        print(f'Warning: No se pudo registrar módulo contacts: {e}')
    register_legacy_terceros_redirects(app)


def register_legacy_terceros_redirects(app) -> None:
    """Compat: /admin/terceros → maestro central /admin/contacts."""
    if 'contacts_legacy.terceros_redirect' in getattr(app, 'view_functions', {}):
        return
    try:
        from flask import Blueprint, redirect, url_for

        from nodeone.services.contacts_module import is_contacts_globally_allowed

        if not is_contacts_globally_allowed():
            return
    except ImportError:
        return

    legacy_bp = Blueprint('contacts_legacy', __name__)

    @legacy_bp.route('/admin/terceros')
    @legacy_bp.route('/admin/terceros/')
    @legacy_bp.route('/admin/terceros/<path:subpath>')
    def terceros_redirect(subpath=None):
        return redirect(url_for('contacts_admin.contacts_index'), code=302)

    if 'contacts_legacy' not in app.blueprints:
        app.register_blueprint(legacy_bp)
