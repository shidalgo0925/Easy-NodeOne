"""Orquestación comercial del Asistente de Inicio EPosOne (ADR-024).

Reutiliza: SaasOrganization, User, SubscriptionRegistry, EntitlementService,
DeviceProvisioningService, SaasOrgModule. No crea motores comerciales paralelos.
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


def play_store_url() -> str:
    return (
        (os.environ.get('NODEONE_EPOSONE_PLAY_STORE_URL') or '').strip()
        or 'https://play.google.com/store/search?q=EPosOne&c=apps'
    )


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
    """Prefer EN1-02 (código por caja); fallback legado org-level."""
    from nodeone.core.master.constants import (
        ORG_UNIT_TYPE_BRANCH,
        ORG_UNIT_TYPE_POS,
        ORG_UNIT_TYPE_REGISTER,
    )
    from nodeone.core.master.org_unit import OrgUnitService
    from nodeone.modules.eposone.device_provisioning import (
        DeviceProvisioningError,
        DeviceProvisioningService,
    )

    suffix = secrets.token_hex(2)
    try:
        branch = OrgUnitService.create(
            int(organization_id),
            unit_ref=f'branch-main-{suffix}',
            name='Principal',
            unit_type=ORG_UNIT_TYPE_BRANCH,
            parent_id=None,
        )
        pos = OrgUnitService.create(
            int(organization_id),
            unit_ref=f'pos-main-{suffix}',
            name='POS 1',
            unit_type=ORG_UNIT_TYPE_POS,
            parent_id=int(branch.id),
        )
        register = OrgUnitService.create(
            int(organization_id),
            unit_ref=f'reg-main-{suffix}',
            name='Caja 1',
            unit_type=ORG_UNIT_TYPE_REGISTER,
            parent_id=int(pos.id),
        )
        row = DeviceProvisioningService.issue_code_for_register(
            int(organization_id),
            register_ref=register.unit_ref,
            label=f'{business_name} · Caja 1',
        )
        return {
            'code': row.code,
            'kind': 'register',
            'register_ref': register.unit_ref,
            'branch_ref': branch.unit_ref,
            'pos_ref': pos.unit_ref,
        }
    except (DeviceProvisioningError, Exception):
        code = DeviceProvisioningService.ensure_provisioning_code(int(organization_id))
        return {
            'code': code,
            'kind': 'organization',
            'register_ref': None,
            'branch_ref': None,
            'pos_ref': None,
        }


def _seed_default_cashier(organization_id: int, display_name: str) -> dict[str, Any]:
    """Cajero inicial + PIN (mostrado una vez en /start). Fallo suave: no aborta el alta."""
    import secrets

    from nodeone.modules.eposone.cashier_service import CashierService

    pin = ''.join(secrets.choice('0123456789') for _ in range(4))
    while pin in ('0000', '1111', '1234'):
        pin = ''.join(secrets.choice('0123456789') for _ in range(4))
    name = (display_name or 'Cajero principal').strip()[:80] or 'Cajero principal'
    try:
        dto = CashierService.create(
            int(organization_id),
            {'display_name': name, 'pin': pin},
        )
        return {
            'cashier_id': int(dto.id),
            'display_name': dto.display_name,
            'pin': pin,
        }
    except Exception:
        return {'cashier_id': None, 'display_name': None, 'pin': None}


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
) -> dict[str, Any]:
    """Crea acceso + org + trial/activación + entitlement + código + cajero inicial.

    No inicia sesión web: el asistente es comercial; el panel BO pide login explícito.
    """
    from models.saas import SaasOrganization
    from models.users import User
    from nodeone.core.db import db
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
        is_admin=True,
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
        sub_info = _ensure_subscription_and_entitlement(
            organization_id=int(org.id),
            user_id=int(user.id),
            plan_code=plan,
            legal_meta=legal_meta,
            business_type=btype,
            country=ctry,
        )
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

    cashier_name = first_name or 'Cajero principal'
    cashier_info = _seed_default_cashier(int(org.id), cashier_name)

    # Sin login_user: evita sesión colgada / branding de otro tenant en el host EPosOne.
    try:
        from flask_login import current_user, logout_user

        if getattr(current_user, 'is_authenticated', False):
            logout_user()
    except Exception:
        pass

    plan_view = plan_public_view(plan)
    checks = [
        'Acceso creado',
        'Negocio preparado',
        sub_info.get('activation_label') or 'Plan listo',
        'Código de instalación listo' if code_info.get('code') else 'Código en preparación',
    ]
    if cashier_info.get('pin'):
        checks.append(
            f"Cajero «{cashier_info.get('display_name') or cashier_name}» · PIN {cashier_info['pin']}"
        )
    else:
        checks.append('Cajero: créalo en el panel EN1 antes de operar')

    return {
        'ok': True,
        'organization_id': int(org.id),
        'organization_name': org.name,
        'user_id': int(user.id),
        'email': user.email,
        'business_type': btype,
        'country': ctry,
        'plan': plan_view,
        'subscription': sub_info,
        'installation': {
            'code': code_info.get('code'),
            'kind': code_info.get('kind'),
            'register_ref': code_info.get('register_ref'),
            'message': (
                'Guarda este código: lo necesitarás al abrir EPosOne en tu dispositivo.'
                if code_info.get('code')
                else 'Tu código se está generando. Espera un momento o actualiza.'
            ),
            'cashier': {
                'display_name': cashier_info.get('display_name'),
                'pin': cashier_info.get('pin'),
                'message': (
                    'Anota el PIN del cajero: lo usarás en la tablet (no es el código de instalación).'
                    if cashier_info.get('pin')
                    else None
                ),
            },
        },
        'play_store_url': play_store_url(),
        'session': {'logged_in': False},
        'wow': {
            'title': '¡Bienvenido a EPosOne!',
            'subtitle': 'Tu negocio ya está preparado. Anota código y PIN; luego inicia sesión solo si vas al panel web.',
            'checks': checks,
        },
    }