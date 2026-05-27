"""Acceso privado por compra válida (single-tenant / policy global)."""

from __future__ import annotations

import os

from flask import request, session, url_for
from flask_login import current_user

from nodeone.services.registration_policy import (
    REGISTRATION_ACADEMIC_CLOSED,
    registration_policy_for_org,
)

ACTIVE_ENROLLMENT_STATUSES = ('paid', 'confirmed', 'active')
ACTIVE_PAYMENT_STATUSES = ('paid', 'succeeded', 'completed', 'confirmed', 'active')
ACTIVE_EVENT_REGISTRATION_STATUSES = ('confirmed', 'paid', 'approved', 'active')


def _user_org_id(user) -> int | None:
    try:
        oid = getattr(user, 'organization_id', None)
        return int(oid) if oid is not None else None
    except (TypeError, ValueError):
        return None


def is_academic_closed_org(org_or_id) -> bool:
    return registration_policy_for_org(org_or_id) == REGISTRATION_ACADEMIC_CLOSED


def has_active_enrollment(user_id: int, organization_id: int | None = None) -> bool:
    """Matrícula pagada o confirmada en ``academic_program_enrollment``."""
    from models.academic_program import AcademicProgramEnrollment

    uid = int(user_id)
    q = AcademicProgramEnrollment.query.filter(
        AcademicProgramEnrollment.user_id == uid,
        AcademicProgramEnrollment.status.in_(ACTIVE_ENROLLMENT_STATUSES),
    )
    if organization_id is not None:
        q = q.filter_by(organization_id=int(organization_id))
    return q.first() is not None


def has_paid_payment(user_id: int, organization_id: int | None = None) -> bool:
    """Pago confirmado (NO incluye pending/manual sin aprobar)."""
    from models.payments import Payment

    uid = int(user_id)
    q = Payment.query.filter(
        Payment.user_id == uid,
        Payment.status.in_(ACTIVE_PAYMENT_STATUSES),
    )
    if organization_id is not None and hasattr(Payment, 'organization_id'):
        q = q.filter(Payment.organization_id == int(organization_id))
    return q.first() is not None


def has_approved_event_access(user_id: int, organization_id: int | None = None) -> bool:
    """Registro de evento en estado aprobado/confirmado/pagado."""
    from models.events import EventRegistration

    uid = int(user_id)
    q = EventRegistration.query.filter(
        EventRegistration.user_id == uid,
        EventRegistration.registration_status.in_(ACTIVE_EVENT_REGISTRATION_STATUSES),
    )
    if organization_id is not None and hasattr(EventRegistration, 'organization_id'):
        q = q.filter(EventRegistration.organization_id == int(organization_id))
    return q.first() is not None


def has_active_membership_access(user) -> bool:
    try:
        return bool(user and user.get_active_membership())
    except Exception:
        return False


def user_has_paid_access(user, organization_id: int | None = None) -> bool:
    """
    Acceso privado cuando existe una compra/activación válida.
    Orden: membresía -> matrícula -> pago -> evento aprobado.
    """
    if not user or not getattr(user, 'is_authenticated', False):
        return False
    if user_bypasses_academic_gate(user):
        return True
    oid = organization_id if organization_id is not None else _user_org_id(user)
    uid = int(getattr(user, 'id', 0) or 0)
    if uid <= 0:
        return False
    if has_active_membership_access(user):
        return True
    if has_active_enrollment(uid, oid):
        return True
    if has_paid_payment(uid, oid):
        return True
    if has_approved_event_access(uid, oid):
        return True
    return False


def list_member_enrollments(user_id: int, organization_id: int | None = None) -> list:
    from models.academic_program import AcademicProgram, AcademicProgramEnrollment

    uid = int(user_id)
    q = (
        AcademicProgramEnrollment.query.filter_by(user_id=uid)
        .join(AcademicProgram, AcademicProgramEnrollment.program_id == AcademicProgram.id)
        .order_by(AcademicProgramEnrollment.created_at.desc())
    )
    if organization_id is not None:
        q = q.filter(AcademicProgramEnrollment.organization_id == int(organization_id))
    return q.all()


def list_published_programs_for_org(organization_id: int, *, limit: int = 12) -> list:
    from models.academic_program import AcademicProgram

    return (
        AcademicProgram.query.filter_by(
            organization_id=int(organization_id), status='published'
        )
        .order_by(AcademicProgram.name.asc())
        .limit(int(limit))
        .all()
    )


def group_enrollments_for_display(enrollments: list) -> dict[str, list]:
    """Agrupa matrículas por ``program.program_type`` para el dashboard."""
    groups: dict[str, list] = {}
    labels = {
        'diplomado': 'Diplomados',
        'curso': 'Cursos',
        'taller': 'Talleres',
        'certificacion': 'Certificaciones',
        'servicio': 'Servicios',
        'programa': 'Programas',
    }
    for en in enrollments or []:
        prog = getattr(en, 'program', None)
        key = (getattr(prog, 'program_type', None) or 'programa').strip().lower()
        label = labels.get(key, key.replace('_', ' ').title())
        groups.setdefault(label, []).append(en)
    return groups


def continuar_url_for_enrollment(enrollment) -> str | None:
    prog = getattr(enrollment, 'program', None)
    plan = getattr(enrollment, 'pricing_plan', None)
    if prog is None or not (getattr(prog, 'slug', None) or '').strip():
        return None
    slug = (prog.slug or '').strip().lower()
    plan_code = (getattr(plan, 'code', None) or 'full').strip().lower()
    return url_for('payments.diplomado_continuar', slug=slug, plan=plan_code)


