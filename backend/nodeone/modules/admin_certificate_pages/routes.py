"""Registro de vistas /admin/certificate-* sobre la app (endpoints legacy)."""


def _admin_certificate_return_url():
    """Path interno seguro para volver al flujo Eventos (query ?return=)."""
    from flask import request

    from _app.modules.auth.service import safe_next_path

    return safe_next_path(request.args.get('return'))


def register_admin_certificate_pages_routes(app):
    from flask import render_template

    from app import admin_required, MembershipPlan

    @app.route('/admin/certificate-events')
    @admin_required
    def admin_certificate_events():
        """CRUD de formatos de certificado. Query ?edit=<id> abre el editor; ?return= vuelve al evento."""
        plans = MembershipPlan.get_active_ordered()
        return render_template(
            'admin/certificate_events.html',
            plans=plans or [],
            return_url=_admin_certificate_return_url(),
        )

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
        return render_template(
            'admin/certificate_template_editor.html',
            template_id=template_id,
            return_url=_admin_certificate_return_url(),
        )

    @app.route('/admin/certificate-templates/institutional-editor/<int:template_id>')
    @admin_required
    def admin_certificate_institutional_editor(template_id):
        """Editor de plantilla institucional PDF para certificados de evento."""
        from app import CertificateTemplate, Event

        from nodeone.services.event_institutional_certificate_template import (
            is_institutional_template,
            parse_institutional_meta,
        )

        t = CertificateTemplate.query.get_or_404(template_id)
        if not is_institutional_template(t):
            from flask import abort

            abort(404)
        meta = parse_institutional_meta(t.json_layout) or {}
        event_id = int(meta.get('event_id') or 0)
        event = Event.query.get(event_id) if event_id else None
        event_title = (getattr(event, 'title', None) or t.name or 'Evento').strip()
        return render_template(
            'admin/certificate_institutional_editor.html',
            template_id=template_id,
            event_id=event_id,
            event_title=event_title,
        )
