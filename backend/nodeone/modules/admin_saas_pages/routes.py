"""Registro de vistas admin SaaS en app (endpoints legacy)."""


def register_admin_saas_pages_routes(app):
    from flask import flash, redirect, render_template, request, url_for

    from app import (
        default_organization_id,
        platform_admin_required,
        SaasModule,
        SaasOrganization,
        single_tenant_default_only,
    )

    @app.route('/admin/saas-modules')
    @platform_admin_required
    def admin_saas_modules_page():
        from utils.organization import platform_visible_organization_ids

        orgs = SaasOrganization.query.order_by(SaasOrganization.id).all()
        allow = platform_visible_organization_ids()
        if allow is not None:
            orgs = [o for o in orgs if int(o.id) in allow]
        sel = request.args.get('organization_id', type=int)
        if sel is None and orgs:
            if single_tenant_default_only():
                def_id = default_organization_id()
                sel = def_id if any(int(o.id) == int(def_id) for o in orgs) else orgs[0].id
            else:
                sel = orgs[0].id
        if orgs and sel is not None and not any(int(o.id) == int(sel) for o in orgs):
            sel = int(orgs[0].id)
        show_rail = request.args.get('guide') == '1'
        return render_template(
            'admin/saas_modules.html',
            saas_organizations=orgs,
            selected_organization_id=sel,
            show_onboarding_rail=show_rail,
        )

    @app.route('/admin/saas-catalog')
    @platform_admin_required
    def admin_saas_catalog_list():
        mods = SaasModule.query.order_by(SaasModule.code).all()
        return render_template('admin/saas_catalog_list.html', modules=mods)

    @app.route('/admin/saas-catalog/new')
    @platform_admin_required
    def admin_saas_catalog_new():
        flash('Alta de módulo en catálogo: contactá soporte o usá migración/seed.', 'info')
        return redirect(url_for('admin_saas_catalog_list'))

    @app.route('/admin/saas-catalog/<int:mid>/edit')
    @platform_admin_required
    def admin_saas_catalog_edit(mid):
        SaasModule.query.get_or_404(mid)
        flash('Edición de módulo en catálogo no está habilitada en esta build.', 'info')
        return redirect(url_for('admin_saas_catalog_list'))

    @app.route('/admin/saas-catalog/<int:mid>/delete', methods=['POST'])
    @platform_admin_required
    def admin_saas_catalog_delete(mid):
        flash('Eliminación desde UI no está habilitada.', 'warning')
        return redirect(url_for('admin_saas_catalog_list'))
