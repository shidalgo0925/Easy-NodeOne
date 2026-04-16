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
            from nodeone.services.user_organization import user_in_org_clause

            scope_oid = admin_data_scope_organization_id()
            try:
                pending_payments_count = (
                    db.session.query(Payment)
                    .join(User, Payment.user_id == User.id)
                    .filter(user_in_org_clause(User, scope_oid), Payment.ocr_status.in_(['pending', 'needs_review']), Payment.status == 'pending')
                    .count()
                )
            except AttributeError:
                pending_payments_count = (
                    db.session.query(Payment)
                    .join(User, Payment.user_id == User.id)
                    .filter(user_in_org_clause(User, scope_oid), Payment.status == 'pending')
                    .count()
                )

            total_users = User.query.filter(user_in_org_clause(User, scope_oid)).count()

            try:
                total_memberships = db.session.query(Membership).join(User, Membership.user_id == User.id).filter(user_in_org_clause(User, scope_oid)).count()
                active_memberships = (
                    db.session.query(Membership)
                    .join(User, Membership.user_id == User.id)
                    .filter(user_in_org_clause(User, scope_oid), Membership.is_active.is_(True))
                    .count()
                )
                recent_memberships = (
                    db.session.query(Membership)
                    .join(User, Membership.user_id == User.id)
                    .filter(user_in_org_clause(User, scope_oid))
                    .order_by(Membership.created_at.desc())
                    .limit(5)
                    .all()
                )
            except (AttributeError, Exception):
                total_memberships = (
                    db.session.query(Subscription)
                    .join(User, Subscription.user_id == User.id)
                    .filter(user_in_org_clause(User, scope_oid), Subscription.status == 'active')
                    .count()
                )
                active_memberships = total_memberships
                recent_memberships = (
                    db.session.query(Subscription)
                    .join(User, Subscription.user_id == User.id)
                    .filter(user_in_org_clause(User, scope_oid))
                    .order_by(Subscription.created_at.desc())
                    .limit(5)
                    .all()
                )

            total_payments = (
                db.session.query(Payment)
                .join(User, Payment.user_id == User.id)
                .filter(user_in_org_clause(User, scope_oid), Payment.status == 'succeeded')
                .count()
            )
            try:
                succeeded_payments = (
                    db.session.query(Payment)
                    .join(User, Payment.user_id == User.id)
                    .filter(user_in_org_clause(User, scope_oid), Payment.status == 'succeeded')
                    .all()
                )
                total_revenue = sum([p.amount for p in succeeded_payments]) / 100.0
            except Exception:
                total_revenue = 0.0

            recent_users = (
                User.query.filter(user_in_org_clause(User, scope_oid)).order_by(User.created_at.desc()).limit(5).all()
            )
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
        from nodeone.services.user_organization import user_in_org_clause

        scope_oid = admin_data_scope_organization_id()

        def _load_legacy_memberships():
            def _q():
                return (
                    db.session.query(Membership)
                    .join(User, Membership.user_id == User.id)
                    .filter(user_in_org_clause(User, scope_oid))
                )

            try:
                return _q().order_by(Membership.created_at.desc()).all()
            except Exception:
                db.session.rollback()
            try:
                return _q().order_by(Membership.id.desc()).all()
            except Exception:
                db.session.rollback()
                app.logger.exception('admin_memberships: consulta Membership falló')
                return []

        def _load_subscriptions():
            def _q():
                return (
                    db.session.query(Subscription)
                    .join(User, Subscription.user_id == User.id)
                    .filter(user_in_org_clause(User, scope_oid))
                )

            try:
                return _q().order_by(Subscription.created_at.desc()).all()
            except Exception:
                db.session.rollback()
            try:
                return _q().order_by(Subscription.id.desc()).all()
            except Exception:
                db.session.rollback()
                app.logger.exception('admin_memberships: consulta Subscription falló')
                return []

        old_memberships = _load_legacy_memberships()
        subscriptions = _load_subscriptions()

        def _subscription_amount_eur(payment):
            if payment is None:
                return 0.0
            try:
                amt = getattr(payment, 'amount', None)
                if amt is None:
                    return 0.0
                return float(amt) / 100.0
            except (TypeError, ValueError):
                return 0.0

        def _as_float(v, default=0.0):
            try:
                if v is None:
                    return default
                return float(v)
            except (TypeError, ValueError):
                return default

        def _str_type(v):
            if v is None:
                return ''
            return str(v).strip()

        def _safe_user(obj):
            try:
                u = getattr(obj, 'user', None)
                if u is not None and getattr(u, 'id', None):
                    return u
            except Exception:
                pass
            return None

        def _safe_payment(sub):
            try:
                p = getattr(sub, 'payment', None)
                if p is not None:
                    return p
            except Exception:
                pass
            return None

        def _user_email(u):
            if u is None:
                return ''
            try:
                return (getattr(u, 'email', None) or '').strip()
            except Exception:
                return ''

        _epoch = datetime(1970, 1, 1)
        all_memberships = []
        skipped_rows = 0
        for sub in subscriptions:
            try:
                pay = _safe_payment(sub)
                st = getattr(pay, 'status', None) if pay is not None else None
                u = _safe_user(sub)
                all_memberships.append(
                    {
                        'id': sub.id,
                        'user': u,
                        'user_email': _user_email(u),
                        'membership_type': _str_type(getattr(sub, 'membership_type', None)) or 'basic',
                        'start_date': getattr(sub, 'start_date', None),
                        'end_date': getattr(sub, 'end_date', None),
                        'amount': _subscription_amount_eur(pay),
                        'is_active': bool(sub.is_currently_active()),
                        'payment_status': 'paid' if st == 'succeeded' else 'pending',
                        'payment_id': getattr(sub, 'payment_id', None),
                        'is_subscription': True,
                        'created_at': getattr(sub, 'created_at', None) or _epoch,
                    }
                )
            except Exception:
                skipped_rows += 1
                app.logger.exception('admin_memberships: fila subscription id=%s omitida', getattr(sub, 'id', '?'))

        for mem in old_memberships:
            try:
                u = _safe_user(mem)
                all_memberships.append(
                    {
                        'id': mem.id,
                        'user': u,
                        'user_email': _user_email(u),
                        'membership_type': _str_type(getattr(mem, 'membership_type', None)) or 'basic',
                        'start_date': getattr(mem, 'start_date', None),
                        'end_date': getattr(mem, 'end_date', None),
                        'amount': _as_float(getattr(mem, 'amount', None), 0.0),
                        'is_active': bool(getattr(mem, 'is_active', False)),
                        'payment_status': str(getattr(mem, 'payment_status', None) or 'unknown'),
                        'payment_id': None,
                        'is_subscription': False,
                        'created_at': getattr(mem, 'created_at', None) or datetime.utcnow(),
                    }
                )
            except Exception:
                skipped_rows += 1
                app.logger.exception('admin_memberships: fila membership id=%s omitida', getattr(mem, 'id', '?'))

        if skipped_rows:
            flash(
                f'Se omitieron {skipped_rows} fila(s) por datos incompletos (usuario/pago). El resto se muestra abajo.',
                'warning',
            )

        all_memberships.sort(key=lambda x: x.get('created_at') or _epoch, reverse=True)
        type_labels = []
        for m in all_memberships:
            t = _str_type(m.get('membership_type'))
            if t:
                type_labels.append(t)
        membership_types = sorted(set(type_labels))
        search = request.args.get('search', '').strip().lower()
        raw_mt = (request.args.get('mt') or request.args.get('type') or 'all').strip()
        type_filter = raw_mt if raw_mt else 'all'
        status_filter = request.args.get('status', 'all')
        try:
            page = int(request.args.get('page', 1))
        except (TypeError, ValueError):
            page = 1
        try:
            per_page = min(int(request.args.get('per_page', 10)), 100)
        except (TypeError, ValueError):
            per_page = 10

        if search:

            def _search_match(m):
                em = (m.get('user_email') or '').lower()
                if em.find(search) >= 0:
                    return True
                u = m.get('user')
                if not u:
                    return False
                return (
                    (getattr(u, 'first_name', None) or '').lower().find(search) >= 0
                    or (getattr(u, 'last_name', None) or '').lower().find(search) >= 0
                    or (getattr(u, 'email', None) or '').lower().find(search) >= 0
                )

            all_memberships = [m for m in all_memberships if _search_match(m)]
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

        class _MembershipPagination:
            """Misma firma que Flask-SQLAlchemy Pagination.iter_pages() para la plantilla."""

            __slots__ = ('page', 'per_page', 'total', 'pages', 'has_prev', 'has_next', 'prev_num', 'next_num')

            def __init__(self, page_: int, per_page_: int, total_: int, pages_: int) -> None:
                self.page = page_
                self.per_page = per_page_
                self.total = total_
                self.pages = pages_
                self.has_prev = page_ > 1
                self.has_next = page_ < pages_
                self.prev_num = page_ - 1
                self.next_num = page_ + 1

            def iter_pages(
                self,
                left_edge=1,
                right_edge=1,
                left_current=2,
                right_current=2,
                **_kwargs,
            ):
                for p in range(1, self.pages + 1):
                    yield p

        pagination = _MembershipPagination(page, per_page, total, pages)

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
