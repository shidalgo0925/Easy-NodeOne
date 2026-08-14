"""Provisioning de dispositivos EPosOne — Hito EN1-02 (código = destino).

EN1-01 (código por org + refs en body) queda como compatibilidad legacy.
Contrato oficial: solo device_uuid + metadatos + código de destino.
"""

from __future__ import annotations

import hashlib
import os
import secrets
from datetime import datetime, timedelta
from typing import Any

from models.commercial_core import CorePosTerminal
from models.core_master import CoreOrgUnit
from models.eposone_provisioning import EposoneProvisioningCode
from models.eposone_settings import EposoneSettings
from models.saas import SaasOrganization
from nodeone.core.commerce.constants import POS_TERMINAL_ACTIVE
from nodeone.core.master.constants import (
    ORG_UNIT_POS_TYPES,
    ORG_UNIT_STATUS_ACTIVE,
    ORG_UNIT_TYPE_BRANCH,
    ORG_UNIT_TYPE_REGISTER,
)
EVENT_REGISTERED = 'eposone.device.registered'
EVENT_REPROVISIONED = 'eposone.device.reprovisioned'
EVENT_AUTH_FAILED = 'eposone.device.auth_failed'
EVENT_PROVISION_FAILED = 'eposone.device.provision_failed'
EVENT_CODE_ISSUED = 'eposone.provisioning_code.issued'
EVENT_INSTALLATION_READY = 'eposone.installation.ready'

DEFAULT_TIMEZONE = 'America/Panama'
STATUS_ACTIVE = 'active'
STATUS_REVOKED = 'revoked'
STATUS_USED = 'used'
STATUS_EXPIRED = 'expired'


def _resolve_cash_mode(organization_id: int) -> str:
    from nodeone.modules.eposone.cash_operation_mode import resolve_cash_operation_mode

    return resolve_cash_operation_mode(int(organization_id))


def _audit_publish(organization_id: int, event_type: str, payload: dict[str, Any] | None = None) -> None:
    try:
        from nodeone.core.services.audit import AuditService

        AuditService.publish_domain_event(
            int(organization_id),
            event_type,
            payload,
            source_app_id='eposone',
        )
    except Exception:
        pass


class DeviceProvisioningError(ValueError):
    def __init__(self, code: str, *, http_status: int = 400) -> None:
        super().__init__(code)
        self.code = code
        self.http_status = http_status


def _hash_token(token: str) -> str:
    return hashlib.sha256((token or '').encode('utf-8')).hexdigest()


def _iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    return dt.replace(microsecond=0).isoformat() + 'Z'


def _deploy_environment_label() -> str:
    """Metadato no-gate para bloque installation.deployment."""
    for key in (
        'EPOSONE_DEPLOY_ENV',
        'EASYNODEONE_DEPLOY_ENV',
        'EASYNODEONE_SILO',
        'FLASK_ENV',
    ):
        val = (os.environ.get(key) or '').strip().lower()
        if val:
            return val
    return 'unknown'


def installation_enforcement_enabled() -> bool:
    """C3b — 403 installation_incomplete en cash/orders. Default off (piloto)."""
    raw = (os.environ.get('EPOSONE_ENFORCE_INSTALLATION_READY') or '').strip().lower()
    return raw in {'1', 'true', 'yes', 'on'}


def build_installation_block(
    *,
    now: datetime | None = None,
    ready_acked_at: datetime | None = None,
) -> dict[str, Any]:
    """
    ADR-021 / Installation Lifecycle Contract v1 — bloque aditivo bootstrap.

    Clientes viejos ignoran el objeto. No implica persistencia de estados APK.
    """
    min_app = (os.environ.get('EPOSONE_MIN_APP_VERSION') or '').strip() or None
    when = now or datetime.utcnow()
    enforce = installation_enforcement_enabled()
    return {
        'schema_version': 1,
        'bootstrap_required': True,
        'channel': 'integrated',
        'min_app_version': min_app,
        'min_bootstrap_schema': 1,
        'capabilities': {
            'cash_shifts': True,
            'orders': True,
            'offline': True,
        },
        'sync_policy': {
            'mode': 'bootstrap_then_incremental',
            'catalog_full_on_mismatch': True,
        },
        'deployment': {
            'environment': _deploy_environment_label(),
            'server_time': _iso(when),
        },
        # Observabilidad ACK (C3a) — no es gate de operación por sí solo.
        'ready_acked_at': _iso(ready_acked_at),
        'enforcement': {
            'installation_ready_required': enforce,
        },
    }


def _new_access_token() -> str:
    return secrets.token_urlsafe(32)


def _new_provisioning_code() -> str:
    return secrets.token_urlsafe(12)


