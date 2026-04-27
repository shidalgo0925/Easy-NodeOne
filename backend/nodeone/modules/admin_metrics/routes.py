"""KPIs operativos de servicios (admin, JSON)."""

from __future__ import annotations


def register_admin_service_metrics_routes(app):
    if 'admin_metrics_services' in getattr(app, 'view_functions', {}):
        return
    from flask import jsonify
    from sqlalchemy import func

    from app import admin_data_scope_organization_id, admin_required

    @app.route('/admin/metrics/services')
    @admin_required
    def admin_metrics_services():
        oid = int(admin_data_scope_organization_id())
        from models.service_request import ServiceRequest
        from nodeone.core.db import db
        from nodeone.modules.accounting.models import Invoice, InvoiceLine
        from nodeone.modules.sales.models import Quotation

        from models.appointments import Appointment

        out: dict = {
            'organization_id': oid,
            'service_requests_total': 0,
            'service_requests_with_quotation': 0,
            'appointments_total': 0,
            'quotations_total': 0,
            'invoices_total': 0,
            'invoices_paid_or_posted': 0,
            'conversion_request_to_quotation': None,
            'revenue_by_service': [],
        }
        try:
            out['service_requests_total'] = int(
                db.session.query(func.count(ServiceRequest.id)).filter(ServiceRequest.organization_id == oid).scalar() or 0
            )
            out['service_requests_with_quotation'] = int(
                db.session.query(func.count(ServiceRequest.id))
                .filter(
                    ServiceRequest.organization_id == oid,
                    ServiceRequest.quotation_id.isnot(None),
                )
                .scalar()
                or 0
            )
        except Exception:
            pass
        try:
            out['appointments_total'] = int(
                db.session.query(func.count(Appointment.id)).filter(Appointment.organization_id == oid).scalar() or 0
            )
        except Exception:
            pass
        try:
            out['quotations_total'] = int(
                db.session.query(func.count(Quotation.id)).filter(Quotation.organization_id == oid).scalar() or 0
            )
        except Exception:
            pass
        try:
            out['invoices_total'] = int(
                db.session.query(func.count(Invoice.id)).filter(Invoice.organization_id == oid).scalar() or 0
            )
            out['invoices_paid_or_posted'] = int(
                db.session.query(func.count(Invoice.id))
                .filter(Invoice.organization_id == oid, Invoice.status.in_(('paid', 'posted', 'partial')))
                .scalar()
                or 0
            )
        except Exception:
            pass
        n_req = out['service_requests_total'] or 0
        n_q_sr = out['service_requests_with_quotation'] or 0
        if n_req > 0:
            out['conversion_request_to_quotation'] = round(n_q_sr / n_req, 4)
        try:
            from models.catalog import Service

            q = (
                db.session.query(
                    InvoiceLine.product_id,
                    func.coalesce(func.sum(InvoiceLine.total), 0.0).label('rev'),
                )
                .join(Invoice, InvoiceLine.invoice_id == Invoice.id)
                .filter(
                    Invoice.organization_id == oid,
                    Invoice.status.in_(('paid', 'posted', 'partial')),
                    InvoiceLine.product_id.isnot(None),
                )
                .group_by(InvoiceLine.product_id)
            )
            rows = q.all()
            sids = [int(r[0]) for r in rows if r[0]]
            names = {}
            if sids:
                for s in Service.query.filter(Service.id.in_(sids), Service.organization_id == oid).all():
                    names[int(s.id)] = (s.name or '').strip() or f'Servicio #{s.id}'
            out['revenue_by_service'] = [
                {
                    'service_id': int(r[0]),
                    'name': names.get(int(r[0]), f'Producto #{int(r[0])}'),
                    'revenue': float(r[1] or 0.0),
                }
                for r in rows
            ]
        except Exception:
            out['revenue_by_service'] = []
        return jsonify(out)
