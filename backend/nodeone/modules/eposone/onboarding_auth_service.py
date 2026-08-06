"""Onboarding Login V1 — auth usuario EN1 + contexto de instalación (ADR-027)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from flask import current_app
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

_ONBOARDING_SALT = 'eposone-onboarding-v1'
_TOKEN_MAX_AGE_SEC = 12 * 3600  # 12 h


class OnboardingAuthError(Exception):
    def __init__(self, code: str, http_status: int = 400):
        super().__init__(code)
        self.code = code
        self.http_status = http_status


def _serializer() -> URLSafeTimedSerializer:
    secret = current_app.config.get('SECRET_KEY') or current_app.secret_key
    if not secret:
        raise OnboardingAuthError('server_misconfigured', 500)
    return URLSafeTimedSerializer(str(secret), salt=_ONBOARDING_SALT)


def issue_access_token(*, user_id: int, organization_id: int | None = None) -> tuple[str, int]:
    payload = {'uid': int(user_id), 'oid': int(organization_id) if organization_id else None}
    token = _serializer().dumps(payload)
    return token, _TOKEN_MAX_AGE_SEC


def parse_access_token(token: str) -> dict[str, Any]:
    raw = (token or '').strip()
    if not raw:
        raise OnboardingAuthError('auth_required', 401)
    try:
        data = _serializer().loads(raw, max_age=_TOKEN_MAX_AGE_SEC)
    except SignatureExpired as exc:
        raise OnboardingAuthError('token_expired', 401) from exc
    except BadSignature as exc:
        raise OnboardingAuthError('invalid_token', 401) from exc
    try:
        uid = int(data.get('uid') or 0)
    except (TypeError, ValueError) as exc:
        raise OnboardingAuthError('invalid_token', 401) from exc
    if uid < 1:
        raise OnboardingAuthError('invalid_token', 401)
    oid = data.get('oid')
    try:
        oid_i = int(oid) if oid is not None else None
    except (TypeError, ValueError):
        oid_i = None
    return {'user_id': uid, 'organization_id': oid_i}


def authenticate_bearer(authorization_header: str | None) -> dict[str, Any]:
    header = (authorization_header or '').strip()
    if not header.lower().startswith('bearer '):
        raise OnboardingAuthError('auth_required', 401)
    return parse_access_token(header[7:].strip())


def _user_can_install(user, organization_id: int) -> bool:
    if getattr(user, 'is_admin', False):
        return True
    from models.users import UserOrganization

    row = UserOrganization.query.filter_by(
        user_id=int(user.id),
        organization_id=int(organization_id),
        status='active',
    ).first()
    if row is None:
        return False
    role = (getattr(row, 'role', None) or '').strip().lower()
    if role in ('owner', 'admin', 'manager'):
        return True
    # Dueño legacy / admin tenant
    if bool(getattr(user, 'is_org_admin', False) or getattr(user, 'is_organization_admin', False)):
        return True
    try:
        if int(getattr(user, 'organization_id', 0) or 0) == int(organization_id):
            return True
    except (TypeError, ValueError):
        pass
    return False


def _subscription_block(organization_id: int) -> dict[str, Any]:
    from nodeone.core.platform.subscription_registry import SubscriptionRegistry

    rec = SubscriptionRegistry.get_for_tenant_product(
        int(organization_id),
        'eposone',
        scope_organization_id=int(organization_id),
    )
    if rec is None:
        return {
            'product_code': 'eposone',
            'status': 'none',
            'entitled': False,
            'trial_ends_at': None,
            'starts_at': None,
            'ends_at': None,
        }
    return {
        'product_code': 'eposone',
        'status': str(rec.status or '').lower(),
        'entitled': bool(rec.is_entitled),
        'trial_ends_at': rec.trial_ends_at.isoformat() if rec.trial_ends_at else None,
        'starts_at': rec.starts_at.isoformat() if rec.starts_at else None,
        'ends_at': rec.ends_at.isoformat() if rec.ends_at else None,
    }


def _org_resources(organization_id: int) -> dict[str, Any]:
    from nodeone.core.master.constants import (
        ORG_UNIT_TYPE_BRANCH,
        ORG_UNIT_TYPE_POS,
        ORG_UNIT_TYPE_REGISTER,
    )
    from nodeone.core.platform.commercial_plans import commercial_context_for_org
    from nodeone.core.services.org_unit import OrgUnitService
    from nodeone.modules.eposone.device_provisioning import DeviceProvisioningService
    from nodeone.modules.eposone.register_license_service import RegisterLicenseService

    oid = int(organization_id)
    commercial = commercial_context_for_org(oid, product_code='eposone')
    subscription = _subscription_block(oid)

    branches = OrgUnitService.list_units(oid, unit_type=ORG_UNIT_TYPE_BRANCH)
    pos_units = OrgUnitService.list_units(oid, unit_type=ORG_UNIT_TYPE_POS)
    registers = OrgUnitService.list_units(oid, unit_type=ORG_UNIT_TYPE_REGISTER)
    pos_by_id = {int(p.id): p for p in pos_units}
    branch_by_id = {int(b.id): b for b in branches}

    devices = DeviceProvisioningService.list_devices(oid, limit=200)
    device_rows: list[dict[str, Any]] = []
    for d in devices:
        device_rows.append(
            {
                'device_uuid': str(d.terminal_ref),
                'device_label': d.device_label,
                'status': str(d.status or ''),
                'register_ref': d.register_ref,
                'branch_ref': d.branch_ref,
                'pos_ref': d.pos_ref,
                'app_version': d.app_version,
                'last_seen_at': d.last_seen_at.isoformat() if d.last_seen_at else None,
                'installation_ready_at': (
                    d.installation_ready_at.isoformat()
                    if getattr(d, 'installation_ready_at', None)
                    else None
                ),
            }
        )

    register_rows: list[dict[str, Any]] = []
    licenses: list[dict[str, Any]] = []
    for reg in registers:
        ref = str(reg.unit_ref)
        pos = pos_by_id.get(int(reg.parent_id)) if reg.parent_id is not None else None
        branch = None
        if pos is not None and pos.parent_id is not None:
            branch = branch_by_id.get(int(pos.parent_id))
        active_code = DeviceProvisioningService.get_active_code_for_register(oid, ref)
        snap = RegisterLicenseService.snapshot(oid, ref)
        register_rows.append(
            {
                'register_ref': ref,
                'name': str(reg.name or ref),
                'status': str(getattr(reg, 'status', None) or 'active'),
                'pos_ref': pos.unit_ref if pos is not None else None,
                'pos_name': pos.name if pos is not None else None,
                'branch_ref': branch.unit_ref if branch is not None else None,
                'branch_name': branch.name if branch is not None else None,
                'has_active_code': active_code is not None,
                'active_code_expires_at': (
                    active_code.expires_at.isoformat()
                    if active_code is not None and active_code.expires_at
                    else None
                ),
                # Código en claro solo si hay uno activo (APK Camino C); no loguear.
                'active_provisioning_code': (
                    str(active_code.code) if active_code is not None else None
                ),
            }
        )
        licenses.append(
            {
                'register_ref': ref,
                'license_type': snap.license_type,
                'status': snap.status,
                'plan_code': snap.plan_code,
                'can_operate': snap.can_operate,
                'commercial_ui': snap.commercial_ui,
                'expires_at': snap.expires_at.isoformat() if snap.expires_at else None,
                'days_remaining': snap.days_remaining,
            }
        )

    return {
        'commercial': commercial,
        'subscription': subscription,
        'modality': commercial.get('modality'),
        'plan_code': commercial.get('plan_code'),
        'branches': [
            {'branch_ref': b.unit_ref, 'name': b.name, 'status': getattr(b, 'status', None)}
            for b in branches
        ],
        'pos': [
            {'pos_ref': p.unit_ref, 'name': p.name, 'status': getattr(p, 'status', None)}
            for p in pos_units
        ],
        'registers': register_rows,
        'devices': device_rows,
        'licenses': licenses,
    }


def build_onboarding_session_payload(
    user,
    *,
    organization_id: int | None = None,
) -> dict[str, Any]:
    from app import SaasOrganization
    from nodeone.services.user_organization import active_organization_ids_for_user

    oid_set = active_organization_ids_for_user(user)
    orgs_out: list[dict[str, Any]] = []
    for oid in sorted(oid_set):
        org = SaasOrganization.query.filter_by(id=int(oid)).first()
        if org is None or not getattr(org, 'is_active', True):
            continue
        can_issue = _user_can_install(user, int(oid))
        block = {
            'organization_id': int(oid),
            'name': str(org.name or ''),
            'can_issue_provisioning_code': can_issue,
        }
        # Detalle completo solo para la org seleccionada (o la única).
        include_detail = organization_id is not None and int(organization_id) == int(oid)
        if organization_id is None and len(oid_set) == 1:
            include_detail = True
        if include_detail:
            if not can_issue and int(oid) not in oid_set:
                raise OnboardingAuthError('org_forbidden', 403)
            resources = _org_resources(int(oid))
            block.update(resources)
            block['subscription'] = resources['subscription']
            block['modality'] = resources['modality']
            block['plan_code'] = resources['plan_code']
        else:
            # Resumen mínimo siempre
            sub = _subscription_block(int(oid))
            from nodeone.core.platform.commercial_plans import commercial_context_for_org

            commercial = commercial_context_for_org(int(oid), product_code='eposone')
            block['subscription'] = sub
            block['modality'] = commercial.get('modality')
            block['plan_code'] = commercial.get('plan_code')
        orgs_out.append(block)

    if organization_id is not None:
        wanted = int(organization_id)
        if wanted not in oid_set:
            raise OnboardingAuthError('org_forbidden', 403)
        # Filtrar a una org con detalle
        detailed = [o for o in orgs_out if int(o['organization_id']) == wanted]
        if not detailed:
            raise OnboardingAuthError('org_forbidden', 403)
        orgs_out = detailed
        # Asegurar recursos si faltaron
        if 'registers' not in orgs_out[0]:
            if not _user_can_install(user, wanted):
                raise OnboardingAuthError('org_forbidden', 403)
            resources = _org_resources(wanted)
            orgs_out[0].update(resources)

    selected = orgs_out[0] if len(orgs_out) == 1 else None
    next_action = 'select_organization'
    if selected is not None:
        sub = selected.get('subscription') or {}
        if not sub.get('entitled'):
            next_action = 'subscription_inactive'
        elif any(r.get('has_active_code') for r in (selected.get('registers') or [])):
            next_action = 'provision_with_code'
        elif any(d.get('status') == 'active' for d in (selected.get('devices') or [])):
            next_action = 'restore_or_cashier'
        else:
            next_action = 'issue_code'

    return {
        'schema_version': 1,
        'user_id': int(user.id),
        'email': str(getattr(user, 'email', '') or ''),
        'full_name': (
            f"{getattr(user, 'first_name', '') or ''} {getattr(user, 'last_name', '') or ''}"
        ).strip()
        or None,
        'organizations': orgs_out,
        'organization_count': len(orgs_out),
        'selected_organization_id': (
            int(selected['organization_id']) if selected is not None else None
        ),
        'next_action': next_action,
        'generated_at': datetime.utcnow().isoformat() + 'Z',
    }


def login_with_password(
    email: str,
    password: str,
    *,
    organization_id: int | None = None,
) -> dict[str, Any]:
    from models.users import User
    from sqlalchemy import func

    mail = (email or '').strip().lower()
    if not mail or not password:
        raise OnboardingAuthError('invalid_credentials', 401)
    user = User.query.filter(func.lower(User.email) == mail).first()
    if user is None or not getattr(user, 'is_active', False):
        raise OnboardingAuthError('invalid_credentials', 401)
    if not user.check_password(password):
        raise OnboardingAuthError('invalid_credentials', 401)

    from nodeone.services.user_organization import active_organization_ids_for_user

    oid_set = active_organization_ids_for_user(user)
    if not oid_set:
        raise OnboardingAuthError('no_organization', 403)
    oid = int(organization_id) if organization_id is not None else None
    if oid is not None and oid not in oid_set:
        raise OnboardingAuthError('org_forbidden', 403)
    if oid is None and len(oid_set) == 1:
        oid = next(iter(oid_set))

    token, expires_in = issue_access_token(user_id=int(user.id), organization_id=oid)
    session_payload = build_onboarding_session_payload(user, organization_id=oid)
    return {
        'access_token': token,
        'token_type': 'Bearer',
        'expires_in': expires_in,
        'session': session_payload,
    }


def issue_provisioning_code_for_user(
    user,
    *,
    organization_id: int,
    register_ref: str,
) -> dict[str, Any]:
    from nodeone.modules.eposone.device_provisioning import (
        DeviceProvisioningError,
        DeviceProvisioningService,
    )
    from nodeone.services.user_organization import active_organization_ids_for_user

    oid = int(organization_id)
    if oid not in active_organization_ids_for_user(user):
        raise OnboardingAuthError('org_forbidden', 403)
    if not _user_can_install(user, oid):
        raise OnboardingAuthError('forbidden', 403)
    ref = (register_ref or '').strip()
    if not ref:
        raise OnboardingAuthError('register_ref_required', 400)
    try:
        row = DeviceProvisioningService.issue_code_for_register(oid, register_ref=ref)
    except DeviceProvisioningError as exc:
        raise OnboardingAuthError(exc.code, int(exc.http_status)) from exc
    return {
        'organization_id': oid,
        'register_ref': ref,
        'code': str(row.code),
        'expires_at': row.expires_at.isoformat() if row.expires_at else None,
        'status': str(row.status or 'active'),
    }


def load_user(user_id: int):
    from models.users import User

    user = User.query.filter_by(id=int(user_id)).first()
    if user is None or not getattr(user, 'is_active', False):
        raise OnboardingAuthError('invalid_token', 401)
    return user
