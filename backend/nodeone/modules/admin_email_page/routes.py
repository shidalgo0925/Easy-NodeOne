"""Registro de vista /admin/email en app (endpoint legacy)."""


def register_admin_email_page_routes(app):
    from flask import render_template

    from app import admin_required, EmailConfig, EmailTemplate

    @app.route('/admin/email')
    @admin_required
    def admin_email():
        """Panel de configuración de email (SMTP y templates)"""
        email_config = EmailConfig.get_active_config()
        templates = EmailTemplate.query.order_by(EmailTemplate.category, EmailTemplate.name).all()

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