def pending_enrollment_for_user(user_id: int, organization_id: int | None = None):
    from models.academic_program import AcademicProgramEnrollment

    q = AcademicProgramEnrollment.query.filter_by(
        user_id=int(user_id), status='pending_payment'
    ).order_by(AcademicProgramEnrollment.id.desc())
    if organization_id is not None:
        q = q.filter_by(organization_id=int(organization_id))
    return q.first()


def user_bypasses_academic_gate(user) -> bool:
    """Admin plataforma, admin tenant (RBAC) o asesor: sin bloqueo de campus."""
    if not user or not getattr(user, 'is_authenticated', False):
        return True
    if getattr(user, 'is_admin', False):
        return True
    if getattr(user, 'is_advisor', False):
        return True
    try:
        from app import _user_has_any_admin_permission

        if _user_has_any_admin_permission(user):
            return True
    except Exception:
        pass
    return False


def member_needs_academic_enrollment(user, organization_id: int | None = None) -> bool:
    if user_bypasses_academic_gate(user):
        return False
    oid = organization_id if organization_id is not None else _user_org_id(user)
    if oid is None or not is_academic_closed_org(oid):
        return False
    return not has_active_enrollment(int(user.id), oid)


def require_paid_access_enabled() -> bool:
    """
    Política global del despliegue (single-tenant): exigir compra válida.
    """
    raw = (os.environ.get('REQUIRE_PAID_ACCESS') or '').strip().lower()
    if raw in ('1', 'true', 'yes', 'on'):
        return True
    if raw in ('0', 'false', 'no', 'off'):
        return False
    try:
        from nodeone.config.settings import settings as _settings

        return bool(getattr(_settings, 'REQUIRE_PAID_ACCESS', True))
    except Exception:
        return True


_ACADEMIC_GATE_ALLOW_PREFIXES = (
    '/static/',
    '/login',
    '/logout',
    '/register',
    '/auth/',
    '/oauth',
    '/change-password',
    '/resend-verification',
    '/verify-email',
    '/select-organization',
    '/set-organization',
    '/inscripcion',
    '/programas',
    '/program-resources/',
    '/programa-academico/',
    '/events',
    '/checkout',
    '/cart',
    '/payment/',
    '/payments/',
    '/create-payment-intent',
    '/api/public/',
    '/api/landing/',
    '/api/catalog/',
    '/member-payments',
    '/membership',
    '/member/plan',
    '/member-payments',
    '/payments-history',
    '/programs/',
    '/public/',
    '/service-worker',
    '/manifest',
)


_ACADEMIC_GATE_ALLOW_ENDPOINTS = frozenset({
    'auth.login',
    'auth.register',
    'auth.logout',
    'auth.select_organization',
    'auth.change_password',
    'register',
    'login',
    'logout',
    'resend_verification',
    'verify_email',
    'set_organization',
    'payments.cart',
    'payments.checkout',
    'payments.diplomado_landing',
    'payments.diplomado_continuar',
    'payments.inscripcion_seleccionar_plan',
    'payments.checkout_programa_shortcut',
    'payments.program_enrollment_thanks',
    'program_resource_download',
    'academic_program_public_pdf',
    'member_plan',
    'membership',
    'member_payments',
})


def _path_allowed_without_enrollment() -> bool:
    path = (request.path or '').lower()
    for prefix in _ACADEMIC_GATE_ALLOW_PREFIXES:
        if path.startswith(prefix):
            return True
    ep = request.endpoint or ''
    if ep in _ACADEMIC_GATE_ALLOW_ENDPOINTS:
        return True
    if ep and (ep.startswith('payments.') or ep.startswith('payments_checkout.')):
        return True
    return False


def default_inscripcion_url_for_org(organization_id: int) -> str:
    from models.academic_program import AcademicProgram

    p = (
        AcademicProgram.query.filter_by(organization_id=int(organization_id), status='published')
        .order_by(AcademicProgram.id.asc())
        .first()
    )
    if p and (p.slug or '').strip():
        return url_for('payments.diplomado_landing', slug=p.slug.strip().lower())
    return url_for('dashboard')


def academic_gate_redirect_url() -> str:
    """Destino cuando el miembro sin matrícula intenta abrir catálogo abierto."""
    slug = (session.get('pending_program_slug') or '').strip()
    if slug:
        return url_for('payments.diplomado_landing', slug=slug)
    return url_for('dashboard')


def maybe_redirect_academic_gate():
    """
    ``before_request``: campus cerrado sin matrícula → solo inscripción/checkout/cuenta.
    Retorna ``Response`` redirect o ``None``.
    """
    from flask import redirect

    if not getattr(current_user, 'is_authenticated', False):
        return None
    if session.get('require_org_selection'):
        return None
    if user_bypasses_academic_gate(current_user):
        return None
    oid = _user_org_id(current_user)
    try:
        from app import get_current_organization_id

        sid = get_current_organization_id()
        if sid is not None:
            oid = int(sid)
    except Exception:
        pass
    # Gate activo cuando el despliegue exige compra o la org está en academic_closed.
    if not (require_paid_access_enabled() or is_academic_closed_org(oid)):
        return None
    if user_has_paid_access(current_user, oid):
        return None
    if _path_allowed_without_enrollment():
        return None
    path = (request.path or '').lower()
    if path.startswith('/api/'):
        from flask import jsonify

        return jsonify(
            {
                'success': False,
                'message': 'forbidden_paid_access_required',
            }
        ), 403
    from flask import flash

    flash(
        'Tu acceso privado se activa al confirmar una compra válida '
        '(membresía, matrícula, pago aprobado o evento confirmado).',
        'info',
    )
    return redirect(academic_gate_redirect_url())
