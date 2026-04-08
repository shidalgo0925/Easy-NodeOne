#!/usr/bin/env python3
"""
Control de módulos SaaS por organización (Fase 1).
Importación diferida de app para evitar ciclos al cargar blueprints.
"""

from functools import wraps

from flask import flash, jsonify, redirect, request, url_for
from flask_login import current_user


def enforce_saas_module_or_response(module_code):
    """
    Si el módulo no está habilitado para el tenant, devuelve Response (403/redirect).
    Si está OK o no aplica, devuelve None.
    Los usuarios is_admin omiten el check (operación de plataforma).
    """
    if not current_user.is_authenticated:
        return None
    if getattr(current_user, 'is_admin', False):
        return None

    from app import get_current_organization_id, has_saas_module_enabled

    try:
        org_id = get_current_organization_id()
    except RuntimeError:
        # Sesión autenticada sin organization_id (race u org corrupta): reparar y seguir.
        try:
            from flask import session as _sess
            from app import (
                _usable_session_organization_id_for_user,
                default_organization_id,
                single_tenant_default_only,
            )

            if single_tenant_default_only():
                _sess['organization_id'] = default_organization_id()
            else:
                _sess['organization_id'] = _usable_session_organization_id_for_user(current_user)
            org_id = get_current_organization_id()
        except Exception:
            flash('Tu sesión perdió el contexto de organización. Inicia sesión de nuevo.', 'error')
            return redirect(url_for('auth.login'))
    bp = getattr(request, 'blueprint', '') or ''
    path = request.path or ''
    is_api = path.startswith('/api/') or bp.endswith('_api') or 'api' in bp

    if org_id is None:
        if is_api or request.is_json:
            return jsonify({'error': 'Organización no disponible', 'module': module_code}), 403
        flash('Debes iniciar sesión con un contexto de organización válido.', 'error')
        return redirect(url_for('dashboard'))

    if has_saas_module_enabled(org_id, module_code):
        return None

    if is_api or request.is_json:
        return jsonify({'error': 'Módulo no habilitado', 'module': module_code}), 403

    flash('Esta función no está habilitada para su organización.', 'error')
    return redirect(url_for('dashboard'))


def require_saas_module(module_code):
    """Decorador para vistas sueltas (opcional)."""

    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('auth.login'))
            resp = enforce_saas_module_or_response(module_code)
            if resp is not None:
                return resp
            return f(*args, **kwargs)

        return wrapped

    return decorator


def register_appointments_saas_guards(*blueprints):
    """Registra before_request (módulo appointments) en cada blueprint citas/API relacionada."""

    def _attach_guard(bp):
        @bp.before_request
        def _guard_appointments():
            return enforce_saas_module_or_response('appointments')

    for bp in blueprints:
        _attach_guard(bp)


def register_services_saas_guards(services_bp):
    """Catálogo /services y solicitud de cita con pago: mismo tenant que módulo citas."""

    @services_bp.before_request
    def _guard_services_catalog():
        return enforce_saas_module_or_response('appointments')


def register_events_saas_guards(events_bp, admin_events_bp, events_api_bp):
    """Registra before_request en los blueprints de eventos."""

    @events_bp.before_request
    def _guard_member_events():
        return enforce_saas_module_or_response('events')

    @admin_events_bp.before_request
    def _guard_admin_events():
        return enforce_saas_module_or_response('events')

    @events_api_bp.before_request
    def _guard_api_events():
        # API pública: sin sesión también debe respetar el módulo (tenant actual).
        if current_user.is_authenticated and getattr(current_user, 'is_admin', False):
            return None
        from app import _org_id_for_module_visibility, has_saas_module_enabled

        if has_saas_module_enabled(_org_id_for_module_visibility(), 'events'):
            return None
        return jsonify({'error': 'Módulo no habilitado', 'module': 'events'}), 403


# IA / chatbots (admin); api_ai_ping queda fuera (solo localhost).
_CHATBOT_APP_ENDPOINTS = frozenset({
    'admin_ai',
    'admin_chatbots',
    'ai_api.api_ai_config',
    'ai_api.api_ai_test',
})

_CRM_CONTACTS_APP_ENDPOINTS = frozenset({
    'admin_tenant_contacts',
    'admin_tenant_contact_delete',
    'admin_tenant_contact_update',
})


def register_saas_app_route_guards(app):
    """before_request a nivel app para vistas sueltas fuera de blueprints."""

    @app.before_request
    def _saas_guard_app_module_routes():
        ep = request.endpoint
        if ep in _CHATBOT_APP_ENDPOINTS:
            return enforce_saas_module_or_response('chatbot')
        if ep in _CRM_CONTACTS_APP_ENDPOINTS:
            return enforce_saas_module_or_response('crm_contacts')
        return None


def register_marketing_saas_guard(marketing_bp):
    """Bloquea marketing_email salvo rutas públicas (pixel, click, unsubscribe)."""

    @marketing_bp.before_request
    def _guard_marketing():
        path = request.path or ''
        if '/marketing/email/open/' in path or path.endswith('/email/open'):
            return None
        if '/marketing/email/click/' in path or '/marketing/email/click' in path:
            return None
        if '/marketing/unsubscribe/' in path:
            return None
        return enforce_saas_module_or_response('marketing_email')


def register_certificates_saas_guards(
    certificates_api_bp,
    certificates_page_bp,
    certificate_templates_bp,
    certificates_builder_bp,
    certificates_builder_page_bp,
):
    """Certificados (no aplica a verify público: va en otro blueprint)."""

    @certificates_api_bp.before_request
    def _guard_cert_api():
        return enforce_saas_module_or_response('certificates')

    @certificates_page_bp.before_request
    def _guard_cert_page():
        return enforce_saas_module_or_response('certificates')

    @certificate_templates_bp.before_request
    def _guard_cert_tpl():
        return enforce_saas_module_or_response('certificates')

    @certificates_builder_bp.before_request
    def _guard_cert_bld_api():
        return enforce_saas_module_or_response('certificates')

    @certificates_builder_page_bp.before_request
    def _guard_cert_bld_page():
        return enforce_saas_module_or_response('certificates')


def register_simple_saas_guard(bp, module_code):
    """before_request genérico para un blueprint."""

    @bp.before_request
    def _guard_saas_module():
        return enforce_saas_module_or_response(module_code)


def register_payments_checkout_saas_guard(payments_checkout_bp):
    """Módulo payments; excluye webhook Stripe (sin sesión / firma propia)."""

    @payments_checkout_bp.before_request
    def _guard_payments_checkout_saas():
        if request.endpoint == 'payments_checkout.stripe_webhook':
            return None
        return enforce_saas_module_or_response('payments')


def register_policies_public_saas_guard(policies_bp):
    """
    /normativas y detalle: si el módulo policies está off para el tenant actual, 404.
    La gestión en /admin/policies se protege aparte (tenant admin bloqueado; is_admin plataforma puede entrar).
    """

    @policies_bp.before_request
    def _guard_policies_normativas():
        from flask import abort

        from app import _org_id_for_module_visibility, has_saas_module_enabled

        if has_saas_module_enabled(_org_id_for_module_visibility(), 'policies'):
            return None
        abort(404)

