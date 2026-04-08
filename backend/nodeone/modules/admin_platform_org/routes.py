"""Registro de rutas admin platform/org en app (endpoints legacy)."""

import os
import re


def register_admin_platform_org_routes(app):
    from flask import abort, current_app, flash, redirect, render_template, request, send_from_directory, url_for
    from app import (
        admin_required,
        db,
        platform_admin_required,
        SaasModule,
        SaasOrganization,
        SaasOrgModule,
        User,
    )

    guide_product_img_dir = os.path.normpath(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..', 'static', 'images', 'products')
    )

    def _product_guide_product_lines():
        return [
            {'id': 'line-services', 'expanded': True, 'image': 'help-services-catalog.png', 'name': 'Catalogo y servicios', 'title_question': 'Que cubre?', 'intro': 'Oferta de servicios o productos con precios, turnos y pagos integrados al mismo portal.', 'bullets': [], 'footer_title': '', 'footer': '', 'rich': False},
            {'id': 'line-confirm', 'expanded': False, 'image': 'product-confirma.png', 'name': 'Confirmacion y seguimiento', 'title_question': 'Que cubre?', 'intro': 'Flujos de confirmacion y comunicacion con el cliente tras la reserva o la compra.', 'bullets': [], 'footer_title': '', 'footer': '', 'rich': False},
            {'id': 'line-go', 'expanded': False, 'image': 'product-go.png', 'name': 'Operacion y crecimiento', 'title_question': 'Que cubre?', 'intro': 'Herramientas para operar el dia a dia y escalar (modulos, automatizacion, canales).', 'bullets': [], 'footer_title': '', 'footer': '', 'rich': False},
        ]

    def _product_guide_saas_items():
        items = []
        try:
            for i, m in enumerate(SaasModule.query.order_by(SaasModule.is_core.desc(), SaasModule.name).limit(40).all()):
                items.append(
                    {
                        'id': f'mod-{m.id}',
                        'expanded': i == 0,
                        'image': f'mod-{m.code}.png',
                        'name': m.name,
                        'title_question': 'Para que sirve?',
                        'intro': (m.description or 'Modulo del catalogo SaaS.').strip(),
                        'bullets': [],
                        'footer_title': 'Codigo',
                        'footer': m.code,
                        'rich': False,
                    }
                )
        except Exception:
            pass
        return items

    def _platform_setup_wizard_state():
        orgs = SaasOrganization.query.order_by(SaasOrganization.id).all()
        first = orgs[0] if orgs else None
        tid = first.id if first else None
        step_tenant = len(orgs) >= 1
        step_subdomain_strict = bool(first and (first.subdomain or '').strip())
        step_modules = False
        step_users = False
        if tid:
            step_modules = SaasOrgModule.query.filter_by(organization_id=tid, enabled=True).count() > 0
            step_users = User.query.filter_by(organization_id=tid).count() >= 1
        step_review = bool(step_tenant and step_subdomain_strict and step_modules and step_users)
        if not step_tenant:
            current_step = 1
        elif not step_subdomain_strict:
            current_step = 2
        elif not step_modules:
            current_step = 3
        elif not step_users:
            current_step = 4
        elif not step_review:
            current_step = 5
        else:
            current_step = 6
        done = sum([step_tenant, step_subdomain_strict, step_modules, step_users, step_review])
        percent = min(100, int(100 * done / 5)) if done else 0
        return {
            'current_step': current_step,
            'percent': percent,
            'step_tenant': step_tenant,
            'step_subdomain_strict': step_subdomain_strict,
            'step_modules': step_modules,
            'step_users': step_users,
            'step_review': step_review,
            'first_tenant_id': tid,
            'first_tenant_name': first.name if first else None,
        }

    def _tenant_public_base():
        return (os.environ.get('TENANT_PUBLIC_BASE') or os.environ.get('EASYNODEONE_PUBLIC_DOMAIN') or 'easynodeone.com').strip()

    def _normalize_org_subdomain(raw):
        if raw is None:
            return None
        s = (raw or '').strip().lower()
        if not s:
            return None
        if len(s) > 128:
            return False
        if not (re.match(r'^[a-z0-9]$', s) or re.match(r'^[a-z0-9][a-z0-9-]{1,126}[a-z0-9]$', s)):
            return False
        return s

    @app.route('/admin/guide-img/<filename>')
    @admin_required
    def admin_guide_product_image(filename):
        if not filename or not re.match(r'^[a-zA-Z0-9._-]+$', filename):
            abort(404)
        try:
            return send_from_directory(guide_product_img_dir, filename)
        except FileNotFoundError:
            abort(404)

    @app.route('/admin/product-guide')
    @admin_required
    def admin_product_guide():
        return render_template('admin/product_guide.html', product_lines=_product_guide_product_lines(), saas_products=_product_guide_saas_items())

    @app.route('/admin/platform-setup')
    @admin_required
    def admin_platform_setup():
        preview = [{'name': m.name, 'is_core': bool(m.is_core)} for m in SaasModule.query.order_by(SaasModule.is_core.desc(), SaasModule.name).limit(12).all()]
        return render_template('admin/platform_setup.html', w=_platform_setup_wizard_state(), saas_modules_preview=preview)

    @app.route('/admin/organizations')
    @platform_admin_required
    def admin_organizations_list():
        from utils.organization import platform_visible_organization_ids

        orgs = SaasOrganization.query.order_by(SaasOrganization.id).all()
        allow = platform_visible_organization_ids()
        if allow is not None:
            orgs = [o for o in orgs if int(o.id) in allow]
        return render_template('admin/organizations_list.html', organizations=orgs, tenant_public_base=_tenant_public_base())

    @app.route('/admin/organizations/new', methods=['GET', 'POST'])
    @platform_admin_required
    def admin_organization_new():
        show_rail = request.args.get('guide') == '1'
        if request.method == 'POST':
            name = (request.form.get('name') or '').strip()
            sub_raw = _normalize_org_subdomain(request.form.get('subdomain'))
            is_active = request.form.get('is_active') == '1'
            if not name:
                flash('El nombre es obligatorio.', 'error')
                return render_template('admin/organization_form.html', org=None, form=request.form, show_onboarding_rail=show_rail)
            if sub_raw is False:
                flash('Subdominio invalido: solo minusculas, numeros y guiones; no empezar ni terminar con guion.', 'error')
                return render_template('admin/organization_form.html', org=None, form=request.form, show_onboarding_rail=show_rail)
            if sub_raw and SaasOrganization.query.filter_by(subdomain=sub_raw).first():
                flash('Ese subdominio ya esta en uso.', 'error')
                return render_template('admin/organization_form.html', org=None, form=request.form, show_onboarding_rail=show_rail)
            o = SaasOrganization(name=name, subdomain=sub_raw, is_active=is_active)
            db.session.add(o)
            try:
                db.session.commit()
                try:
                    from nodeone.services.saas_catalog_defaults import (
                        ensure_sales_org_module_links,
                        ensure_toggleable_tenant_module_links,
                    )

                    ensure_sales_org_module_links()
                    ensure_toggleable_tenant_module_links(organization_id=o.id)
                except Exception as seed_ex:
                    current_app.logger.warning('saas seed post-org-create: %s', seed_ex)
                flash('Empresa creada.', 'success')
                return redirect(url_for('admin_organizations_list'))
            except Exception as ex:
                db.session.rollback()
                flash('No se pudo guardar: %s' % (ex,), 'error')
                return render_template('admin/organization_form.html', org=None, form=request.form, show_onboarding_rail=show_rail)
        return render_template('admin/organization_form.html', org=None, form=None, show_onboarding_rail=show_rail)

    @app.route('/admin/organizations/<int:oid>/edit', methods=['GET', 'POST'])
    @platform_admin_required
    def admin_organization_edit(oid):
        o = SaasOrganization.query.get_or_404(oid)
        show_rail = request.args.get('guide') == '1'
        if request.method == 'POST':
            name = (request.form.get('name') or '').strip()
            sub_raw = _normalize_org_subdomain(request.form.get('subdomain'))
            is_active = True if oid == 1 else request.form.get('is_active') == '1'
            if not name:
                flash('El nombre es obligatorio.', 'error')
                return render_template('admin/organization_form.html', org=o, form=request.form, show_onboarding_rail=show_rail)
            if sub_raw is False:
                flash('Subdominio invalido: solo minusculas, numeros y guiones; no empezar ni terminar con guion.', 'error')
                return render_template('admin/organization_form.html', org=o, form=request.form, show_onboarding_rail=show_rail)
            if sub_raw:
                other = SaasOrganization.query.filter(SaasOrganization.subdomain == sub_raw, SaasOrganization.id != oid).first()
                if other:
                    flash('Ese subdominio ya esta en uso.', 'error')
                    return render_template('admin/organization_form.html', org=o, form=request.form, show_onboarding_rail=show_rail)
            o.name = name
            o.subdomain = sub_raw
            o.is_active = is_active
            try:
                db.session.commit()
                flash('Empresa actualizada.', 'success')
                return redirect(url_for('admin_organizations_list'))
            except Exception as ex:
                db.session.rollback()
                flash('No se pudo guardar: %s' % (ex,), 'error')
                return render_template('admin/organization_form.html', org=o, form=request.form, show_onboarding_rail=show_rail)
        return render_template('admin/organization_form.html', org=o, form=None, show_onboarding_rail=show_rail)

    @app.route('/admin/organizations/<int:oid>/deactivate', methods=['POST'])
    @platform_admin_required
    def admin_organization_deactivate(oid):
        if oid == 1:
            flash('La organizacion por defecto (id 1) no se desactiva.', 'error')
            return redirect(url_for('admin_organizations_list'))
        o = SaasOrganization.query.get_or_404(oid)
        o.is_active = False
        db.session.commit()
        flash('Empresa desactivada.', 'success')
        return redirect(url_for('admin_organizations_list'))

    @app.route('/admin/organizations/<int:oid>/activate', methods=['POST'])
    @platform_admin_required
    def admin_organization_activate(oid):
        o = SaasOrganization.query.get_or_404(oid)
        o.is_active = True
        db.session.commit()
        flash('Empresa activada.', 'success')
        return redirect(url_for('admin_organizations_list'))

    @app.route('/admin/organizations/<int:oid>/delete', methods=['POST'])
    @platform_admin_required
    def admin_organization_delete(oid):
        flash('Eliminacion de tenant desde UI no esta habilitada en esta build.', 'warning')
        return redirect(url_for('admin_organizations_list'))
