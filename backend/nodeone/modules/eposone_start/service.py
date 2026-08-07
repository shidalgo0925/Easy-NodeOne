"""Orquestación comercial del Asistente de Inicio EPosOne (ADR-024 / ADR-031).

Reutiliza: SaasOrganization, User, Cliente/Contrato, SubscriptionRegistry,
EntitlementService, DeviceProvisioningService. Registro ≠ implementación ops.
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
    from models.saas import SaasModule, SaasOrgModule
    from nodeone.core.db import db

    mod = SaasModule.query.filter_by(code=PRODUCT_CODE).first()
    if mod is None:
        return
    link = SaasOrgModule.query.filter_by(
        organization_id=int(organization_id),
        module_id=int(mod.id),
    ).first()
    if link is None:
        db.session.add(
            SaasOrgModule(
                organization_id=int(organization_id),
                module_id=int(mod.id),
                enabled=True,
            )
        )
    else:
        link.enabled = True


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
) -> dict[str, Any]:
    from nodeone.core.platform.entitlement_service import EntitlementService
    from nodeone.core.platform.subscription_registry import SubscriptionRegistry

    plan = get_commercial_plan(plan_code)
    trial_days = int(plan.get('trial_days') or 0)
    metadata = {
        'source': 'eposone_start_assistant',
        'plan_code': plan_code,
        'business_type': business_type,
        'country': country,
        'legal_acceptance': legal_meta,
    }
    if trial_days > 0:
        ends = datetime.utcnow() + timedelta(days=trial_days)
        rec = SubscriptionRegistry.create_trial(
            int(organization_id),
            PRODUCT_CODE,
            ends,
            user_id=int(user_id),
            metadata=metadata,
        )
        status = 'trial'
        activation_label = f'Trial de {trial_days} días iniciado'
    else:
        # Standalone: activación comercial al contratar (Dev: marca ACTIVE sin pasarela).
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

            row = EtsProductSubscription.query.filter_by(
                organization_id=int(organization_id),
                product_code=PRODUCT_CODE,
            ).first()
            if row is not None and metadata:
                import json

                row.metadata_json = json.dumps(metadata, ensure_ascii=False)
                db.session.commit()
        except Exception:
            pass

    EntitlementService.ensure_for_subscription(
        int(organization_id),
        PRODUCT_CODE,
        plan_code=plan_code,
        user_id=int(user_id),
    )
    return {
        'subscription_id': getattr(rec, 'id', None),
        'status': status,
        'activation_label': activation_label,
        'trial_days': trial_days,
    }


def _issue_install_code(organization_id: int, business_name: str) -> dict[str, Any]:
    """Código de instalación a nivel organización (ADR-031: sin árbol ops en registro)."""
    from nodeone.modules.eposone.device_provisioning import DeviceProvisioningService

    _ = business_name  # etiqueta futura; org-level no la requiere
    code = DeviceProvisioningService.ensure_provisioning_code(int(organization_id))
    return {
        'code': code,
        'kind': 'organization',
        'register_ref': None,
        'branch_ref': None,
        'pos_ref': None,
    }


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
) -> dict[str, Any]:
    """Registro comercial: acceso + org + Cliente + Contrato + sub + activación Standalone.

    No crea Sucursal/POS/Caja ni cajero (implementación diferida — ADR-031).
    Emite token ADR-035 modality=standalone (P0 E2E; Connected = ADR-034, fuera de alcance).
    No inicia sesión web: el asistente es comercial; el panel BO pide login explícito.
    """
    from models.saas import SaasOrganization
    from models.users import User
    from nodeone.core.db import db
    from nodeone.core.platform.commercial_registration import (
        ensure_customer_and_contract,
        link_subscription_to_contract,
    )
    from nodeone.services.user_organization import ensure_membership

    name = (full_name or '').strip()
    mail = (email or '').strip().lower()
    pwd = password or ''
    biz = (business_name or '').strip()
    btype = normalize_business_type(business_type)
    ctry = (country or '').strip() or DEFAULT_COUNTRY
    plan = normalize_commercial_plan_code(plan_code)

    if not name or not mail or not pwd or not biz:
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

    first_name, last_name = _split_display_name(name)
    org = SaasOrganization(
        name=biz[:200],
        legal_name=biz[:200],
        subdomain=_unique_subdomain(biz),
        is_active=True,
        registration_policy='invite_only',
        timezone=DEFAULT_TZ,
        fiscal_country=ctry[:120],
        fiscal_email=mail[:200],
    )
    db.session.add(org)
    db.session.flush()

    user = User(
        email=mail,
        first_name=first_name,
        last_name=last_name,
        country=ctry[:100],
        organization_id=int(org.id),
        is_admin=False,
        email_verified=False,
        is_active=True,
    )
    user.set_password(pwd)
    db.session.add(user)
    db.session.flush()

    ensure_membership(int(user.id), int(org.id), role='owner')
    _enable_eposone_module(int(org.id))
    db.session.commit()

    legal_meta = _record_legal_metadata(
        organization_id=int(org.id),
        user_id=int(user.id),
        accepted={'terms': True, 'privacy': True, 'eula': True},
        plan_code=plan,
        ip_address=ip_address,
    )

    try:
        commercial = ensure_customer_and_contract(
            organization_id=int(org.id),
            user_id=int(user.id),
            display_name=name,
            email=mail,
            country=ctry,
            product_code=PRODUCT_CODE,
            plan_code=plan,
            source='eposone_start_assistant',
            metadata={
                'business_name': biz,
                'business_type': btype,
                'legal_acceptance': legal_meta,
            },
        )
    except Exception as exc:
        raise StartAssistantError(
            'prepare_failed',
            'No pudimos completar el registro comercial. Tu acceso quedó guardado. Intenta nuevamente.',
            http_status=500,
        ) from exc

    try:
        sub_info = _ensure_subscription_and_entitlement(
            organization_id=int(org.id),
            user_id=int(user.id),
            plan_code=plan,
            legal_meta=legal_meta,
            business_type=btype,
            country=ctry,
        )
        link_subscription_to_contract(
            organization_id=int(org.id),
            product_code=PRODUCT_CODE,
            contract_id=int(commercial['contract_id']),
        )
        sub_info['contract_id'] = commercial['contract_id']
        sub_info['contract_number'] = commercial['contract_number']
        sub_info['modality'] = commercial['modality']
    except Exception as exc:
        raise StartAssistantError(
            'prepare_failed',
            'No pudimos completar este paso. Tu información está guardada. Intenta nuevamente.',
            http_status=500,
        ) from exc

    try:
        code_info = _issue_install_code(int(org.id), biz)
    except Exception:
        code_info = {
            'code': None,
            'kind': None,
            'register_ref': None,
            'branch_ref': None,
            'pos_ref': None,
        }

    activation_info = None
    try:
        from nodeone.core.platform.activation_service import ActivationService

        # P0 Standalone E2E: siempre emitir token ADR-035 modality=standalone
        # (sin árbol ops). El plan comercial puede ser connected; Connected ops = ADR-034.
        activation_info = ActivationService.issue_for_organization_standalone(
            organization_id=int(org.id),
            contract_id=int(commercial['contract_id']),
            subscription_id=sub_info.get('subscription_id'),
            user_id=int(user.id),
            public_base=public_base,
            metadata={
                'source': 'eposone_start_assistant',
                'commercial_modality': commercial.get('modality'),
                'plan_code': plan,
            },
        )
    except Exception as exc:
        import logging

        logging.getLogger(__name__).exception(
            'eposone_start: activation issue failed org=%s: %s',
            getattr(org, 'id', None),
            exc,
        )
        activation_info = None

    try:
        from nodeone.services.organization_context_resolver import set_pending_initial_organization

        set_pending_initial_organization(int(user.id), int(org.id))
    except Exception:
        pass

    # Sin login_user: evita sesión colgada / branding de otro tenant en el host EPosOne.
    try:
        from flask_login import current_user, logout_user

        if getattr(current_user, 'is_authenticated', False):
            logout_user()
    except Exception:
        pass

    plan_view = plan_public_view(plan)
    act_token = (activation_info or {}).get('token')
    checks = [
        'Acceso creado',
        'Cliente y contrato registrados',
        sub_info.get('activation_label') or 'Plan listo',
        'Token de activación listo' if act_token else (
            'Código de instalación listo' if code_info.get('code') else 'Código en preparación'
        ),
        'Implementación operativa diferida (sin sucursal/caja aún)',
    ]

    return {
        'ok': True,
        'organization_id': int(org.id),
        'organization_name': org.name,
        'user_id': int(user.id),
        'email': user.email,
        'business_type': btype,
        'country': ctry,
        'plan': plan_view,
        'commercial': {
            'customer_id': commercial['customer_id'],
            'contract_id': commercial['contract_id'],
            'contract_number': commercial['contract_number'],
            'modality': commercial['modality'],
        },
        'subscription': sub_info,
        'implementation': {
            'status': 'deferred',
            'ops_tree_created': False,
            'message': (
                'El registro comercial está listo. Sucursal, POS y caja se crean '
                'en la fase de implementación (no en este alta).'
            ),
        },
        'activation': activation_info,
        'installation': {
            'code': act_token or code_info.get('code'),
            'kind': 'activation_token' if act_token else (code_info.get('kind') or 'organization'),
            'register_ref': None,
            'legacy_provisioning_code': code_info.get('code'),
            'message': (
                'Guarda este token de activación: lo usarás al abrir EPosOne (ADR-035).'
                if act_token
                else (
                    'Guarda este código: lo necesitarás al abrir EPosOne en tu dispositivo.'
                    if code_info.get('code')
                    else 'Tu código se está generando. Espera un momento o actualiza.'
                )
            ),
            'cashier': {
                'display_name': None,
                'pin': None,
                'message': (
                    'El cajero se crea en el asistente Standalone (ADR-033) '
                    'o en la implementación Connected.'
                ),
            },
        },
        'play_store_url': play_store_url(),
        'download_cta_label': download_cta_label(),
        'session': {'logged_in': False},
        'wow': {
            'title': '¡Bienvenido a EPosOne!',
            'subtitle': (
                'Tu registro comercial está listo. Anota el token de activación; '
                'la configuración de caja se completa en el asistente de la app.'
                if act_token
                else (
                    'Tu registro comercial está listo. Anota el código de instalación; '
                    'la configuración de caja se completa en la implementación.'
                )
            ),
            'checks': checks,
        },
    }
