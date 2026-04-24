"""Registro de rutas public membership en app (endpoints legacy)."""


def register_public_membership_routes(app):
    from datetime import datetime

    from flask import flash, redirect, render_template, request, session, url_for
    from flask_login import current_user, login_required

    from app import (
        Benefit,
        Certificate,
        CertificateEvent,
        db,
        has_saas_module_enabled,
        MembershipPlan,
        Service,
        ServicePricingRule,
        UserService,
        tenant_data_organization_id,
    )

    STATUS_META = {
        'active': {'label': 'Activo', 'badge': 'success'},
        'pending': {'label': 'Pendiente', 'badge': 'warning'},
        'scheduled': {'label': 'Agendado', 'badge': 'info'},
        'completed': {'label': 'Completado', 'badge': 'secondary'},
        'expired': {'label': 'Vencido', 'badge': 'danger'},
        'entitled': {'label': 'Incluido (plan registro)', 'badge': 'success'},
    }

    def _canonical_user_service_status(user_service):
        st = (getattr(user_service, 'status', '') or 'active').strip().lower()
        if st not in STATUS_META:
            st = 'active'
        appt = getattr(user_service, 'appointment', None)
        if appt:
            appt_st = (getattr(appt, 'status', '') or '').strip().lower()
            if appt_st in ('completed', 'completada'):
                return 'completed'
            if appt_st in ('pending', 'pendiente', 'confirmada', 'confirmed'):
                return 'scheduled'
        return st

    def _user_service_primary_action(status_key, service_id, order_id=None):
        if status_key == 'active':
            return ('Reservar cita', url_for('services.request_appointment', service_id=service_id))
        if status_key == 'pending':
            if order_id:
                return ('Ver detalle', url_for('payments_checkout.payment_status', payment_id=order_id))
            return ('Ver detalle', url_for('services.list'))
        if status_key == 'scheduled':
            return ('Ver cita', url_for('appointments.appointments_home'))
        if status_key == 'completed':
            return ('Ver historial', url_for('appointments.appointments_home'))
        return ('Comprar nuevamente', url_for('services.list'))

    @app.route('/dashboard')
    @login_required
    def dashboard():
        """Panel de control del usuario con verificación completa de estado"""
        if bool(getattr(current_user, 'must_change_password', False)):
            flash('Debes cambiar tu contraseña antes de continuar.', 'warning')
            return redirect(url_for('auth.change_password'))
        from app import Appointment, EventRegistration, Event, Payment, UserService
        from user_status_checker import UserStatusChecker
    
        # Verificar estado completo del usuario
        user_status = UserStatusChecker.check_user_status(current_user.id, db.session)
    
        active_membership = current_user.get_active_membership()
        _toid = tenant_data_organization_id()
        benefits = Benefit.query.filter_by(is_active=True, organization_id=_toid).all()
    
        # Calcular días desde inicio y días restantes
        days_active = None
        days_remaining = None
        now = datetime.utcnow()
    
        if active_membership:
            if active_membership.start_date:
                days_active = (now - active_membership.start_date).days
            if active_membership.end_date:
                days_remaining = (active_membership.end_date - now).days
    
        # Estadísticas del usuario
        upcoming_appointments = Appointment.query.filter(
            Appointment.user_id == current_user.id,
            Appointment.start_datetime >= now,
            Appointment.status.in_(['pending', 'confirmed', 'PENDIENTE', 'CONFIRMADA'])
        ).order_by(Appointment.start_datetime.asc()).limit(5).all()
    
        past_appointments_count = Appointment.query.filter(
            Appointment.user_id == current_user.id,
            Appointment.start_datetime < now
        ).count()
    
        upcoming_events = EventRegistration.query.join(Event).filter(
            EventRegistration.user_id == current_user.id,
            EventRegistration.registration_status == 'confirmed',
            Event.start_date >= now
        ).order_by(Event.start_date.asc()).limit(5).all()
    
        registered_events_count = EventRegistration.query.filter(
            EventRegistration.user_id == current_user.id,
            EventRegistration.registration_status == 'confirmed'
        ).count()

        available_services_count = UserService.query.filter(
            UserService.user_id == current_user.id,
            UserService.status.in_(('active', 'pending', 'scheduled')),
        ).count()

        recent_payments_count = Payment.query.filter(
            Payment.user_id == current_user.id
        ).count()

        pending_payments_count = Payment.query.filter(
            Payment.user_id == current_user.id,
            Payment.status.in_(('pending', 'awaiting_confirmation')),
        ).count()
    
        # Obtener todos los eventos públicos para el calendario
        all_public_events = Event.query.filter(
            Event.publish_status == 'published',
            Event.start_date.isnot(None)
        ).order_by(Event.start_date.asc()).all()
    
        # Citas confirmadas (leyenda bajo el calendario)
        user_confirmed_appointments = Appointment.query.filter(
            Appointment.user_id == current_user.id,
            Appointment.status.in_(['CONFIRMADA', 'confirmed']),
            Appointment.start_datetime.isnot(None),
            Appointment.start_datetime >= now
        ).order_by(Appointment.start_datetime.asc()).all()

        # Citas en el calendario del dashboard: pendiente + confirmada (misma idea que «Mi Agenda»)
        user_calendar_appointments = Appointment.query.filter(
            Appointment.user_id == current_user.id,
            Appointment.status.in_(['pending', 'confirmed', 'PENDIENTE', 'CONFIRMADA']),
            Appointment.start_datetime.isnot(None),
            Appointment.end_datetime.isnot(None),
            Appointment.start_datetime >= now,
        ).order_by(Appointment.start_datetime.asc()).limit(120).all()
    
        # Detectar si es un usuario nuevo (creado en las últimas 24 horas)
        is_new_user = False
        if current_user.created_at:
            hours_since_creation = (now - current_user.created_at).total_seconds() / 3600
            is_new_user = hours_since_creation < 24
    
        # Verificar si el usuario ha visto el onboarding
        onboarding_seen = session.get('onboarding_seen', False)
        show_onboarding = is_new_user and not onboarding_seen

        next_featured_event = None
        try:
            if has_saas_module_enabled(int(_toid), 'events'):
                from nodeone.services.events_portal import get_next_featured_portal_event

                next_featured_event = get_next_featured_portal_event(
                    organization_id=int(_toid), user=current_user
                )
        except Exception:
            next_featured_event = None
    
        return render_template('dashboard.html', 
                             membership=active_membership, 
                             benefits=benefits,
                             days_active=days_active,
                             days_remaining=days_remaining,
                             now=now,
                             upcoming_appointments=upcoming_appointments,
                             past_appointments_count=past_appointments_count,
                             upcoming_events=upcoming_events,
                             registered_events_count=registered_events_count,
                             all_public_events=all_public_events,
                             user_confirmed_appointments=user_confirmed_appointments,
                             user_calendar_appointments=user_calendar_appointments,
                             available_services_count=available_services_count,
                             recent_payments_count=recent_payments_count,
                             pending_payments_count=pending_payments_count,
                             show_onboarding=show_onboarding,
                             is_new_user=is_new_user,
                             user_status=user_status,
                             next_featured_event=next_featured_event)



    @app.route('/membership')
    @login_required
    def membership():
        """Página de membresía"""
        active_membership = current_user.get_active_membership()
    
        # Planes desde BD (para que se vean los planes de membresía)
        plans = MembershipPlan.get_active_ordered()
        pricing_monthly = {p.slug: float(p.price_monthly or 0) for p in plans}
        pricing_yearly = {p.slug: float(p.price_yearly or 0) for p in plans}
        if not pricing_monthly:
            pricing_monthly = {'basic': 0, 'personal': 12.42, 'emprendedor': 37.42, 'ejecutivo': 79.08}
        if not pricing_yearly:
            pricing_yearly = {'basic': 0, 'personal': 149, 'emprendedor': 449, 'ejecutivo': 949}
    
        # Servicios activos solo de la empresa del usuario (no mezclar con otras orgs)
        _svc_org = tenant_data_organization_id()
        all_services = Service.query.filter_by(is_active=True, organization_id=_svc_org).order_by(
            Service.display_order, Service.name
        ).all()
    
        # Jerarquía de membresías (desde BD; fallback a dict por si no hay tabla aún)
        try:
            membership_hierarchy = MembershipPlan.get_hierarchy()
            if not membership_hierarchy:
                membership_hierarchy = {'basic': 0, 'personal': 1, 'emprendedor': 2, 'ejecutivo': 3}
        except Exception:
            membership_hierarchy = {'basic': 0, 'personal': 1, 'emprendedor': 2, 'ejecutivo': 3}
    
        # Para cada servicio, determinar en qué planes está disponible
        # Esto se usará en el template para mostrar checkmarks
        services_with_plans = []
        for service in all_services:
            # Obtener todas las reglas de precio activas para este servicio
            pricing_rules = ServicePricingRule.query.filter_by(
                service_id=service.id,
                is_active=True
            ).all()
        
            available_plans = []
        
            # SIEMPRE incluir el membership_type base del servicio (CRÍTICO)
            # Esto asegura que un servicio con membership_type='ejecutivo' aparezca en esa columna, etc.
            if service.membership_type:
                smt = (service.membership_type or '').strip().lower()
                # ``basic`` en el servicio = disponible para todos los planes de pago (no hay fila de venta ``basic``).
                if smt == 'basic':
                    # Incluido en el nivel gratuito / base y en planes superiores (sin columna admin).
                    if 'basic' not in available_plans:
                        available_plans.append('basic')
                    for slug, tier in membership_hierarchy.items():
                        if slug in ('admin', 'basic'):
                            continue
                        if tier > 0 and slug not in available_plans:
                            available_plans.append(slug)
                elif smt not in available_plans:
                    available_plans.append(smt)
        
            # Si tiene reglas de precio, agregar también esos planes
            # Las pricing_rules permiten que un servicio aparezca en múltiples planes
            if pricing_rules:
                for rule in pricing_rules:
                    if rule.membership_type and rule.membership_type not in available_plans:
                        available_plans.append(rule.membership_type)
            else:
                # Si no tiene reglas, agregar también a todos los planes superiores (jerarquía)
                # Esto permite que servicios básicos aparezcan en todos los planes superiores
                service_tier = membership_hierarchy.get(service.membership_type, -1)
                if service_tier >= 0:  # Solo si el tier es válido
                    for plan_type, tier in membership_hierarchy.items():
                        if tier > service_tier and plan_type not in available_plans:
                            available_plans.append(plan_type)
        
            services_with_plans.append({
                'service': service,
                'available_plans': available_plans
            })
    
        # Sin columna ``admin``. ``basic`` se muestra si existe en BD (plan gratuito / entrada).
        plans_display = [p for p in plans if (p.slug or '').lower() != 'admin']
        # Certificado de membresía: evento activo "Certificado de Membresía" o code_prefix MEM (emitir desde esta página)
        membership_cert_event_id = None
        membership_cert_issued = False
        membership_cert_download_url = None
        if active_membership:
            try:
                CertificateEvent.__table__.create(db.engine, checkfirst=True)
                Certificate.__table__.create(db.engine, checkfirst=True)
                _mem_cert_oid = int(tenant_data_organization_id())
                if not CertificateEvent.query.filter(
                    CertificateEvent.organization_id == _mem_cert_oid,
                    db.or_(
                        CertificateEvent.name == 'Certificado de Membresía',
                        CertificateEvent.code_prefix == 'MEM',
                    ),
                ).first():
                    ev_default = CertificateEvent(
                        organization_id=_mem_cert_oid,
                        name='Certificado de Membresía',
                        is_active=True,
                        verification_enabled=True,
                        code_prefix='MEM',
                        membership_required_id=None,
                        event_required_id=None,
                    )
                    db.session.add(ev_default)
                    db.session.commit()
                cert_ev = CertificateEvent.query.filter(
                    CertificateEvent.organization_id == _mem_cert_oid,
                    CertificateEvent.is_active == True,
                    db.or_(
                        CertificateEvent.name == 'Certificado de Membresía',
                        CertificateEvent.code_prefix == 'MEM',
                    ),
                ).first()
                if cert_ev:
                    membership_cert_event_id = cert_ev.id
                    existing = Certificate.query.filter_by(
                        user_id=current_user.id,
                        certificate_event_id=cert_ev.id
                    ).first()
                    if existing:
                        membership_cert_issued = True
                        membership_cert_download_url = url_for('certificates_api.download_certificate', certificate_code=existing.certificate_code)
            except Exception:
                pass
        return render_template('membership.html', 
                             membership=active_membership,
                             plans=plans,
                             plans_display=plans_display,
                             pricing_monthly=pricing_monthly,
                             pricing_yearly=pricing_yearly,
                             services_with_plans=services_with_plans,
                             membership_hierarchy=membership_hierarchy,
                             membership_cert_event_id=membership_cert_event_id,
                             membership_cert_issued=membership_cert_issued,
                             membership_cert_download_url=membership_cert_download_url)




    @app.route('/member/plan')
    @login_required
    def member_plan():
        """Alias semántico para la vista de plan del cliente."""
        return redirect(url_for('membership'))


    def _entitlement_action_for_service(service):
        """CTA para servicio de plan básico aún sin fila en user_service."""
        stype = (getattr(service, 'service_type', '') or '').upper()
        if stype == 'CV_REGISTRATION':
            return 'Completar formulario', url_for('cv_registro', service=service.id)
        if stype == 'COURSE':
            return 'Ver en catálogo', url_for('services.list')
        el = (service.external_link or '').strip()
        if el:
            if el.startswith(('http://', 'https://', '//')):
                return 'Abrir enlace', el
            if el.startswith('/'):
                base = (request.url_root or '').rstrip('/')
                return 'Abrir enlace', base + el
        if service.requires_appointment():
            if stype == 'CONSULTIVO':
                return 'Solicitar reunión', url_for('appointments.request_appointment', service_id=service.id)
            return 'Solicitar cita', url_for('services.request_appointment', service_id=service.id)
        return 'Ver en catálogo', url_for('services.list')

    @app.route('/member/services')
    @login_required
    def member_services():
        """Compras (user_service) + servicios básicos del catálogo incluidos con el registro."""
        from sqlalchemy import func

        from _app.modules.services.service import resolve_service_card_image_url

        # Empresa del perfil (registro), no `tenant_data_organization_id()`: para usuarios admin
        # el host/selector puede apuntar a otra org y vaciaba servicios básicos de la suya.
        uoid = getattr(current_user, 'organization_id', None)
        try:
            _toid = int(uoid) if uoid is not None else int(tenant_data_organization_id())
        except (TypeError, ValueError):
            _toid = int(tenant_data_organization_id())
        records = (
            UserService.query.join(Service, UserService.service_id == Service.id)
            .filter(
                UserService.user_id == current_user.id,
                Service.organization_id == _toid,
            )
            .order_by(UserService.created_at.desc(), UserService.id.desc())
            .all()
        )

        cards = []
        purchased_service_ids = set()
        for rec in records:
            service = rec.service
            if not service:
                continue
            purchased_service_ids.add(service.id)
            status_key = _canonical_user_service_status(rec)
            meta = STATUS_META.get(status_key, STATUS_META['active'])
            action_label, action_url = _user_service_primary_action(
                status_key,
                service.id,
                order_id=getattr(rec, 'order_id', None),
            )
            cards.append(
                {
                    'id': rec.id,
                    'service_id': service.id,
                    'name': service.name,
                    'description': (service.description or '').strip(),
                    'image_url': resolve_service_card_image_url(service.name, service.image_url),
                    'icon': service.icon or 'fas fa-cog',
                    'status_key': status_key,
                    'status_label': meta['label'],
                    'status_badge': meta['badge'],
                    'created_at': rec.created_at,
                    'expires_at': rec.expires_at,
                    'appointment_id': rec.appointment_id,
                    'action_label': action_label,
                    'action_url': action_url,
                    'entitlement': False,
                }
            )

        # Servicios marcados como plan básico: derecho con cuenta; si no hubo compra, igual se listan
        basic_services = (
            Service.query.filter(
                Service.organization_id == _toid,
                Service.is_active == True,
                func.lower(func.coalesce(Service.membership_type, '')) == 'basic',
            )
            .order_by(Service.display_order, Service.name)
            .all()
        )
        entitlement_meta = STATUS_META['entitled']
        entitlement_cards = []
        for service in basic_services:
            if service.id in purchased_service_ids:
                continue
            alabel, aurl = _entitlement_action_for_service(service)
            entitlement_cards.append(
                {
                    'id': None,
                    'service_id': service.id,
                    'name': service.name,
                    'description': (service.description or '').strip(),
                    'image_url': resolve_service_card_image_url(service.name, service.image_url),
                    'icon': service.icon or 'fas fa-cog',
                    'status_key': 'entitled',
                    'status_label': entitlement_meta['label'],
                    'status_badge': entitlement_meta['badge'],
                    'created_at': None,
                    'expires_at': None,
                    'appointment_id': None,
                    'action_label': alabel,
                    'action_url': aurl,
                    'entitlement': True,
                }
            )

        cards = entitlement_cards + cards

        return render_template('member_services.html', cards=cards)


    @app.route('/member/payments')
    @login_required
    def member_payments():
        """Alias semántico para pagos/facturas del cliente."""
        return redirect(url_for('payments_checkout.payments_history'))


    @app.route('/benefits')
    @login_required
    def benefits():
        """Página de beneficios: muestra los de tu plan y planes inferiores (según jerarquía)."""
        active_membership = current_user.get_active_membership()
        if not active_membership:
            flash('Necesitas una membresía activa para acceder a los beneficios.', 'warning')
            return redirect(url_for('membership'))
        mt = (active_membership.membership_type or '').strip().lower()
        try:
            hierarchy = MembershipPlan.get_hierarchy()
            if not hierarchy:
                hierarchy = {'basic': 0, 'personal': 1, 'emprendedor': 2, 'ejecutivo': 3, 'admin': 99}
        except Exception:
            hierarchy = {'basic': 0, 'personal': 1, 'emprendedor': 2, 'ejecutivo': 3, 'admin': 99}
        user_level = hierarchy.get(mt, 0)
        allowed_types = [p for p, level in hierarchy.items() if level <= user_level]
        if not allowed_types:
            allowed_types = [mt] if mt else []
        _toid = tenant_data_organization_id()
        benefits = Benefit.query.filter(
            Benefit.organization_id == _toid,
            Benefit.membership_type.in_(allowed_types),
            Benefit.is_active == True
        ).order_by(Benefit.membership_type, Benefit.name).all()
        return render_template('benefits.html', benefits=benefits, membership=active_membership)







