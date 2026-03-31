"""Registro de rutas /admin/contacts sobre la app (endpoints legacy sin prefijo de blueprint)."""


def register_admin_tenant_contacts_routes(app):
    from flask import flash, redirect, render_template, request, url_for
    from flask_login import current_user

    from app import (
        admin_required,
        db,
        get_current_organization_id,
        SaasOrganization,
        scoped_query,
        TenantCrmContact,
    )

    @app.route('/admin/contacts', methods=['GET', 'POST'])
    @admin_required
    def admin_tenant_contacts():
        """CRM contactos por tenant (base.html → Clientes)."""
        is_plat = bool(getattr(current_user, 'is_admin', False))
        orgs = (
            SaasOrganization.query.filter_by(is_active=True).order_by(SaasOrganization.name.asc(), SaasOrganization.id.asc()).all()
            if is_plat
            else []
        )
        filter_oid = request.args.get('organization_id', type=int)
        ctx_oid = int(get_current_organization_id())

        if request.method == 'POST':
            name = (request.form.get('name') or '').strip()
            if not name:
                flash('El nombre es obligatorio.', 'error')
                return redirect(request.url)
            oid = ctx_oid
            if is_plat:
                oid = filter_oid if filter_oid else ctx_oid
            org = SaasOrganization.query.get(oid)
            if org is None or not getattr(org, 'is_active', True):
                flash('Organización no válida.', 'error')
                return redirect(url_for('admin_tenant_contacts'))
            if not is_plat and oid != ctx_oid:
                flash('No autorizado.', 'error')
                return redirect(url_for('admin_tenant_contacts'))
            row = TenantCrmContact(
                organization_id=oid,
                name=name,
                email=(request.form.get('email') or '').strip() or None,
                phone=(request.form.get('phone') or '').strip() or None,
                company=(request.form.get('company') or '').strip() or None,
                notes=(request.form.get('notes') or '').strip() or None,
            )
            db.session.add(row)
            db.session.commit()
            flash('Contacto guardado.', 'success')
            redir = url_for('admin_tenant_contacts', organization_id=oid) if is_plat and oid else url_for('admin_tenant_contacts')
            return redirect(redir)

        if is_plat:
            q = TenantCrmContact.query
            if filter_oid:
                q = q.filter_by(organization_id=filter_oid)
        else:
            q = scoped_query(TenantCrmContact)
        contacts = q.order_by(TenantCrmContact.created_at.desc()).limit(500).all()
        return render_template(
            'admin/contacts.html',
            saas_organizations=orgs,
            contacts=contacts,
            contacts_org_filter=filter_oid,
        )

    @app.route('/admin/contacts/<int:cid>/delete', methods=['POST'])
    @admin_required
    def admin_tenant_contact_delete(cid):
        c = TenantCrmContact.query.get_or_404(cid)
        if not getattr(current_user, 'is_admin', False) and c.organization_id != int(get_current_organization_id()):
            flash('No autorizado.', 'error')
            return redirect(url_for('admin_tenant_contacts'))
        db.session.delete(c)
        db.session.commit()
        flash('Contacto eliminado.', 'success')
        return redirect(url_for('admin_tenant_contacts'))
