"""Rutas HTML y API del módulo Analytics / Dashboards."""

from __future__ import annotations

import os


def register_admin_analytics_routes(app):
    """Registra /admin/analytics* y /api/admin/analytics/* (idempotente)."""
    if 'admin_analytics' in getattr(app, 'view_functions', {}):
        return
    if os.environ.get('NODEONE_SKIP_ANALYTICS_MODULE', '').strip().lower() in ('1', 'true', 'yes'):
        return

    from functools import wraps

    from flask import jsonify, render_template, request

    from app import admin_data_scope_organization_id, admin_required
    from saas_features import enforce_saas_module_or_response

    from nodeone.modules.analytics import service as analytics_svc

    def require_saas_analytics_module(f):
        """Módulo SaaS `analytics` encendido para el tenant (además del permiso RBAC)."""

        @wraps(f)
        def wrapped(*args, **kwargs):
            resp = enforce_saas_module_or_response('analytics')
            if resp is not None:
                return resp
            return f(*args, **kwargs)

        return wrapped

    @app.route('/admin/analytics')
    @admin_required
    @require_saas_analytics_module
    def admin_analytics():
        oid = admin_data_scope_organization_id()
        start, end = analytics_svc.resolve_date_range(
            request.args.get('start_date'),
            request.args.get('end_date'),
        )
        snapshot = analytics_svc.build_executive_snapshot(oid, start, end)
        return render_template(
            'admin/analytics_dashboard.html',
            board='executive',
            start_date=start.strftime('%Y-%m-%d'),
            end_date=end.date().strftime('%Y-%m-%d'),
            snapshot=snapshot,
            metrics=snapshot.get('legacy_metrics') or {},
        )

    @app.route('/admin/analytics/sales')
    @admin_required
    @require_saas_analytics_module
    def admin_analytics_sales():
        oid = admin_data_scope_organization_id()
        start, end = analytics_svc.resolve_date_range(
            request.args.get('start_date'),
            request.args.get('end_date'),
        )
        data = analytics_svc.build_sales_board(oid, start, end)
        return render_template(
            'admin/analytics_dashboard.html',
            board='sales',
            start_date=start.strftime('%Y-%m-%d'),
            end_date=end.date().strftime('%Y-%m-%d'),
            snapshot=data.get('snapshot') or {},
            sales_extra=data,
            metrics=(data.get('snapshot') or {}).get('legacy_metrics') or {},
        )

    @app.route('/admin/analytics/crm')
    @admin_required
    @require_saas_analytics_module
    def admin_analytics_crm():
        oid = admin_data_scope_organization_id()
        start, end = analytics_svc.resolve_date_range(
            request.args.get('start_date'),
            request.args.get('end_date'),
        )
        crm = analytics_svc.build_crm_board(oid, start, end)
        snapshot = analytics_svc.build_executive_snapshot(oid, start, end)
        return render_template(
            'admin/analytics_dashboard.html',
            board='crm',
            start_date=start.strftime('%Y-%m-%d'),
            end_date=end.date().strftime('%Y-%m-%d'),
            snapshot=snapshot,
            crm_board=crm,
            metrics=snapshot.get('legacy_metrics') or {},
        )

    @app.route('/admin/analytics/members')
    @admin_required
    @require_saas_analytics_module
    def admin_analytics_members():
        oid = admin_data_scope_organization_id()
        start, end = analytics_svc.resolve_date_range(
            request.args.get('start_date'),
            request.args.get('end_date'),
        )
        snapshot = analytics_svc.build_executive_snapshot(oid, start, end)
        return render_template(
            'admin/analytics_dashboard.html',
            board='members',
            start_date=start.strftime('%Y-%m-%d'),
            end_date=end.date().strftime('%Y-%m-%d'),
            snapshot=snapshot,
            metrics=snapshot.get('legacy_metrics') or {},
        )

    @app.route('/admin/analytics/registrations')
    @admin_required
    @require_saas_analytics_module
    def admin_analytics_registrations():
        oid = admin_data_scope_organization_id()
        start, end = analytics_svc.resolve_date_range(
            request.args.get('start_date'),
            request.args.get('end_date'),
        )
        snapshot = analytics_svc.build_executive_snapshot(oid, start, end)
        return render_template(
            'admin/analytics_dashboard.html',
            board='registrations',
            start_date=start.strftime('%Y-%m-%d'),
            end_date=end.date().strftime('%Y-%m-%d'),
            snapshot=snapshot,
            metrics=snapshot.get('legacy_metrics') or {},
        )

    @app.route('/api/admin/analytics/realtime')
    @admin_required
    @require_saas_analytics_module
    def api_admin_analytics_realtime():
        oid = admin_data_scope_organization_id()
        return jsonify(analytics_svc.build_realtime_24h(oid))

    @app.route('/api/admin/analytics/summary')
    @admin_required
    @require_saas_analytics_module
    def api_admin_analytics_summary():
        oid = admin_data_scope_organization_id()
        start, end = analytics_svc.resolve_date_range(
            request.args.get('start_date'),
            request.args.get('end_date'),
        )
        snap = analytics_svc.build_executive_snapshot(oid, start, end)
        return jsonify(snap)
