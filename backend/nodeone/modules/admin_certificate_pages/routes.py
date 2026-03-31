"""Registro de vistas /admin/certificate-* sobre la app (endpoints legacy)."""


def register_admin_certificate_pages_routes(app):
    from flask import render_template

    from app import admin_required, MembershipPlan

    @app.route('/admin/certificate-events')
    @admin_required
    def admin_certificate_events():
        """CRUD de eventos de certificado (fondos, logos, datos)."""
        plans = MembershipPlan.get_active_ordered()
        return render_template('admin/certificate_events.html', plans=plans or [])

    @app.route('/admin/certificate-templates')
    @admin_required
    def admin_certificate_templates():
        """Lista de plantillas visuales de certificado (tipo Canva)."""
        return render_template('admin/certificate_templates.html')

    @app.route('/admin/certificate-templates/editor')
    @app.route('/admin/certificate-templates/editor/<int:template_id>')
    @admin_required
    def admin_certificate_template_editor(template_id=None):
        """Editor drag & drop (Fabric.js) para crear/editar plantilla de certificado."""
        return render_template('admin/certificate_template_editor.html', template_id=template_id)
