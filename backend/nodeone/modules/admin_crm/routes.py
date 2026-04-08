"""Vistas admin CRM (HTML) usando API /crm/*."""


def register_admin_crm_routes(app):
    from flask import render_template

    from app import admin_required

    @app.route('/admin/crm')
    @admin_required
    def admin_crm_dashboard():
        return render_template('admin/crm_dashboard.html', crm_view='dashboard')

    @app.route('/admin/crm/kanban')
    @admin_required
    def admin_crm_kanban():
        return render_template('admin/crm_dashboard.html', crm_view='kanban')

    @app.route('/admin/crm/leads')
    @admin_required
    def admin_crm_leads():
        return render_template('admin/crm_dashboard.html', crm_view='list')

    @app.route('/admin/crm/reports')
    @admin_required
    def admin_crm_reports():
        return render_template('admin/crm_dashboard.html', crm_view='reports')
