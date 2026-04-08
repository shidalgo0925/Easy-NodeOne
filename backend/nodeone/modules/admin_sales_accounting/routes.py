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
        from nodeone.modules.sales.models import Quotation

        qrow = Quotation.query.filter_by(id=quotation_id, organization_id=oid).first()
        quotation_status = qrow.status if qrow else None
        return render_template(
            'admin/sales_quotation_form.html',
            quotation_id=quotation_id,
            quotation_status=quotation_status,
        )

    @app.route('/admin/accounting/invoices')
    @admin_required
    def admin_accounting_invoices():
        oid = admin_data_scope_organization_id()
        if not has_saas_module_enabled(oid, 'sales'):
            flash('El módulo Ventas no está habilitado para esta organización.', 'error')
            return redirect(url_for('dashboard'))
        return render_template('admin/accounting_invoices.html')
