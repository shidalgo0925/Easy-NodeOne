"""Registro de blueprints EPosOne."""

from __future__ import annotations

import os


def register_eposone_blueprints(app) -> None:
    if os.environ.get('NODEONE_SKIP_EPOSONE_MODULE', '').strip().lower() in ('1', 'true', 'yes'):
        return
    try:
        from nodeone.modules.eposone.routes import eposone_bp
        from nodeone.modules.eposone.api_routes import eposone_api_bp
        from saas_features import register_simple_saas_guard

        if 'eposone' not in app.blueprints:
            register_simple_saas_guard(eposone_bp, 'eposone')
            app.register_blueprint(eposone_bp)
        if 'eposone_api' not in app.blueprints:
            register_simple_saas_guard(eposone_api_bp, 'eposone')
            app.register_blueprint(eposone_api_bp)
    except ImportError as e:
        print(f'Warning: No se pudo registrar eposone_bp: {e}')
