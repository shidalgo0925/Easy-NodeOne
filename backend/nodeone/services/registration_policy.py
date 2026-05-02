"""Política de registro público por tenant (SaasOrganization.registration_policy)."""

from __future__ import annotations

from models.saas import SaasOrganization
from nodeone.core.db import db

REGISTRATION_FREE = 'free_registration'
REGISTRATION_PAID = 'paid_only'
REGISTRATION_ADMIN = 'admin_only'
REGISTRATION_INVITE = 'invitation_only'

REGISTRATION_POLICIES = (
    REGISTRATION_FREE,
    REGISTRATION_PAID,
    REGISTRATION_ADMIN,
    REGISTRATION_INVITE,
)


def normalize_registration_policy(raw: str | None) -> str:
    s = (raw or '').strip()
    return s if s in REGISTRATION_POLICIES else REGISTRATION_FREE


def get_organization(org_or_id: SaasOrganization | int | None) -> SaasOrganization | None:
    if org_or_id is None:
        return None
    if isinstance(org_or_id, SaasOrganization):
        return org_or_id
    try:
        oid = int(org_or_id)
    except (TypeError, ValueError):
        return None
    return SaasOrganization.query.get(oid)


def registration_policy_for_org(org_or_id: SaasOrganization | int | None) -> str:
    org = get_organization(org_or_id)
    if org is None:
        return REGISTRATION_FREE
    return normalize_registration_policy(getattr(org, 'registration_policy', None))


def can_register_publicly(org_or_id: SaasOrganization | int | None) -> bool:
    return registration_policy_for_org(org_or_id) == REGISTRATION_FREE


def requires_payment_before_user(org_or_id: SaasOrganization | int | None) -> bool:
    return registration_policy_for_org(org_or_id) == REGISTRATION_PAID


def requires_admin_creation(org_or_id: SaasOrganization | int | None) -> bool:
    return registration_policy_for_org(org_or_id) == REGISTRATION_ADMIN


def requires_invitation(org_or_id: SaasOrganization | int | None) -> bool:
    return registration_policy_for_org(org_or_id) == REGISTRATION_INVITE


def session_key_paid_registration(org_id: int) -> str:
    return f'reg_policy_paid_ok_{int(org_id)}'


def mark_session_paid_registration_allowed(sess, organization_id: int) -> None:
    """Tras checkout pagado: permite completar alta (formulario u OAuth) en esta org."""
    sess[session_key_paid_registration(organization_id)] = True
    sess.modified = True


def session_allows_paid_registration(sess, organization_id: int) -> bool:
    return bool(sess.get(session_key_paid_registration(int(organization_id))))


def assert_can_create_user_via_public_flow(
    organization_id: int | None,
    *,
    has_valid_invite: bool,
    sess,
    oauth_new_user: bool,
) -> tuple[bool, str | None]:
    """
    Validar creación de usuario nuevo vía /register o OAuth (no aplica a admin ni importaciones).
    has_valid_invite: invitación válida y email coincidente.
    """
    if not organization_id:
        return False, 'No se pudo determinar la organización.'
    org = get_organization(organization_id)
    if org is None:
        return False, 'Organización no encontrada.'
    pol = registration_policy_for_org(org)

    if pol == REGISTRATION_FREE:
        return True, None

    if pol == REGISTRATION_ADMIN:
        return False, 'El registro público está cerrado. Creá tu cuenta solo mediante el administrador de la institución.'

    if pol == REGISTRATION_INVITE:
        if has_valid_invite:
            return True, None
        return False, 'Solo podés registrarte con un enlace de invitación válido enviado por la institución.'

    if pol == REGISTRATION_PAID:
        if session_allows_paid_registration(sess, int(organization_id)):
            return True, None
        if has_valid_invite:
            return True, None
        return (
            False,
            'Para esta institución el alta se habilita después de completar un pago (curso o membresía) o con invitación. '
            'Si ya pagaste, volvé desde el enlace de confirmación o iniciá sesión si ya tenés cuenta.',
        )

    return True, None


def registration_notice_for_banner(organization_id: int | None) -> str | None:
    """Texto suave para GET /register (sin bloquear la vista del formulario)."""
    if not organization_id:
        return None
    pol = registration_policy_for_org(organization_id)
    if pol == REGISTRATION_FREE:
        return None
    if pol == REGISTRATION_ADMIN:
        return 'Esta institución no permite autoregistro: contactá al administrador para que te den de alta.'
    if pol == REGISTRATION_INVITE:
        return 'Esta institución solo permite registro con invitación: usá el enlace que te enviaron por correo.'
    if pol == REGISTRATION_PAID:
        return 'Esta institución suele dar de alta tras un pago o invitación. Si ya pagaste, seguí el enlace del comprobante o iniciá sesión.'
    return None
