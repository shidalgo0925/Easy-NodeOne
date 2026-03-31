"""Registro de vistas admin AI en app (endpoints legacy)."""


def register_admin_ai_pages_routes(app):
    from flask import render_template

    from app import admin_required, _infra_org_id_for_runtime

    @app.route('/admin/ai')
    @admin_required
    def admin_ai():
        """Configuración IA (plantilla admin/ai_settings.html)."""
        ai_cfg = None
        try:
            import app as M

            ac = getattr(M, 'AIConfig', None)
            if ac is not None and hasattr(ac, 'get_active_config'):
                ai_org = _infra_org_id_for_runtime()
                if ai_org is not None:
                    ai_cfg = ac.get_active_config(organization_id=ai_org)
        except Exception:
            ai_cfg = None
        return render_template('admin/ai_settings.html', ai_config=ai_cfg)

    @app.route('/admin/chatbots')
    @admin_required
    def admin_chatbots():
        """Hub chatbots (plantilla admin/chatbots.html)."""
        ai_cfg = None
        try:
            import app as M

            ac = getattr(M, 'AIConfig', None)
            if ac is not None and hasattr(ac, 'get_active_config'):
                ai_org = _infra_org_id_for_runtime()
                if ai_org is not None:
                    ai_cfg = ac.get_active_config(organization_id=ai_org)
        except Exception:
            ai_cfg = None
        return render_template('admin/chatbots.html', ai_config=ai_cfg)
