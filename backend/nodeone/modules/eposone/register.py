"""Registro de blueprints EPosOne."""

from __future__ import annotations

import os


def register_eposone_blueprints(app) -> None:
    if os.environ.get('NODEONE_SKIP_EPOSONE_MODULE', '').strip().lower() in ('1', 'true', 'yes'):
        return
    try:
        from nodeone.modules.eposone.routes import eposone_bp
        from nodeone.modules.eposone.api_routes import eposone_api_bp
        from nodeone.modules.eposone.devices_v1_routes import eposone_devices_v1_bp
        from saas_features import register_simple_saas_guard

        if 'eposone' not in app.blueprints:
            register_simple_saas_guard(eposone_bp, 'eposone')
            app.register_blueprint(eposone_bp)
        if 'eposone_api' not in app.blueprints:
            register_simple_saas_guard(eposone_api_bp, 'eposone')
            app.register_blueprint(eposone_api_bp)
        # Hito EN1-01: auth por provisioning code / Bearer dispositivo (sin sesión admin)
        if 'eposone_devices_v1' not in app.blueprints:
            app.register_blueprint(eposone_devices_v1_bp)
        from nodeone.modules.eposone.onboarding_v1_routes import eposone_onboarding_v1_bp

        if 'eposone_onboarding_v1' not in app.blueprints:
            app.register_blueprint(eposone_onboarding_v1_bp)
        # Hito 3: Order Domain APIs (Device Bearer / BO session)
        from nodeone.modules.eposone.orders_v1_routes import eposone_orders_v1_bp

        if 'eposone_orders_v1' not in app.blueprints:
            app.register_blueprint(eposone_orders_v1_bp)
        # Hito cash-shift HTTP: Device Bearer open/close
        from nodeone.modules.eposone.cash_shifts_v1_routes import eposone_cash_v1_bp

        if 'eposone_cash_v1' not in app.blueprints:
            app.register_blueprint(eposone_cash_v1_bp)
        from nodeone.modules.eposone.public_routes import eposone_public_bp

        if 'eposone_public' not in app.blueprints:
            app.register_blueprint(eposone_public_bp)
    except ImportError as e:
        print(f'Warning: No se pudo registrar eposone_bp: {e}')
