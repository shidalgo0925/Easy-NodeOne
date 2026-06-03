"""Vistas admin para Cotizaciones y Facturación."""

from __future__ import annotations


def register_admin_tax_configuration_routes(app):
    """
    Pantalla y redirect de impuestos: siempre registrado (independiente del skip de cotizaciones).
    Idempotente.
    """
    if 'admin_configuration_taxes' in getattr(app, 'view_functions', {}):
        return
    from flask import redirect, render_template, url_for

    from app import admin_required

    @app.route('/admin/configuration/taxes')
    @admin_required
    def admin_configuration_taxes():
        """CRUD de impuestos: configuración por organización."""
        return render_template('admin/config_taxes.html')

    @app.route('/admin/sales/taxes')
    @admin_required
    def admin_sales_taxes():
        """Compatibilidad: URL antigua."""
        return redirect(url_for('admin_configuration_taxes'), code=302)


def register_admin_sales_catalog_route(app):
    """Hub Catálogo comercial (Ventas): enlaces a rutas existentes según módulos SaaS."""
    if 'admin_sales_catalog' in getattr(app, 'view_functions', {}):
        return
    from flask import flash, redirect, render_template, url_for

    from app import admin_required
    from nodeone.core.nav_menu import _v_catalog_hub, build_nav_context
    from nodeone.services.academic_module import is_academic_module_enabled_for_org
    from nodeone.services.office365_module import is_office365_module_enabled_for_org

    @app.route('/admin/sales/catalog')
    @admin_required
    def admin_sales_catalog():
        from app import (
            _nav_can_permission,
            _org_id_for_module_visibility,
            has_view_endpoint,
            saas_module_enabled,
            saas_module_enabled_chain,
        )

        ctx = build_nav_context(
            nav_can=_nav_can_permission,
            saas_module_enabled=saas_module_enabled,
            saas_module_enabled_chain=saas_module_enabled_chain,
            has_view_endpoint=has_view_endpoint,
            show_academic_admin_nav=(
                'academic_admin' in app.blueprints
                and is_academic_module_enabled_for_org(_org_id_for_module_visibility())
            ),
            office365_module_enabled=is_office365_module_enabled_for_org(
                _org_id_for_module_visibility()
            ),
            show_platform_admin_nav=False,
            is_platform_admin=False,
            is_advisor=False,
            show_tenant_admin_menu=True,
        )
        if not _v_catalog_hub(ctx):
            flash('No hay secciones de catálogo habilitadas para esta organización.', 'error')
            return redirect(url_for('dashboard'))
        return render_template('admin/sales_catalog.html')