class DeviceProvisioningService:
    """Registro / reprovisioning / config — destino resuelto por código (EN1-02)."""

    # --- EN1-02: códigos por Caja ---

    @staticmethod
    def issue_code_for_register(
        organization_id: int,
        *,
        register_ref: str,
        label: str | None = None,
    ) -> EposoneProvisioningCode:
        """Genera código activo para una caja; revoca códigos activos previos de esa caja."""
        from app import db

        oid = int(organization_id)
        reg = DeviceProvisioningService._get_unit(
            oid, register_ref, allowed_types=frozenset({ORG_UNIT_TYPE_REGISTER})
        )
        # Resolver POS y sucursal desde jerarquía parent
        pos = None
        branch = None
        if reg.parent_id is not None:
            pos = CoreOrgUnit.query.filter_by(organization_id=oid, id=int(reg.parent_id)).first()
        if pos is not None and str(pos.unit_type) not in ORG_UNIT_POS_TYPES:
            # parent no es POS: intentar como branch directo (legado)
            if str(pos.unit_type) == ORG_UNIT_TYPE_BRANCH:
                branch = pos
                pos = None
            else:
                pos = None
        if pos is not None and pos.parent_id is not None:
            branch = CoreOrgUnit.query.filter_by(organization_id=oid, id=int(pos.parent_id)).first()
        if pos is None or branch is None or str(branch.unit_type) != ORG_UNIT_TYPE_BRANCH:
            raise DeviceProvisioningError(
                'register_hierarchy_incomplete',
                http_status=400,
            )
        if str(pos.status) != ORG_UNIT_STATUS_ACTIVE or str(branch.status) != ORG_UNIT_STATUS_ACTIVE:
            raise DeviceProvisioningError('destination_inactive', http_status=400)

        # Revocar activos previos de esta caja
        prev = EposoneProvisioningCode.query.filter_by(
            organization_id=oid,
            register_ref=reg.unit_ref,
            status=STATUS_ACTIVE,
        ).all()
        for p in prev:
            p.status = STATUS_REVOKED

        code = _new_provisioning_code()
        # Garantizar unicidad global
        while EposoneProvisioningCode.query.filter_by(code=code).first() is not None:
            code = _new_provisioning_code()

        from nodeone.modules.eposone.register_license_service import RegisterLicenseService

        ttl_min = int(RegisterLicenseService._policy(oid)['provisioning_code_ttl_minutes'] or 30)
        expires_at = datetime.utcnow() + timedelta(minutes=max(1, ttl_min))

        row = EposoneProvisioningCode(
            organization_id=oid,
            branch_ref=branch.unit_ref,
            pos_ref=pos.unit_ref,
            register_ref=reg.unit_ref,
            code=code,
            status=STATUS_ACTIVE,
            label=(label or '').strip() or f'{pos.name} / {reg.name}',
            expires_at=expires_at,
        )
        db.session.add(row)
        db.session.commit()
        _audit_publish(
            oid,
            EVENT_CODE_ISSUED,
            {
                'code_id': int(row.id),
                'branch_ref': row.branch_ref,
                'pos_ref': row.pos_ref,
                'register_ref': row.register_ref,
                'expires_at': expires_at.isoformat(sep=' ', timespec='seconds'),
            },
        )
        return row

    @staticmethod
    def list_codes(organization_id: int, *, active_only: bool = True) -> list[EposoneProvisioningCode]:
        q = EposoneProvisioningCode.query.filter_by(organization_id=int(organization_id))
        if active_only:
            q = q.filter_by(status=STATUS_ACTIVE)
        return q.order_by(EposoneProvisioningCode.created_at.desc()).all()

    @staticmethod
    def get_active_code_for_register(
        organization_id: int, register_ref: str
    ) -> EposoneProvisioningCode | None:
        row = (
            EposoneProvisioningCode.query.filter_by(
                organization_id=int(organization_id),
                register_ref=(register_ref or '').strip(),
                status=STATUS_ACTIVE,
            )
            .order_by(EposoneProvisioningCode.id.desc())
            .first()
        )
        if row is None:
            return None
        if row.expires_at is not None and row.expires_at < datetime.utcnow():
            from app import db

            row.status = STATUS_EXPIRED
            db.session.commit()
            return None
        return row

    @staticmethod
    def resolve_destination_by_code(code: str | None) -> EposoneProvisioningCode:
        provided = (code or '').strip()
        if not provided:
            DeviceProvisioningService._audit_auth_failed(None, reason='provisioning_code_missing')
            raise DeviceProvisioningError('provisioning_code_required', http_status=401)
        row = EposoneProvisioningCode.query.filter_by(code=provided, status=STATUS_ACTIVE).first()
        if row is not None:
            if row.expires_at is not None and row.expires_at < datetime.utcnow():
                from app import db

                row.status = STATUS_EXPIRED
                db.session.commit()
                DeviceProvisioningService._audit_auth_failed(
                    int(row.organization_id), reason='provisioning_code_expired'
                )
                raise DeviceProvisioningError('provisioning_code_expired', http_status=401)
            return row
        # ADR-035 puente: token de activación Connected con register_ref
        bridged = DeviceProvisioningService._bridge_activation_token(provided)
        if bridged is not None:
            return bridged
        DeviceProvisioningService._audit_auth_failed(None, reason='provisioning_code_invalid')
        raise DeviceProvisioningError('provisioning_code_invalid', http_status=401)

    @staticmethod
    def _bridge_activation_token(code: str):
        """Compatibilidad: token ADR-035 Connected actúa como código de destino."""
        from models.ets_activation_license import EtsActivationLicense
        from models.ets_activation_token import EtsActivationToken

        tok = EtsActivationToken.query.filter_by(token=code.strip().upper()).first()
        if tok is None:
            tok = EtsActivationToken.query.filter_by(token=code.strip()).first()
        if tok is None:
            return None
        lic = EtsActivationLicense.query.get(int(tok.license_id))
        if lic is None:
            raise DeviceProvisioningError('license_revoked', http_status=403)
        if str(lic.modality) == 'standalone':
            raise DeviceProvisioningError('modality_mismatch', http_status=409)
        if str(tok.status) not in ('active', 'consumed'):
            if str(tok.status) == 'revoked':
                raise DeviceProvisioningError('activation_token_revoked', http_status=403)
            if str(tok.status) == 'expired':
                raise DeviceProvisioningError('activation_token_expired', http_status=400)
            raise DeviceProvisioningError('activation_token_invalid', http_status=401)
        if tok.expires_at is not None and tok.expires_at < datetime.utcnow() and str(tok.status) == 'active':
            raise DeviceProvisioningError('activation_token_expired', http_status=400)
        reg = (tok.register_ref or '').strip()
        if not reg:
            raise DeviceProvisioningError('ops_not_ready', http_status=409)
        # Objeto duck-typed compatible con register() que lee branch/pos/register_ref
        from models.core_master import CoreOrgUnit
        from nodeone.core.master.constants import ORG_UNIT_TYPE_REGISTER

        unit = CoreOrgUnit.query.filter_by(
            organization_id=int(tok.organization_id), unit_ref=reg
        ).first()
        if unit is None or str(getattr(unit, 'unit_type', '')).lower() != ORG_UNIT_TYPE_REGISTER:
            raise DeviceProvisioningError('ops_not_ready', http_status=409)
        pos_ref = ''
        branch_ref = ''
        if unit.parent_id:
            pos = CoreOrgUnit.query.filter_by(
                organization_id=int(tok.organization_id), id=int(unit.parent_id)
            ).first()
            if pos is not None:
                pos_ref = pos.unit_ref
                if pos.parent_id:
                    br = CoreOrgUnit.query.filter_by(
                        organization_id=int(tok.organization_id), id=int(pos.parent_id)
                    ).first()
                    if br is not None:
                        branch_ref = br.unit_ref

        class _Bridge:
            pass

        bridge = _Bridge()
        bridge.organization_id = int(tok.organization_id)
        bridge.branch_ref = branch_ref or 'branch-unknown'
        bridge.pos_ref = pos_ref or 'pos-unknown'
        bridge.register_ref = reg
        bridge.code = tok.token
        bridge.status = 'active'
        bridge.id = None
        bridge._activation_token_id = int(tok.id)
        return bridge

    # --- Legacy EN1-01 (org-level code) ---

    @staticmethod
    def ensure_provisioning_code(organization_id: int) -> str:
        """Legacy: código por org (solo compatibilidad / display). Preferir issue_code_for_register."""
        from app import db

        oid = int(organization_id)
        row = EposoneSettings.query.filter_by(organization_id=oid).first()
        if row is None:
            row = EposoneSettings(organization_id=oid)
            db.session.add(row)
            db.session.flush()
        code = (getattr(row, 'provisioning_code', None) or '').strip()
        if not code:
            code = _new_provisioning_code()
            row.provisioning_code = code
            db.session.commit()
        return code

    @staticmethod
    def rotate_provisioning_code(organization_id: int) -> str:
        from app import db

        oid = int(organization_id)
        row = EposoneSettings.query.filter_by(organization_id=oid).first()
        if row is None:
            row = EposoneSettings(organization_id=oid)
            db.session.add(row)
        code = _new_provisioning_code()
        row.provisioning_code = code
        db.session.commit()
        return code

    @staticmethod
    def _resolve_organization(
        *,
        organization_id: int | None,
        organization_ref: str | None,
    ) -> SaasOrganization:
        if organization_id is not None:
            org = SaasOrganization.query.filter_by(id=int(organization_id)).first()
            if org is None:
                raise DeviceProvisioningError('organization_not_found', http_status=404)
            return org
        ref = (organization_ref or '').strip()
        if not ref:
            raise DeviceProvisioningError('organization_required', http_status=400)
        org = SaasOrganization.query.filter_by(subdomain=ref).first()
        if org is None:
            org = SaasOrganization.query.filter_by(name=ref).first()
        if org is None:
            raise DeviceProvisioningError('organization_not_found', http_status=404)
        return org

    @staticmethod
    def _assert_eposone_enabled(organization_id: int) -> None:
        from models.saas import SaasModule, SaasOrgModule

        mod = SaasModule.query.filter_by(code='eposone').first()
        if mod is None:
            return
        link = SaasOrgModule.query.filter_by(
            organization_id=int(organization_id),
            module_id=int(mod.id),
            enabled=True,
        ).first()
        if link is None:
            raise DeviceProvisioningError('eposone_not_enabled', http_status=403)

    @staticmethod
    def _validate_org_level_code(organization_id: int, code: str | None) -> None:
        provided = (code or '').strip()
        if not provided:
            raise DeviceProvisioningError('provisioning_code_required', http_status=401)
        row = EposoneSettings.query.filter_by(organization_id=int(organization_id)).first()
        expected = (getattr(row, 'provisioning_code', None) or '').strip() if row else ''
        env_fallback = (os.environ.get('EPOSONE_PROVISIONING_CODE') or '').strip()
        ok = False
        if expected and secrets.compare_digest(provided, expected):
            ok = True
        elif not expected and env_fallback and secrets.compare_digest(provided, env_fallback):
            ok = True
        if not ok:
            DeviceProvisioningService._audit_auth_failed(
                organization_id, reason='provisioning_code_invalid_legacy'
            )
            raise DeviceProvisioningError('provisioning_code_invalid', http_status=401)

    @staticmethod
    def _audit_auth_failed(organization_id: int | None, *, reason: str) -> None:
        _audit_publish(int(organization_id or 0), EVENT_AUTH_FAILED, {'reason': reason})

    @staticmethod
    def _get_unit(
        organization_id: int,
        unit_ref: str,
        *,
        allowed_types: frozenset[str],
    ) -> CoreOrgUnit:
        ref = (unit_ref or '').strip()
        if not ref:
            raise DeviceProvisioningError('unit_ref_required', http_status=400)
        row = CoreOrgUnit.query.filter_by(
            organization_id=int(organization_id),
            unit_ref=ref,
        ).first()
        if row is None:
            raise DeviceProvisioningError(f'unit_not_found:{ref}', http_status=400)
        if str(row.unit_type) not in allowed_types:
            raise DeviceProvisioningError(f'invalid_unit_type:{row.unit_type}', http_status=400)
        if str(row.status) != ORG_UNIT_STATUS_ACTIVE:
            raise DeviceProvisioningError(f'unit_inactive:{ref}', http_status=400)
        return row

    @staticmethod
    def register(
        *,
        provisioning_code: str | None,
        device_uuid: str,
        organization_id: int | None = None,
        organization_ref: str | None = None,
        branch_ref: str | None = None,
        pos_ref: str | None = None,
        register_ref: str | None = None,
        device_name: str | None = None,
        platform: str | None = None,
        device_model: str | None = None,
        android_version: str | None = None,
        app_version: str | None = None,
    ) -> dict[str, Any]:
        from app import db

        uuid = (device_uuid or '').strip()
        if not uuid:
            raise DeviceProvisioningError('device_uuid_required', http_status=400)

        dest_code: EposoneProvisioningCode | None = None
        # Camino oficial EN1-02: código = destino
        try:
            dest_code = DeviceProvisioningService.resolve_destination_by_code(provisioning_code)
        except DeviceProvisioningError as exc:
            # Si el body trae jerarquía completa → legacy EN1-01
            has_legacy = (
                (organization_id is not None or (organization_ref or '').strip())
                and (branch_ref or '').strip()
                and (pos_ref or '').strip()
                and (register_ref or '').strip()
            )
            if not has_legacy:
                raise exc
            dest_code = None

        if dest_code is not None:
            oid = int(dest_code.organization_id)
            org = SaasOrganization.query.filter_by(id=oid).first()
            if org is None or not org.is_active:
                raise DeviceProvisioningError('organization_inactive', http_status=403)
            DeviceProvisioningService._assert_eposone_enabled(oid)
            try:
                branch = DeviceProvisioningService._get_unit(
                    oid, dest_code.branch_ref, allowed_types=frozenset({ORG_UNIT_TYPE_BRANCH})
                )
                pos = DeviceProvisioningService._get_unit(
                    oid, dest_code.pos_ref, allowed_types=ORG_UNIT_POS_TYPES
                )
                register = DeviceProvisioningService._get_unit(
                    oid, dest_code.register_ref, allowed_types=frozenset({ORG_UNIT_TYPE_REGISTER})
                )
            except DeviceProvisioningError as exc:
                _audit_publish(
                    oid,
                    EVENT_PROVISION_FAILED,
                    {'error': exc.code, 'device_uuid': uuid},
                )
                raise
            dest_code.last_used_at = datetime.utcnow()
            if getattr(dest_code, 'id', None) is not None:
                dest_code.status = STATUS_USED
            elif getattr(dest_code, '_activation_token_id', None):
                # Puente ADR-035: no mutar fila provisioning; token ya se gestiona en redeem
                pass
            else:
                dest_code.status = STATUS_USED
        else:
            # Legacy EN1-01
            org = DeviceProvisioningService._resolve_organization(
                organization_id=int(organization_id)
                if organization_id is not None and str(organization_id).strip() != ''
                else None,
                organization_ref=organization_ref,
            )
            if not org.is_active:
                raise DeviceProvisioningError('organization_inactive', http_status=403)
            oid = int(org.id)
            DeviceProvisioningService._assert_eposone_enabled(oid)
            DeviceProvisioningService._validate_org_level_code(oid, provisioning_code)
            try:
                branch = DeviceProvisioningService._get_unit(
                    oid, str(branch_ref or ''), allowed_types=frozenset({ORG_UNIT_TYPE_BRANCH})
                )
                pos = DeviceProvisioningService._get_unit(
                    oid, str(pos_ref or ''), allowed_types=ORG_UNIT_POS_TYPES
                )
                register = DeviceProvisioningService._get_unit(
                    oid, str(register_ref or ''), allowed_types=frozenset({ORG_UNIT_TYPE_REGISTER})
                )
            except DeviceProvisioningError as exc:
                _audit_publish(
                    oid,
                    EVENT_PROVISION_FAILED,
                    {'error': exc.code, 'device_uuid': uuid},
                )
                raise

        existing = CorePosTerminal.query.filter_by(
            organization_id=oid,
            terminal_ref=uuid,
        ).first()

        access_token = _new_access_token()
        token_hash = _hash_token(access_token)
        now = datetime.utcnow()
        is_reprovision = existing is not None

        if existing is None:
            row = CorePosTerminal(
                organization_id=oid,
                terminal_ref=uuid,
                register_ref=register.unit_ref,
                status=POS_TERMINAL_ACTIVE,
                device_label=(device_name or '').strip() or None,
                profile='fixed',
                platform=(platform or 'android').strip() or 'android',
                device_model=(device_model or None),
                app_version=(app_version or None),
                android_version=(android_version or None),
                branch_ref=branch.unit_ref,
                pos_ref=pos.unit_ref,
                sync_enabled=True,
                last_seen_at=now,
                access_token_hash=token_hash,
                config_version=1,
            )
            db.session.add(row)
            event = EVENT_REGISTERED
        else:
            existing.register_ref = register.unit_ref
            existing.branch_ref = branch.unit_ref
            existing.pos_ref = pos.unit_ref
            if device_name is not None:
                existing.device_label = (device_name or '').strip() or None
            if platform is not None:
                existing.platform = (platform or '').strip() or existing.platform
            if device_model is not None:
                existing.device_model = device_model or None
            if app_version is not None:
                existing.app_version = app_version or None
            if android_version is not None:
                existing.android_version = android_version or None
            existing.status = POS_TERMINAL_ACTIVE
            existing.sync_enabled = True
            existing.last_seen_at = now
            existing.access_token_hash = token_hash
            existing.config_version = int(getattr(existing, 'config_version', 0) or 0) + 1
            row = existing
            event = EVENT_REPROVISIONED

        db.session.commit()

        if dest_code is not None and event == EVENT_REGISTERED:
            try:
                from nodeone.modules.eposone.register_license_service import RegisterLicenseService

                RegisterLicenseService.on_first_device_provisioned(oid, str(register.unit_ref))
            except Exception:
                pass

        _audit_publish(
            oid,
            event,
            {
                'device_uuid': uuid,
                'branch_ref': branch.unit_ref,
                'pos_ref': pos.unit_ref,
                'register_ref': register.unit_ref,
                'reprovision': is_reprovision,
                'contract': 'en1-02' if dest_code is not None else 'en1-01-legacy',
            },
        )

        config = DeviceProvisioningService.build_config(row, org=org)
        # Installation Lifecycle v1 — hint aditivo (EN1-02 addendum); no breaking.
        return {
            'access_token': access_token,
            'token_type': 'Bearer',
            'device': DeviceProvisioningService.device_public_dict(row),
            'config': config,
            'next': 'bootstrap',
            'bootstrap_required': True,
        }

    @staticmethod
    def require_installation_ready(row: CorePosTerminal) -> None:
        """
        C3b — si EPOSONE_ENFORCE_INSTALLATION_READY está activo, exige ACK previo.

        No aplica a terminal sintético BO (`en1-backoffice`).
        Error: installation_incomplete 403.
        """
        if not installation_enforcement_enabled():
            return
        from nodeone.modules.eposone.bo_actor import BACKOFFICE_TERMINAL_REF

        if str(getattr(row, 'terminal_ref', '') or '') == BACKOFFICE_TERMINAL_REF:
            return
        if getattr(row, 'installation_ready_at', None) is not None:
            return
        raise DeviceProvisioningError('installation_incomplete', http_status=403)

    @staticmethod
    def authenticate_bearer(authorization_header: str | None) -> CorePosTerminal:
        raw = (authorization_header or '').strip()
        if not raw.lower().startswith('bearer '):
            DeviceProvisioningService._audit_auth_failed(None, reason='bearer_missing')
            raise DeviceProvisioningError('unauthorized', http_status=401)
        token = raw[7:].strip()
        if not token:
            DeviceProvisioningService._audit_auth_failed(None, reason='bearer_empty')
            raise DeviceProvisioningError('unauthorized', http_status=401)
        token_hash = _hash_token(token)
        row = CorePosTerminal.query.filter_by(access_token_hash=token_hash).first()
        if row is None:
            DeviceProvisioningService._audit_auth_failed(None, reason='token_invalid')
            raise DeviceProvisioningError('unauthorized', http_status=401)
        if str(row.status) != POS_TERMINAL_ACTIVE:
            raise DeviceProvisioningError('device_inactive', http_status=403)
        return row

    @staticmethod
    def get_config_for_terminal(row: CorePosTerminal) -> dict[str, Any]:
        from app import db

        row.last_seen_at = datetime.utcnow()
        db.session.commit()
        return DeviceProvisioningService.build_config(row)

    @staticmethod
    def build_bootstrap_for_terminal(
        row: CorePosTerminal,
        *,
        include: frozenset[str] | None = None,
        known_cashiers_version: int | None = None,
        known_policies_version: int | None = None,
        known_catalog_version: int | None = None,
    ) -> dict[str, Any]:
        """
        Hito 2 — Device Bootstrap (Sync Down) v1.
        Snapshot: config + products + stock_balances + cashiers + commercial policies (infra V6).

        ADR-039 post-F6: si ``known_catalog_version`` coincide con ``catalog_version``,
        no se reenvía el array ``products`` (mismo patrón que cashiers).
        """
        from app import db
        from models.core_master import CoreProduct
        from nodeone.core.commerce.stock import StockService
        from nodeone.core.services.product import ProductService

        include_set = include or frozenset(
            {'config', 'products', 'stock', 'cashiers', 'policies'}
        )
        oid = int(row.organization_id)

        row.last_seen_at = datetime.utcnow()
        db.session.commit()

        full_config = DeviceProvisioningService.build_config(row)
        # Forma compacta del contrato Hito 2 (sin anidar device dentro de config).
        config_out = {
            'organization': full_config.get('organization'),
            'branch': full_config.get('branch'),
            'pos': full_config.get('pos'),
            'register': full_config.get('register'),
            'currency': full_config.get('currency'),
            'timezone': full_config.get('timezone'),
            'business_name': full_config.get('business_name'),
            'commercial': full_config.get('commercial'),
        }

        products_out: list[dict[str, Any]] = []
        catalog_version = 1
        if 'products' in include_set:
            # Activos primero; incluir inactive para que APK pueda ocultar.
            items = ProductService.search(oid, limit=500)
            products_out = [
                {
                    'product_ref': p.product_ref,
                    'name': p.name,
                    'description': p.description,
                    'product_type': p.product_type,
                    'status': p.status,
                    'category': p.category,
                    'fiscal_category': getattr(p, 'fiscal_category', None),
                    'barcode': p.barcode,
                    'unit_price': float(p.unit_price or 0),
                    'currency': p.currency or 'USD',
                    'cost_price': p.cost_price,
                    'tracks_inventory': bool(p.tracks_inventory),
                    'uom': p.uom or 'und',
                    'purchase_uom': p.purchase_uom,
                    'pack_factor': float(p.pack_factor if p.pack_factor is not None else 1),
                    'min_stock': p.min_stock,
                    'max_stock': p.max_stock,
                    'image_url': p.image_url,
                }
                for p in items
            ]
            latest = (
                CoreProduct.query.filter_by(organization_id=oid)
                .order_by(CoreProduct.updated_at.desc(), CoreProduct.id.desc())
                .first()
            )
            if latest is not None and getattr(latest, 'updated_at', None):
                catalog_version = int(latest.updated_at.timestamp())
            elif products_out:
                catalog_version = len(products_out)

        stock_out: list[dict[str, Any]] = []
        if 'stock' in include_set:
            branch_unit = None
            if row.branch_ref:
                branch_unit = CoreOrgUnit.query.filter_by(
                    organization_id=oid, unit_ref=str(row.branch_ref)
                ).first()
            warehouse_id = StockService.resolve_warehouse_id(
                oid,
                int(branch_unit.id) if branch_unit is not None else None,
            )
            balances = StockService.list_balances(
                oid,
                warehouse_org_unit_id=warehouse_id,
                limit=500,
            )
            # Si no hay bodega de sucursal, devolver todos los saldos de la org (fallback).
            if warehouse_id is None:
                balances = StockService.list_balances(oid, limit=500)

            wh_ref_by_id: dict[int, str] = {}
            for b in balances:
                wid = int(b.warehouse_org_unit_id)
                if wid not in wh_ref_by_id:
                    wu = CoreOrgUnit.query.filter_by(organization_id=oid, id=wid).first()
                    wh_ref_by_id[wid] = str(wu.unit_ref) if wu is not None else str(wid)
                stock_out.append(
                    {
                        'product_ref': b.product_ref,
                        'warehouse_ref': wh_ref_by_id[wid],
                        'warehouse_org_unit_id': wid,
                        'quantity_on_hand': float(b.quantity_on_hand),
                        'quantity_reserved': float(b.quantity_reserved),
                        'quantity_available': float(b.quantity_available),
                    }
                )

        generated_at = datetime.utcnow()
        payload: dict[str, Any] = {
            'schema_version': 1,
            'generated_at': _iso(generated_at),
            'config_version': int(full_config.get('config_version') or 1),
            'catalog_version': int(catalog_version),
            # Installation Lifecycle Contract v1 — aditivo; APKs viejas lo ignoran.
            'installation': build_installation_block(
                now=generated_at,
                ready_acked_at=getattr(row, 'installation_ready_at', None),
            ),
        }
        if 'config' in include_set:
            payload['config'] = config_out
        if 'products' in include_set:
            catalog_unchanged = (
                known_catalog_version is not None
                and int(known_catalog_version) == int(catalog_version)
            )
            payload['products_changed'] = not catalog_unchanged
            if not catalog_unchanged:
                payload['products'] = products_out
                payload['products_count'] = len(products_out)
            else:
                payload['products_count'] = 0
        if 'stock' in include_set:
            payload['stock_balances'] = stock_out
            payload['stock_balances_count'] = len(stock_out)
        if 'cashiers' in include_set:
            from nodeone.modules.eposone.cashier_service import CashierService

            cashiers, cashiers_version = CashierService.snapshot(oid)
            payload['cashiers_version'] = cashiers_version
            unchanged = (
                known_cashiers_version is not None
                and int(known_cashiers_version) == cashiers_version
            )
            payload['cashiers_changed'] = not unchanged
            if not unchanged:
                payload['cashiers'] = cashiers
                payload['cashiers_count'] = len(cashiers)
        if 'policies' in include_set:
            from nodeone.modules.eposone.commercial_policy_service import (
                CommercialPolicyService,
            )

            policy_snap = CommercialPolicyService.snapshot_for_terminal(
                oid,
                branch_ref=row.branch_ref,
                pos_ref=row.pos_ref,
                register_ref=row.register_ref,
                known_policies_version=known_policies_version,
            )
            payload.update(policy_snap)
        return payload

    @staticmethod
    def device_public_dict(row: CorePosTerminal) -> dict[str, Any]:
        return {
            'uuid': str(row.terminal_ref),
            'name': row.device_label,
            'status': str(row.status),
            'registered_at': _iso(row.created_at),
            'last_seen_at': _iso(row.last_seen_at),
            'organization_id': int(row.organization_id),
            'branch_ref': row.branch_ref,
            'pos_ref': row.pos_ref,
            'register_ref': row.register_ref,
            'app_version': row.app_version,
            'installation_ready_at': _iso(getattr(row, 'installation_ready_at', None)),
            'client_install_id': getattr(row, 'client_install_id', None),
        }

    @staticmethod
    def ack_installation_ready(
        row: CorePosTerminal,
        body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Installation Lifecycle C3 — ACK observabilidad (no habilita ni bloquea POS en EN1).

        Idempotente: re-ACK actualiza ready_at / checklist / app_version.
        """
        import json

        from app import db

        payload = body or {}
        client_install_id = str(payload.get('client_install_id') or '').strip() or None
        app_version = str(payload.get('app_version') or '').strip() or None
        checklist = payload.get('checklist')
        if checklist is not None and not isinstance(checklist, dict):
            raise DeviceProvisioningError('invalid_checklist', http_status=400)

        ready_at = datetime.utcnow()
        raw_ready = payload.get('ready_at')
        if raw_ready is not None and str(raw_ready).strip():
            try:
                from datetime import timezone

                text = str(raw_ready).strip().replace('Z', '+00:00')
                parsed = datetime.fromisoformat(text)
                if parsed.tzinfo is not None:
                    ready_at = parsed.astimezone(timezone.utc).replace(tzinfo=None)
                else:
                    ready_at = parsed
            except (TypeError, ValueError):
                raise DeviceProvisioningError('invalid_ready_at', http_status=400) from None

        row.installation_ready_at = ready_at
        if client_install_id is not None:
            row.client_install_id = client_install_id[:128]
        if app_version is not None:
            row.app_version = app_version[:64]
        if checklist is not None:
            row.installation_checklist_json = json.dumps(checklist, ensure_ascii=False, separators=(',', ':'))
        row.last_seen_at = datetime.utcnow()
        db.session.commit()

        _audit_publish(
            int(row.organization_id),
            EVENT_INSTALLATION_READY,
            {
                'device_uuid': str(row.terminal_ref),
                'register_ref': row.register_ref,
                'client_install_id': row.client_install_id,
                'app_version': row.app_version,
                'ready_at': _iso(row.installation_ready_at),
                'checklist_keys': sorted(checklist.keys()) if isinstance(checklist, dict) else [],
            },
        )
        return {
            'ok': True,
            'installation_ready_at': _iso(row.installation_ready_at),
            'client_install_id': row.client_install_id,
            'device': DeviceProvisioningService.device_public_dict(row),
        }

    @staticmethod
    def build_config(
        row: CorePosTerminal,
        *,
        org: SaasOrganization | None = None,
    ) -> dict[str, Any]:
        from nodeone.modules.eposone.settings_service import EposoneSettingsService
        from nodeone.core.timezone_service import TimeZoneService

        oid = int(row.organization_id)
        if org is None:
            org = SaasOrganization.query.filter_by(id=oid).first()
        settings = EposoneSettingsService.get_settings(oid)

        def _unit_name(unit_ref: str | None) -> str | None:
            if not unit_ref:
                return None
            u = CoreOrgUnit.query.filter_by(organization_id=oid, unit_ref=unit_ref).first()
            return str(u.name) if u is not None else None

        return {
            'config_version': int(getattr(row, 'config_version', 1) or 1),
            'business_name': str(org.name) if org is not None else '',
            'currency': str(settings.default_currency or 'USD'),
            'timezone': (
                TimeZoneService.org_timezone_name(org)
                if org is not None
                else TimeZoneService.validate_iana(
                    (os.environ.get('EPOSONE_DEFAULT_TIMEZONE') or DEFAULT_TIMEZONE)
                )
            ),
            'organization': {
                'id': oid,
                'name': str(org.name) if org is not None else '',
            },
            'branch': {
                'ref': row.branch_ref,
                'name': _unit_name(row.branch_ref),
            },
            'pos': {
                'ref': row.pos_ref,
                'name': _unit_name(row.pos_ref),
            },
            'register': {
                'ref': row.register_ref,
                'name': _unit_name(row.register_ref),
                'cash_operation_mode': _resolve_cash_mode(oid),
            },
            'device': {
                'uuid': str(row.terminal_ref),
                'name': row.device_label,
                'status': str(row.status),
                'app_version': row.app_version,
                'last_seen_at': _iso(row.last_seen_at),
                'installation_ready_at': _iso(getattr(row, 'installation_ready_at', None)),
            },
            'commercial': _commercial_block_for_org(oid),
            'license': _license_block_for_register(oid, str(row.register_ref or '')),
        }

    @staticmethod
    def list_devices(organization_id: int, *, limit: int = 100) -> list[CorePosTerminal]:
        return (
            CorePosTerminal.query.filter_by(organization_id=int(organization_id))
            .order_by(CorePosTerminal.created_at.desc(), CorePosTerminal.id.asc())
            .limit(max(1, int(limit)))
            .all()
        )


def _license_block_for_register(organization_id: int, register_ref: str) -> dict[str, Any]:
    try:
        from nodeone.modules.eposone.register_license_service import RegisterLicenseService

        return RegisterLicenseService.serve_for_device(
            int(organization_id),
            register_ref,
            touch_validation=True,
            event='license.bootstrap_served',
        )
    except Exception:
        try:
            from nodeone.core.services.audit import AuditService

            AuditService.publish_domain_event(
                int(organization_id),
                'license.validation_failed',
                {'register_ref': register_ref, 'reason': 'license_unavailable'},
                source_app_id='eposone',
            )
        except Exception:
            pass
        return {
            'schema_version': 1,
            'license_id': None,
            'license_type': 'TRIAL',
            'status': 'PENDING',
            'plan_code': 'eposone',
            'activation_method': 'EN1',
            'issued_at': None,
            'starts_at': None,
            'expires_at': None,
            'grace_until': None,
            'last_validation': None,
            'features': [],
            'limits': {},
            'updated_at': None,
        }


def _commercial_block_for_org(organization_id: int) -> dict[str, Any]:
    """ADR-027 / Onboarding Gate 1 — modality for APK (not License Engine plan_code)."""
    try:
        from nodeone.core.platform.commercial_plans import commercial_context_for_org

        return commercial_context_for_org(int(organization_id), product_code='eposone')
    except Exception:
        return {
            'schema_version': 1,
            'product_code': 'eposone',
            'plan_code': 'starter',
            'plan_name': 'Starter',
            'modality': 'connected',
            'operating_modality': 'connected',
            'sync_cloud': True,
        }
