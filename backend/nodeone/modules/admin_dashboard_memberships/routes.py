"""Registro de rutas admin dashboard/memberships en app (endpoints legacy)."""


def register_admin_dashboard_memberships_routes(app):
    from datetime import datetime

    from flask import flash, redirect, render_template, request, url_for

    from app import (
        admin_data_scope_organization_id,
        admin_required,
        db,
        Membership,
        Payment,
        require_permission,
        Subscription,
        User,
    )

    @app.route('/admin')
    @app.route('/admin/')
    @admin_required
    def admin_dashboard():
        """Panel de administración principal"""
        try:
            scope_oid = admin_data_scope_organization_id()
            try:
                pending_payments_count = (
                    db.session.query(Payment)
                    .join(User, Payment.user_id == User.id)
                    .filter(User.organization_id == scope_oid, Payment.ocr_status.in_(['pending', 'needs_review']), Payment.status == 'pending')
                    .count()
                )
            except AttributeError:
                pending_payments_count = (
                    db.session.query(Payment).join(User, Payment.user_id == User.id).filter(User.organization_id == scope_oid, Payment.status == 'pending').count()
                )

            total_users = User.query.filter_by(organization_id=scope_oid).count()

            try:
                total_memberships = db.session.query(Membership).join(User, Membership.user_id == User.id).filter(User.organization_id == scope_oid).count()
                active_memberships = (
                    db.session.query(Membership).join(User, Membership.user_id == User.id).filter(User.organization_id == scope_oid, Membership.is_active.is_(True)).count()
                )
                recent_memberships = (
                    db.session.query(Membership).join(User, Membership.user_id == User.id).filter(User.organization_id == scope_oid).order_by(Membership.created_at.desc()).limit(5).all()
                )
            except (AttributeError, Exception):
                total_memberships = (
                    db.session.query(Subscription).join(User, Subscription.user_id == User.id).filter(User.organization_id == scope_oid, Subscription.status == 'active').count()
                )
                active_memberships = total_memberships
                recent_memberships = (
                    db.session.query(Subscription).join(User, Subscription.user_id == User.id).filter(User.organization_id == scope_oid).order_by(Subscription.created_at.desc()).limit(5).all()
                )

            total_payments = db.session.query(Payment).join(User, Payment.user_id == User.id).filter(User.organization_id == scope_oid, Payment.status == 'succeeded').count()
            try:
                succeeded_payments = db.session.query(Payment).join(User, Payment.user_id == User.id).filter(User.organization_id == scope_oid, Payment.status == 'succeeded').all()
                total_revenue = sum([p.amount for p in succeeded_payments]) / 100.0
            except Exception:
                total_revenue = 0.0

            recent_users = User.query.filter_by(organization_id=scope_oid).order_by(User.created_at.desc()).limit(5).all()
            return render_template(
                'admin/dashboard.html',
                total_users=total_users,
                total_memberships=total_memberships,
                active_memberships=active_memberships,
                total_payments=total_payments,
                total_revenue=total_revenue,
                recent_users=recent_users,
                recent_memberships=recent_memberships,
                pending_payments_count=pending_payments_count,
            )
        except Exception as e:
            flash(f'Error al cargar el panel de administración: {str(e)}', 'error')
            return redirect(url_for('dashboard'))

    @app.route('/admin/memberships')
    @require_permission('memberships.view')
    def admin_memberships():
        """Gestión de membresías (incluye Membership y Subscription) con filtros y paginación"""
        old_memberships = Membership.query.order_by(Membership.created_at.desc()).all()
        subscriptions = Subscription.query.order_by(Subscription.created_at.desc()).all()
        all_memberships = []
        for sub in subscriptions:
            all_memberships.append(
                {
                    'id': sub.id,
                    'user': sub.user,
                    'membership_type': sub.membership_type,
                    'start_date': sub.start_date,
                    'end_date': sub.end_date,
                    'amount': sub.payment.amount / 100.0 if sub.payment else 0.0,
                    'is_active': sub.is_currently_active(),
                    'payment_status': 'paid' if sub.payment and sub.payment.status == 'succeeded' else 'pending',
                    'payment_id': sub.payment_id,
                    'is_subscription': True,
                    'created_at': sub.created_at,
                }
            )
        for mem in old_memberships:
            all_memberships.append(
                {
                    'id': mem.id,
                    'user': mem.user,
                    'membership_type': mem.membership_type,
                    'start_date': mem.start_date,
                    'end_date': mem.end_date,
                    'amount': mem.amount if hasattr(mem, 'amount') else 0.0,
                    'is_active': mem.is_active if hasattr(mem, 'is_active') else False,
                    'payment_status': mem.payment_status if hasattr(mem, 'payment_status') else 'unknown',
                    'payment_id': None,
                    'is_subscription': False,
                    'created_at': mem.created_at if hasattr(mem, 'created_at') else datetime.utcnow(),
                }
            )
        all_memberships.sort(key=lambda x: x['created_at'], reverse=True)
        membership_types = sorted(set(m.get('membership_type') or '' for m in all_memberships if m.get('membership_type')))
        search = request.args.get('search', '').strip().lower()
        type_filter = request.args.get('type', 'all')
        status_filter = request.args.get('status', 'all')
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 10, type=int), 100)

        if search:
            all_memberships = [m for m in all_memberships if m['user'] and ((m['user'].first_name or '').lower().find(search) >= 0 or (m['user'].last_name or '').lower().find(search) >= 0 or (m['user'].email or '').lower().find(search) >= 0)]
        if type_filter != 'all':
            all_memberships = [m for m in all_memberships if (m.get('membership_type') or '').lower() == type_filter.lower()]
        if status_filter == 'active':
            all_memberships = [m for m in all_memberships if m.get('is_active')]
        elif status_filter == 'inactive':
            all_memberships = [m for m in all_memberships if not m.get('is_active')]

        total = len(all_memberships)
        pages = max(1, (total + per_page - 1) // per_page) if per_page else 1
        page = min(max(1, page), pages)
        start = (page - 1) * per_page
        memberships = all_memberships[start : start + per_page]

        def _iter_pages(left_edge=1, right_edge=1, left_current=2, right_current=2):
            for p in range(1, pages + 1):
                yield p

        pagination = type(
            'Pagination',
            (),
            {
                'page': page,
                'per_page': per_page,
                'total': total,
                'pages': pages,
                'has_prev': page > 1,
                'has_next': page < pages,
                'prev_num': page - 1,
                'next_num': page + 1,
                'iter_pages': lambda le=1, re=1, lc=2, rc=2: _iter_pages(le, re, lc, rc),
            },
        )()

        return render_template(
            'admin/memberships.html',
            memberships=memberships,
            subscriptions=subscriptions,
            old_memberships=old_memberships,
            pagination=pagination,
            search=search,
            type_filter=type_filter,
            status_filter=status_filter,
            membership_types=membership_types,
        )