def register_admin_sales_quotations_invoices_routes(app):
    """Cotizaciones e facturas (respeta NODEONE_SKIP en features). Idempotente."""
    if 'admin_sales_quotations' in getattr(app, 'view_functions', {}):
        return
    from flask import flash, redirect, render_template, url_for

    from app import admin_data_scope_organization_id, admin_required, has_saas_module_enabled

    @app.route('/admin/sales/quotations')
    @admin_required
    def admin_sales_quotations():
        oid = admin_data_scope_organization_id()
        if not has_saas_module_enabled(oid, 'sales'):
            flash('El módulo Ventas no está habilitado para esta organización.', 'error')
            return redirect(url_for('dashboard'))
        return render_template('admin/sales_quotations.html')

    @app.route('/admin/sales/quotations/<int:quotation_id>')
    @admin_required
    def admin_sales_quotation_form(quotation_id):
        oid = admin_data_scope_organization_id()
        if not has_saas_module_enabled(oid, 'sales'):
            flash('El módulo Ventas no está habilitado para esta organización.', 'error')
            return redirect(url_for('dashboard'))
        from models.saas import SaasOrganization
        from nodeone.modules.sales.models import Quotation

        qrow = Quotation.query.filter_by(id=quotation_id, organization_id=oid).first()
        quotation_status = qrow.status if qrow else None
        org_row = SaasOrganization.query.get(oid)
        quotation_org_name = (org_row.name or '').strip() if org_row else ''
        return render_template(
            'admin/sales_quotation_form.html',
            quotation_id=quotation_id,
            quotation_status=quotation_status,
            quotation_org_name=quotation_org_name,
        )

    @app.route('/admin/accounting/invoices')
    @admin_required
    def admin_accounting_invoices():
        oid = admin_data_scope_organization_id()
        if not has_saas_module_enabled(oid, 'sales'):
            flash('El módulo Ventas no está habilitado para esta organización.', 'error')
            return redirect(url_for('dashboard'))
        return render_template('admin/accounting_invoices.html')

    @app.route('/admin/accounting/invoices/<int:invoice_id>')
    @admin_required
    def admin_accounting_invoice_form(invoice_id):
        if invoice_id == 0:
            return redirect(url_for('admin_accounting_invoice_new'), code=302)
        oid = admin_data_scope_organization_id()
        if not has_saas_module_enabled(oid, 'sales'):
            flash('El módulo Ventas no está habilitado para esta organización.', 'error')
            return redirect(url_for('dashboard'))
        from models.saas import SaasOrganization
        from nodeone.modules.accounting.models import Invoice

        inv_row = Invoice.query.filter_by(id=invoice_id, organization_id=oid).first()
        invoice_status = inv_row.status if inv_row else None
        org_row = SaasOrganization.query.get(oid)
        invoice_org_name = (org_row.name or '').strip() if org_row else ''
        return render_template(
            'admin/invoice_form.html',
            invoice_id=invoice_id,
            invoice_status=invoice_status,
            invoice_org_name=invoice_org_name,
        )


def register_admin_accounting_invoice_new_route(app):
    """
    GET /admin/accounting/invoices/new — idempotente por endpoint.

    Va aparte de register_admin_sales_quotations_invoices_routes porque ese bloque
    retorna temprano si ya existía admin_sales_quotations; sin esto, despliegues
    parciales no registraban la ruta y url_for('admin_accounting_invoice_new') → 500.
    """
    if 'admin_accounting_invoice_new' in getattr(app, 'view_functions', {}):
        return
    from flask import flash, redirect, render_template, url_for

    from app import admin_data_scope_organization_id, admin_required, has_saas_module_enabled

    @app.route('/admin/accounting/invoices/new')
    @admin_required
    def admin_accounting_invoice_new():
        oid = admin_data_scope_organization_id()
        if not has_saas_module_enabled(oid, 'sales'):
            flash('El módulo Ventas no está habilitado para esta organización.', 'error')
            return redirect(url_for('dashboard'))
        from models.saas import SaasOrganization

        org_row = SaasOrganization.query.get(oid)
        invoice_org_name = (org_row.name or '').strip() if org_row else ''
        return render_template(
            'admin/invoice_form.html',
            invoice_id=0,
            invoice_status='draft',
            invoice_org_name=invoice_org_name,
        )


def register_admin_sales_commercial_contacts_routes(app):
    """URL histórica: redirige a Usuarios (vendedor = flag en miembro). Idempotente."""
    if 'admin_sales_commercial_contacts' in getattr(app, 'view_functions', {}):
        return
    from flask import flash, redirect, url_for

    from app import admin_required

    @app.route('/admin/sales/commercial-contacts', methods=['GET', 'POST'])
    @admin_required
    def admin_sales_commercial_contacts():
        flash(
            'Los vendedores se configuran en Usuarios: abra el miembro y active «Es vendedor».',
            'info',
        )
        return redirect(url_for('admin_users'), code=302)

    @app.route('/admin/sales/commercial-contacts/<int:cid>/edit', methods=['GET', 'POST'])
    @admin_required
    def admin_sales_commercial_contact_edit(cid):
        flash('Los vendedores se configuran en Usuarios.', 'info')
        return redirect(url_for('admin_users'), code=302)
