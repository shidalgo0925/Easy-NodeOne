"""Registro de blueprints del módulo efactura."""

from __future__ import annotations

import os


def register_efactura_blueprints(app) -> None:
    if os.environ.get('NODEONE_SKIP_EFACTURA_MODULE', '').strip().lower() in ('1', 'true', 'yes'):
        return
    from nodeone.services.efactura_module import is_efactura_globally_allowed

    if not is_efactura_globally_allowed():
        return
    try:
        from nodeone.modules.efactura.admin.routes import efactura_admin_bp
        from nodeone.modules.efactura.api.routes import efactura_api_bp
        from saas_features import register_simple_saas_guard

        if 'efactura_admin' not in app.blueprints:
            register_simple_saas_guard(efactura_admin_bp, 'efactura')
            app.register_blueprint(efactura_admin_bp)
        if 'efactura_api' not in app.blueprints:
            register_simple_saas_guard(efactura_api_bp, 'efactura')
            app.register_blueprint(efactura_api_bp)
    except ImportError as e:
        print(f'Warning: No se pudo registrar módulo efactura: {e}')
