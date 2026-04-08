"""Registro de vista /admin/email en app (endpoint legacy)."""


def register_admin_email_page_routes(app):
    from flask import render_template

    from app import admin_data_scope_organization_id, admin_required, EmailConfig, EmailTemplate

    @app.route('/admin/email')
    @admin_required
    def admin_email():
        """Panel de configuración de email (SMTP y templates)"""
        scope_oid = admin_data_scope_organization_id()
        email_config = EmailConfig.get_active_config(
            organization_id=int(scope_oid),
            allow_fallback_to_default_org=False,
        )

        tq = EmailTemplate.query
        if hasattr(EmailTemplate, 'organization_id'):
            tq = tq.filter(EmailTemplate.organization_id == scope_oid)
        templates = tq.order_by(EmailTemplate.category, EmailTemplate.name).all()

        templates_by_category = {}
        for template in templates:
            if template.category not in templates_by_category:
                templates_by_category[template.category] = []
            templates_by_category[template.category].append(template.to_dict())

        return render_template(
            'admin/email.html',
            email_config=email_config.to_dict() if email_config else None,
            templates=templates_by_category,
        )
