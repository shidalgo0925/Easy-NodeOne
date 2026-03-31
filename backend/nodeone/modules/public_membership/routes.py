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
        MembershipPlan,
        Service,
        ServicePricingRule,
        tenant_data_organization_id,
    )

    @app.route('/dashboard')
    @login_required
    def dashboard():
        """Panel de control del usuario con verificación completa de estado"""
        if bool(getattr(current_user, 'must_change_password', False)):
            flash('Debes cambiar tu contraseña antes de continuar.', 'warning')
            return redirect(url_for('auth.change_password'))
        from app import Appointment, EventRegistration, Event
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
    
        # Obtener todos los eventos públicos para el calendario
        all_public_events = Event.query.filter(
            Event.publish_status == 'published',
            Event.start_date.isnot(None)
        ).order_by(Event.start_date.asc()).all()
    
        # Citas confirmadas del usuario para el calendario (confirmadas por asesor)
        user_confirmed_appointments = Appointment.query.filter(
            Appointment.user_id == current_user.id,
            Appointment.status.in_(['CONFIRMADA', 'confirmed']),
            Appointment.start_datetime.isnot(None),
            Appointment.start_datetime >= now
        ).order_by(Appointment.start_datetime.asc()).all()
    
        # Detectar si es un usuario nuevo (creado en las últimas 24 horas)
        is_new_user = False
        if current_user.created_at:
            hours_since_creation = (now - current_user.created_at).total_seconds() / 3600
            is_new_user = hours_since_creation < 24
    
        # Verificar si el usuario ha visto el onboarding
        onboarding_seen = session.get('onboarding_seen', False)
        show_onboarding = is_new_user and not onboarding_seen
    
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
                             show_onboarding=show_onboarding,
                             is_new_user=is_new_user,
                             user_status=user_status)  # Pasar estado del usuario al template



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
            pricing_monthly = {'basic': 0, 'pro': 5, 'premium': 10, 'deluxe': 15, 'corporativo': 25}
        if not pricing_yearly:
            pricing_yearly = {'basic': 0, 'pro': 60, 'premium': 120, 'deluxe': 200, 'corporativo': 300}
    
        # Servicios activos solo de la empresa del usuario (no mezclar con otras orgs)
        _svc_org = tenant_data_organization_id()
        all_services = Service.query.filter_by(is_active=True, organization_id=_svc_org).order_by(
            Service.display_order, Service.name
        ).all()
    
        # Jerarquía de membresías (desde BD; fallback a dict por si no hay tabla aún)
        try:
            membership_hierarchy = MembershipPlan.get_hierarchy()
            if not membership_hierarchy:
                membership_hierarchy = {'basic': 0, 'pro': 1, 'premium': 2, 'deluxe': 3, 'corporativo': 4}
        except Exception:
            membership_hierarchy = {'basic': 0, 'pro': 1, 'premium': 2, 'deluxe': 3, 'corporativo': 4}
    
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
            # Esto asegura que un servicio con membership_type='corporativo' siempre aparezca en corporativo
            if service.membership_type:
                if service.membership_type not in available_plans:
                    available_plans.append(service.membership_type)
        
            # Si tiene reglas de precio, agregar también esos planes
            # Las pricing_rules permiten que un servicio aparezca en múltiples planes
            if pricing_rules:
                for rule in pricing_rules:
                    if rule.membership_type and rule.membership_type not in available_plans:
                        available_plans.append(rule.membership_type)
            else:
                # Si no tiene reglas, agregar también a todos los planes superiores (jerarquía)
                # Esto permite que servicios básicos aparezcan en todos los planes superiores
                # IMPORTANTE: Excluir 'corporativo' de la herencia automática
                # Solo servicios explícitamente marcados como corporativo aparecen en ese plan
                service_tier = membership_hierarchy.get(service.membership_type, -1)
                if service_tier >= 0:  # Solo si el tier es válido
                    for plan_type, tier in membership_hierarchy.items():
                        # Excluir corporativo de la herencia automática
                        if tier > service_tier and plan_type != 'corporativo' and plan_type not in available_plans:
                            available_plans.append(plan_type)
        
            services_with_plans.append({
                'service': service,
                'available_plans': available_plans
            })
    
        plans_display = [p for p in plans if (p.slug or '') != 'admin']
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
                hierarchy = {'basic': 0, 'pro': 1, 'premium': 2, 'deluxe': 3, 'corporativo': 4, 'admin': 5}
        except Exception:
            hierarchy = {'basic': 0, 'pro': 1, 'premium': 2, 'deluxe': 3, 'corporativo': 4, 'admin': 5}
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







