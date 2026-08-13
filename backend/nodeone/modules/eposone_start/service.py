"""Orquestación comercial /start EPosOne Standalone (ADR-024 / ADR-031 enmienda P0).

Standalone: Cliente ETS + suscripción/licencia + 7 días + código email + APK.
NO crea Organización operativa del negocio (Café Amor nace en EP1).
NO emite provisioning Connected (ADR-034).
"""

from __future__ import annotations

import os
import re
import secrets
import unicodedata
from datetime import datetime, timedelta
from typing import Any

from nodeone.core.platform.commercial_plans import get_commercial_plan, normalize_commercial_plan_code
from nodeone.modules.eposone_start.recommend import normalize_business_type, plan_public_view

PRODUCT_CODE = 'eposone'
DEFAULT_COUNTRY = 'Panamá'
DEFAULT_TZ = 'America/Panama'
STANDALONE_PLAN = 'standalone'
STANDALONE_GRACE_DAYS = 7


class StartAssistantError(Exception):
    def __init__(self, code: str, message: str, *, http_status: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.http_status = http_status


# APK hospedado en EN1 (static). Play Store solo si se fuerza por env.
DEFAULT_APK_DOWNLOAD_URL = '/static/apk/eposone/EPosOne.apk'


def play_store_url() -> str:
    """URL de descarga de la app: APK en EN1 por defecto.

    Prioridad: NODEONE_EPOSONE_APK_URL → NODEONE_EPOSONE_PLAY_STORE_URL → APK estático.
    El nombre histórico `play_store_url` se conserva en la API /start.
    """
    apk = (os.environ.get('NODEONE_EPOSONE_APK_URL') or '').strip()
    if apk:
        return apk
    play = (os.environ.get('NODEONE_EPOSONE_PLAY_STORE_URL') or '').strip()
    if play:
        return play
    return DEFAULT_APK_DOWNLOAD_URL


def download_cta_label(url: str | None = None) -> str:
    """Etiqueta del CTA según destino (APK EN1 vs Play)."""
    target = (url if url is not None else play_store_url()).strip().lower()
    if 'play.google.com' in target:
        return 'Abrir Google Play'
    return 'Descargar APK'


def _slugify(text: str, *, max_len: int = 40) -> str:
    raw = unicodedata.normalize('NFKD', (text or '').strip())
    ascii_only = ''.join(c for c in raw if not unicodedata.combining(c))
    slug = re.sub(r'[^a-zA-Z0-9]+', '-', ascii_only.lower()).strip('-')
    if not slug:
        slug = 'negocio'
    return slug[:max_len].rstrip('-')


def _unique_subdomain(base: str) -> str:
    from models.saas import SaasOrganization

    root = _slugify(base, max_len=28) or 'negocio'
    for _ in range(12):
        candidate = f'{root}-{secrets.token_hex(2)}'
        if SaasOrganization.query.filter_by(subdomain=candidate).first() is None:
            return candidate
    return f'{root}-{secrets.token_hex(4)}'


def _split_display_name(full_name: str) -> tuple[str, str]:
    parts = [p for p in (full_name or '').strip().split() if p]
    if not parts:
        return 'Usuario', 'EPosOne'
    if len(parts) == 1:
        return parts[0][:50], 'EPosOne'
    return parts[0][:50], ' '.join(parts[1:])[:50]


def _enable_eposone_module(organization_id: int) -> None:
    """Legacy Connected/portal. Standalone /start NO debe habilitar módulo ops."""
    _ = organization_id
    return


def _issue_install_code(organization_id: int, business_name: str) -> dict[str, Any]:
    """DEPRECATED — provisioning Connected. Standalone no lo usa."""
    _ = (organization_id, business_name)
    return {
        'code': None,
        'kind': None,
        'register_ref': None,
        'branch_ref': None,
        'pos_ref': None,
    }


def _commercial_shell_org_name(*, person_name: str, email: str) -> str:
    """LEGACY — cascarón P0. Ya no se usa en complete_start."""
    person = (person_name or '').strip() or (email or '').split('@')[0] or 'Cliente'
    return f'Cliente EPosOne — {person}'[:200]


def complete_start(
    *,
    full_name: str,
    email: str,
    password: str,
    business_name: str,
    business_type: str,
    country: str | None,
    plan_code: str,
    accept_terms: bool,
    accept_privacy: bool,
    accept_eula: bool,
    ip_address: str | None = None,
    public_base: str | None = None,
    phone: str | None = None,
    attribution: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Registro comercial Standalone bajo compañía ETS (ADR-031).

    Expediente: Contact ETS + Customer + Contrato (precio/aceptación) + atribución
    + Suscripción + Licencia. NO crea Org operativa del comprador (ADR-033).
    """
    from models.ets_commercial_contract import EtsCommercialContract
    from models.saas import SaasOrganization
    from models.users import User
    from nodeone.core.db import db
    from nodeone.core.platform.commercial_registration import (
        ensure_customer_and_contract,
        link_subscription_to_contract,
    )
    from nodeone.core.platform.ets_provider import ets_provider_organization_id
    from nodeone.core.platform.standalone_expediente import (
        apply_contract_commercial_terms,
        ensure_attribution,
        ensure_standalone_contact,
    )

    name = (full_name or '').strip()
    mail = (email or '').strip().lower()
    pwd = password or ''
    biz = (business_name or '').strip()
    phone_n = (phone or '').strip() or None
    btype = normalize_business_type(business_type) if business_type else 'other'
    ctry = (country or '').strip() or DEFAULT_COUNTRY
    plan = STANDALONE_PLAN
    _ = plan_code
    attr_in = dict(attribution or {})

    if not name or not mail or not pwd:
        raise StartAssistantError(
            'validation_error',
            'Revisa los campos marcados e intenta de nuevo.',
        )
    if len(pwd) < 8:
        raise StartAssistantError(
            'validation_error',
            'La contraseña debe tener al menos 8 caracteres.',
        )
    if not (accept_terms and accept_privacy and accept_eula):
        raise StartAssistantError(
            'legal_required',
            'Debes aceptar Términos, Privacidad y EULA para continuar.',
        )
    if User.query.filter_by(email=mail).first() is not None:
        raise StartAssistantError(
            'email_exists',
            'Ya existe un acceso con este correo. Inicia sesión o recupera tu contraseña.',
            http_status=409,
        )

    provider_id = ets_provider_organization_id()
    provider = SaasOrganization.query.get(int(provider_id))
    if provider is None:
        raise StartAssistantError(
            'provider_missing',
            'No está configurada la compañía ETS. Contactá a soporte.',
            http_status=500,
        )

    first_name, last_name = _split_display_name(name)

    try:
        contact = ensure_standalone_contact(
            provider_organization_id=int(provider.id),
            full_name=name,
            email=mail,
            phone=phone_n,
            country=ctry,
            intended_business_name=biz or None,
        )
        user = User(
            email=mail,
            first_name=first_name,
            last_name=last_name,
            country=ctry[:100],
            organization_id=int(provider.id),
            is_admin=False,
            email_verified=False,
            is_active=True,
        )
        if hasattr(user, 'linked_contact_id'):
            user.linked_contact_id = int(contact.id)
        user.set_password(pwd)
        db.session.add(user)
        # Un solo commit: evita contacto/customer huérfanos si falla el user.
        db.session.commit()
    except StartAssistantError:
        raise
    except Exception as exc:
        db.session.rollback()
        raise StartAssistantError(
            'prepare_failed',
            'No pudimos crear el acceso. Intenta nuevamente.',
            http_status=500,
        ) from exc

    legal_meta = _record_legal_metadata(
        organization_id=int(provider.id),
        user_id=int(user.id),
        accepted={'terms': True, 'privacy': True, 'eula': True},
        plan_code=plan,
        ip_address=ip_address,
    )

    try:
        commercial = ensure_customer_and_contract(
            organization_id=int(provider.id),
            user_id=int(user.id),
            display_name=name,
            email=mail,
            country=ctry,
            product_code=PRODUCT_CODE,
            plan_code=plan,
            source='eposone_start_standalone',
            phone=phone_n,
            contact_id=int(contact.id),
            metadata={
                'provider_organization_id': int(provider.id),
                'intended_business_name': biz or None,
                'business_type': btype,
                'legal_acceptance': legal_meta,
                'contact_id': int(contact.id),
                'note': 'Cliente comercial ETS. Negocio operativo en EP1 (ADR-033).',
            },
        )
        contract = EtsCommercialContract.query.get(int(commercial['contract_id']))
        if contract is not None:
            apply_contract_commercial_terms(
                contract=contract,
                plan_code=plan,
                user_id=int(user.id),
                contract_type='electronic',
                terms_version='start-legal-v1',
                billing_period='monthly',
                implementation_mode='self_serve',
            )
            db.session.commit()
        ensure_attribution(
            provider_organization_id=int(provider.id),
            customer_id=int(commercial['customer_id']),
            contract_id=int(commercial['contract_id']),
            channel=attr_in.get('channel') or 'web',
            source_detail=attr_in.get('source_detail') or attr_in.get('source') or 'eposone_start',
            campaign=attr_in.get('campaign') or attr_in.get('utm_campaign'),
            referral_code=attr_in.get('referral_code'),
            advisor_user_id=attr_in.get('advisor_user_id'),
            utm_source=attr_in.get('utm_source'),
            utm_medium=attr_in.get('utm_medium'),
            utm_campaign=attr_in.get('utm_campaign'),
            utm_content=attr_in.get('utm_content'),
            utm_term=attr_in.get('utm_term'),
            landing_url=attr_in.get('landing_url') or (public_base or '') + '/start',
        )
        db.session.commit()
    except Exception as exc:
        raise StartAssistantError(
            'prepare_failed',
            'No pudimos completar el registro comercial. Tu acceso quedó guardado. Intenta nuevamente.',
            http_status=500,
        ) from exc

    customer_id = int(commercial['customer_id'])
    grace_ends = datetime.utcnow() + timedelta(days=STANDALONE_GRACE_DAYS)
    try:
        sub_info = _ensure_subscription_and_entitlement(
            organization_id=int(provider.id),
            user_id=int(user.id),
            plan_code=plan,
            legal_meta=legal_meta,
            business_type=btype,
            country=ctry,
            customer_id=customer_id,
        )
        link_subscription_to_contract(
            organization_id=int(provider.id),
            product_code=PRODUCT_CODE,
            contract_id=int(commercial['contract_id']),
            customer_id=customer_id,
        )
        sub_info['contract_id'] = commercial['contract_id']
        sub_info['contract_number'] = commercial['contract_number']
        sub_info['modality'] = 'standalone'
        sub_info['grace_days'] = STANDALONE_GRACE_DAYS
        sub_info['grace_ends_at'] = grace_ends.isoformat() + 'Z'
        sub_info['customer_id'] = customer_id
    except Exception as exc:
        raise StartAssistantError(
            'prepare_failed',
            'No pudimos completar este paso. Tu información está guardada. Intenta nuevamente.',
            http_status=500,
        ) from exc

    activation_info = None
    try:
        from nodeone.core.platform.activation_service import ActivationService

        activation_info = ActivationService.issue_for_organization_standalone(
            organization_id=int(provider.id),
            contract_id=int(commercial['contract_id']),
            subscription_id=sub_info.get('subscription_id'),
            customer_id=customer_id,
            user_id=int(user.id),
            bound_email=str(user.email or ''),
            ends_at=grace_ends,
            public_base=public_base,
            metadata={
                'source': 'eposone_start_standalone',
                'commercial_modality': 'standalone',
                'plan_code': plan,
                'grace_days': STANDALONE_GRACE_DAYS,
                'customer_id': customer_id,
            },
        )
    except Exception as exc:
        import logging

        logging.getLogger(__name__).exception(
            'eposone_start: activation issue failed customer=%s: %s',
            customer_id,
            exc,
        )
        activation_info = None

    try:
        from nodeone.services.organization_context_resolver import set_pending_initial_organization

        set_pending_initial_organization(int(user.id), int(provider.id))
    except Exception:
        pass

    try:
        from flask_login import current_user, logout_user

        if getattr(current_user, 'is_authenticated', False):
            logout_user()
    except Exception:
        pass

    plan_view = plan_public_view(plan)
    act_code = (activation_info or {}).get('activation_code') or (activation_info or {}).get('manual_code')
    act_token_id = (activation_info or {}).get('token_id')
    ready_token = None
    try:
        from nodeone.modules.eposone_start.ready_session import issue_ready_token

        ready_token = issue_ready_token(
            user_id=int(user.id),
            organization_id=int(provider.id),
            activation_token_id=int(act_token_id) if act_token_id else None,
            customer_id=customer_id,
        )
    except Exception:
        ready_token = None

    verification_sent, verification_err = False, None
    try:
        from nodeone.services.customer_registration_email import (
            send_customer_registration_info_email,
        )

        ok_mail = send_customer_registration_info_email(
            to_email=user.email,
            display_name=name,
            organization_id=int(provider.id),
            user=user,
            product_code='eposone',
            plan_code=plan_code,
            related_id=customer_id,
            include_verification=True,
            include_payment_methods=True,
        )
        verification_sent = bool(ok_mail)
        if not ok_mail:
            verification_err = 'No se pudo enviar el correo de registro'
    except Exception as exc:
        verification_err = str(exc).strip()[:300] or 'Error al enviar el correo de registro'

    email_verified = bool(getattr(user, 'email_verified', False))
    checks = [
        'Cliente comercial ETS registrado',
        'Suscripción Standalone con 7 días de gracia',
        'Te enviamos un correo para verificar' if verification_sent else 'No pudimos enviar el correo de verificación',
        'Código de activación listo tras verificar',
    ]

    return {
        'ok': True,
        'organization_id': int(provider.id),
        'organization_name': provider.name,
        'provider_organization_id': int(provider.id),
        'commercial_shell': False,
        'user_id': int(user.id),
        'email': user.email,
        'business_type': btype,
        'intended_business_name': biz or None,
        'country': ctry,
        'plan': plan_view,
        'requires_email_verification': not email_verified,
        'email_verified': email_verified,
        'verification_email_sent': verification_sent,
        'verification_email_error': verification_err,
        'ready_token': ready_token,
        'commercial': {
            'customer_id': customer_id,
            'contract_id': commercial['contract_id'],
            'contract_number': commercial['contract_number'],
            'modality': 'standalone',
            'contact_id': int(contact.id),
            'contract_type': 'electronic',
            'implementation_mode': 'self_serve',
        },
        'subscription': sub_info,
        'implementation': {
            'status': 'deferred_to_ep1',
            'ops_tree_created': False,
            'message': 'La configuración del negocio se hace en la app EPosOne tras activar.',
            'adr': 'ADR-033',
        },
        'activation': activation_info if email_verified else None,
        'installation': {
            'code': act_code if email_verified else None,
            'kind': 'activation_code' if act_code else None,
            'register_ref': None,
            'legacy_provisioning_code': None,
            'message': (
                'Después de verificar tu correo te enviamos el código de activación y el enlace de descarga.'
                if not email_verified
                else 'Descargá EPosOne e introducí tu correo y código de activación en la app.'
            ),
            'cashier': {
                'display_name': None,
                'pin': None,
                'message': 'El cajero se crea en el asistente local de la app (ADR-033).',
            },
        },
        'play_store_url': play_store_url(),
        'download_cta_label': download_cta_label(),
        'session': {'logged_in': False},
        'flow': 'standalone',
        'step': 'awaiting_email_verification' if not email_verified else 'ready_to_install',
        'wow': {
            'title': 'Revisá tu correo',
            'subtitle': (
                f'Te enviamos un enlace a {user.email}. Verificá tu correo para recibir el código e instalar EPosOne.'
                if not email_verified
                else 'Tu EPosOne Standalone está listo para instalar.'
            ),
            'checks': checks,
        },
    }



def _record_legal_metadata(
    *,
    organization_id: int,
    user_id: int,
    accepted: dict[str, bool],
    plan_code: str,
    ip_address: str | None,
) -> dict[str, Any]:
    evidence = {
        'accepted_at': datetime.utcnow().replace(microsecond=0).isoformat() + 'Z',
        'ip_address': ip_address,
        'plan_code': plan_code,
        'slugs': [k for k, v in accepted.items() if v],
        'source': 'eposone_start_assistant',
    }
    try:
        from _app.modules.policies.repository import get_policy_by_slug, record_acceptance

        for slug in evidence['slugs']:
            policy = get_policy_by_slug(slug, active_only=True)
            if policy is None:
                continue
            version = getattr(policy, 'version', None) or '1'
            try:
                record_acceptance(int(user_id), int(policy.id), version, ip_address=ip_address)
            except Exception:
                pass
    except Exception:
        pass
    return evidence


def _ensure_subscription_and_entitlement(
    *,
    organization_id: int,
    user_id: int,
    plan_code: str,
    legal_meta: dict[str, Any],
    business_type: str,
    country: str,
    customer_id: int | None = None,
) -> dict[str, Any]:
    from nodeone.core.platform.subscription_registry import SubscriptionRegistry

    plan = get_commercial_plan(plan_code)
    trial_days = int(plan.get('trial_days') or 0)
    metadata = {
        'source': 'eposone_start_assistant',
        'plan_code': plan_code,
        'business_type': business_type,
        'country': country,
        'legal_acceptance': legal_meta,
        'customer_id': int(customer_id) if customer_id else None,
    }
    if trial_days > 0:
        ends = datetime.utcnow() + timedelta(days=trial_days)
        rec = SubscriptionRegistry.create_trial(
            int(organization_id),
            PRODUCT_CODE,
            ends,
            user_id=int(user_id),
            metadata=metadata,
            customer_id=int(customer_id) if customer_id else None,
        )
        status = 'trial'
        activation_label = f'Trial de {trial_days} días iniciado'
    else:
        rec = SubscriptionRegistry.activate(
            int(organization_id),
            PRODUCT_CODE,
            user_id=int(user_id),
        )
        status = 'active'
        activation_label = 'Plan activado'
        try:
            from models.ets_product_subscription import EtsProductSubscription
            from nodeone.core.db import db
            import json

            if customer_id:
                row = EtsProductSubscription.query.filter_by(
                    customer_id=int(customer_id),
                    product_code=PRODUCT_CODE,
                ).first()
            else:
                row = EtsProductSubscription.query.filter_by(
                    organization_id=int(organization_id),
                    product_code=PRODUCT_CODE,
                ).first()
            if row is not None and metadata:
                if customer_id:
                    row.customer_id = int(customer_id)
                row.metadata_json = json.dumps(metadata, ensure_ascii=False)
                db.session.commit()
        except Exception:
            pass

    # Entitlement org-level Connected no aplica a clientes Standalone bajo ETS;
    # la licencia de activación es el gate hacia EP1.
    return {
        'subscription_id': getattr(rec, 'id', None),
        'status': status,
        'activation_label': activation_label,
        'trial_days': trial_days,
        'customer_id': int(customer_id) if customer_id else None,
    }


def ready_status(*, ready_token: str, public_base: str | None = None) -> dict[str, Any]:
    """Solo lectura: ¿email verificado? ¿código listo? No envía correo (evita solape con verify)."""
    from models.ets_activation_license import EtsActivationLicense
    from models.ets_activation_token import EtsActivationToken
    from models.users import User
    from nodeone.core.platform.activation_service import ActivationService
    from nodeone.modules.eposone_start.ready_session import load_ready_token

    try:
        payload = load_ready_token(ready_token)
    except ValueError as exc:
        raise StartAssistantError(str(exc), 'Sesión de instalación inválida o vencida.', http_status=401) from exc

    user = User.query.get(int(payload['uid']))
    if user is None:
        raise StartAssistantError('ready_token_invalid', 'Sesión de instalación inválida.', http_status=401)

    verified = bool(getattr(user, 'email_verified', False))
    out: dict[str, Any] = {
        'ok': True,
        'email': user.email,
        'email_verified': verified,
        'requires_email_verification': not verified,
        'organization_id': int(payload['oid']),
        'user_id': int(user.id),
        'play_store_url': play_store_url(),
        'download_cta_label': download_cta_label(),
        'flow': 'standalone',
        'step': 'awaiting_email_verification' if not verified else 'ready_to_install',
    }
    if not verified:
        out['activation'] = None
        out['ready_email_sent'] = False
        out['wow'] = {
            'title': 'Revisá tu correo',
            'subtitle': (
                f'Te enviamos un enlace a {user.email}. '
                'Confirmá tu correo para ver el código de activación aquí.'
            ),
        }
        return out

    activation = None
    aid = payload.get('aid')
    cid = payload.get('cid')
    if aid:
        tok = EtsActivationToken.query.get(int(aid))
        if tok is not None and int(tok.organization_id) == int(payload['oid']):
            lic = EtsActivationLicense.query.get(int(tok.license_id))
            if lic is not None:
                if cid and getattr(lic, 'customer_id', None) and int(lic.customer_id) != int(cid):
                    lic = None
                if lic is not None:
                    activation = ActivationService._token_public(tok, lic, public_base=public_base)

    out['activation'] = activation
    out['ready_email_sent'] = standalone_ready_email_already_sent(int(user.id))
    act_code = (activation or {}).get('activation_code') or (activation or {}).get('manual_code')
    out['installation'] = {
        'kind': 'activation_code' if act_code else None,
        'code': act_code,
        'message': 'Descargá EPosOne. En la app introducí tu correo y el código de activación.',
    }
    out['wow'] = {
        'title': 'Tu EPosOne está listo',
        'subtitle': 'Descargá la app e introducí tu correo y código de activación.',
        'checks': ['Correo verificado', 'Código de activación listo', 'Listo para instalar'],
    }
    return out


def standalone_ready_email_already_sent(user_id: int) -> bool:
    """Idempotencia: un solo mail 'listo' por usuario (post-verify)."""
    try:
        from models.communications import EmailLog

        row = (
            EmailLog.query.filter_by(
                recipient_id=int(user_id),
                email_type='eposone_ready_install',
                status='sent',
            )
            .order_by(EmailLog.id.desc())
            .first()
        )
        return row is not None
    except Exception:
        return False


def send_standalone_ready_email(
    *,
    user,
    organization_name: str,
    activation: dict[str, Any],
) -> bool:
    """Único correo post-verify: código + APK. No usar desde ready-status (solo lectura)."""
    try:
        from app import apply_email_config_from_db, email_service
        from email_templates import get_eposone_ready_install_email

        try:
            apply_email_config_from_db()
        except Exception:
            pass
        if not email_service:
            return False
        code = str(activation.get('activation_code') or activation.get('manual_code') or '') or None
        apk = str(activation.get('apk_url') or activation.get('app_link') or '')
        html = get_eposone_ready_install_email(
            user,
            app_link=apk,
            apk_url=apk,
            business_name=organization_name,
            activation_code=code,
            manual_code=code,
            organization_name='EPosOne',
        )
        return bool(
            email_service.send_email(
                subject='Tu EPosOne está listo',
                recipients=[user.email],
                html_content=html,
                email_type='eposone_ready_install',
                related_entity_type='user',
                related_entity_id=int(user.id),
                recipient_id=int(user.id),
                recipient_name=f'{user.first_name} {user.last_name}',
            )
        )
    except Exception:
        return False


def ensure_standalone_ready_email_sent(
    *,
    user,
    organization_name: str,
    activation: dict[str, Any],
) -> bool:
    """Único punto de envío del mail de código Standalone (idempotente)."""
    if standalone_ready_email_already_sent(int(user.id)):
        return True
    return bool(
        send_standalone_ready_email(
            user=user,
            organization_name=organization_name,
            activation=activation,
        )
    )


def _send_registration_verification_email(user) -> tuple[bool, str | None]:
    """Misma secuencia que registro web: apply SMTP + send_verification_email."""
    from app import apply_email_config_from_db, send_verification_email

    try:
        apply_email_config_from_db()
    except Exception:
        pass
    try:
        # brand solo cambia asunto/etiqueta; el motor es el de registro.
        return send_verification_email(user, brand='eposone')
    except Exception as exc:
        return False, str(exc).strip()[:300] or 'Error al enviar el correo de verificación.'


def resend_standalone_verification(*, ready_token: str) -> dict[str, Any]:
    """Reenvío por la misma vía que el registro (no camino SMTP paralelo)."""
    from models.users import User
    from nodeone.modules.eposone_start.ready_session import load_ready_token

    try:
        payload = load_ready_token(ready_token)
    except ValueError as exc:
        raise StartAssistantError(str(exc), 'Sesión de instalación inválida o vencida.', http_status=401) from exc

    user = User.query.get(int(payload['uid']))
    if user is None:
        raise StartAssistantError('ready_token_invalid', 'Sesión de instalación inválida.', http_status=401)
    if bool(getattr(user, 'email_verified', False)):
        return {
            'ok': True,
            'already_verified': True,
            'email': user.email,
            'message': 'Tu correo ya está verificado.',
        }
    ok, err = _send_registration_verification_email(user)
    if not ok:
        raise StartAssistantError(
            'email_send_failed',
            err or 'No pudimos reenviar el correo. Intentá de nuevo en unos minutos.',
            http_status=502,
        )
    return {
        'ok': True,
        'already_verified': False,
        'email': user.email,
        'verification_email_sent': True,
        'message': f'Reenviamos el enlace de verificación a {user.email}.',
    }


def deliver_standalone_ready_after_verify(
    *,
    user,
    organization_id: int,
    public_base: str | None = None,
) -> dict[str, Any]:
    """Tras verify: asegurar activación + mail de código (idempotente) + ready_token."""
    from models.ets_activation_license import EtsActivationLicense
    from models.ets_activation_token import EtsActivationToken
    from models.ets_commercial_customer import EtsCommercialCustomer
    from nodeone.core.platform.activation_service import ActivationService
    from nodeone.modules.eposone_start.ready_session import issue_ready_token

    mail = (getattr(user, 'email', None) or '').strip().lower()
    customer = EtsCommercialCustomer.query.filter_by(
        organization_id=int(organization_id),
        email=mail,
    ).first()
    if customer is None and getattr(user, 'id', None):
        customer = EtsCommercialCustomer.query.filter_by(primary_user_id=int(user.id)).first()
    customer_id = int(customer.id) if customer is not None else None
    display = (
        (customer.display_name if customer is not None else None)
        or f'{getattr(user, "first_name", "") or ""}'.strip()
        or 'EPosOne'
    )

    activation = None
    tok = None
    if customer_id:
        lic = (
            EtsActivationLicense.query.filter_by(
                organization_id=int(organization_id),
                customer_id=customer_id,
                modality='standalone',
            )
            .filter(EtsActivationLicense.status.in_(('issued', 'active')))
            .order_by(EtsActivationLicense.id.desc())
            .first()
        )
        if lic is not None:
            tok = (
                EtsActivationToken.query.filter_by(license_id=int(lic.id), status='active')
                .order_by(EtsActivationToken.id.desc())
                .first()
            )
            if tok is not None:
                activation = ActivationService._token_public(tok, lic, public_base=public_base)

    if activation is None:
        try:
            activation = ActivationService.issue_for_organization_standalone(
                organization_id=int(organization_id),
                customer_id=customer_id,
                user_id=int(user.id),
                bound_email=mail,
                public_base=public_base,
                metadata={
                    'source': 'eposone_verify_email',
                    'grace_days': STANDALONE_GRACE_DAYS,
                    'customer_id': customer_id,
                },
            )
            tok_id = activation.get('token_id')
            tok = EtsActivationToken.query.get(int(tok_id)) if tok_id else None
        except Exception:
            activation = None
            tok = None

    email_sent = False
    if activation is not None:
        email_sent = ensure_standalone_ready_email_sent(
            user=user,
            organization_name=str(display),
            activation=activation,
        )

    if customer_id:
        try:
            from nodeone.core.platform.standalone_expediente import mark_customer_active

            mark_customer_active(int(customer_id))
        except Exception:
            pass

    ready_token = None
    try:
        ready_token = issue_ready_token(
            user_id=int(user.id),
            organization_id=int(organization_id),
            activation_token_id=int(tok.id) if tok is not None else None,
            customer_id=customer_id,
        )
    except Exception:
        ready_token = None

    return {
        'email_sent': email_sent,
        'ready_token': ready_token,
        'activation': activation,
    }

