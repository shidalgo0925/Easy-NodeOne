"""URLs legacy: redirigen a Clientes (/admin/contacts). No es una figura de negocio."""

from __future__ import annotations

from flask import Blueprint, flash, redirect, url_for

from nodeone.core.platform.ets_provider import ets_provider_organization_id

admin_commercial_customers_bp = Blueprint('admin_commercial_customers', __name__)


def _platform_admin(f):
    from app import platform_admin_required

    return platform_admin_required(f)


@admin_commercial_customers_bp.route('/admin/commercial/customers')
@_platform_admin
def index():
    return redirect(url_for('contacts_admin.contacts_index', role='customer'))


@admin_commercial_customers_bp.route('/admin/commercial/customers/<int:customer_id>')
@_platform_admin
def detail(customer_id: int):
    from models.ets_commercial_customer import EtsCommercialCustomer

    oid = ets_provider_organization_id()
    row = EtsCommercialCustomer.query.filter_by(
        id=int(customer_id), organization_id=int(oid)
    ).first()
    if row is None or not row.contact_id:
        flash('Cliente no encontrado.', 'error')
        return redirect(url_for('contacts_admin.contacts_index'))
    return redirect(url_for('contacts_admin.contacts_detail', contact_id=int(row.contact_id)))
