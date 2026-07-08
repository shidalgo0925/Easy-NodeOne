"""Registro de blueprints EPayroll."""

from __future__ import annotations

import os


def register_epayroll_blueprints(app) -> None:
    if os.environ.get('NODEONE_SKIP_EPAYROLL_MODULE', '').strip().lower() in ('1', 'true', 'yes'):
        return
    try:
        from nodeone.modules.epayroll.routes import epayroll_bp
        from saas_features import register_simple_saas_guard

        if 'epayroll' not in app.blueprints:
            register_simple_saas_guard(epayroll_bp, 'epayroll')
            app.register_blueprint(epayroll_bp)
    except ImportError as e:
        print(f'Warning: No se pudo registrar epayroll_bp: {e}')
