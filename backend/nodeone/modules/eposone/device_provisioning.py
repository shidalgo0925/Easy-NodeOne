"""Provisioning de dispositivos EPosOne — Hito EN1-02 (código = destino).

EN1-01 (código por org + refs en body) queda como compatibilidad legacy.
Contrato oficial: solo device_uuid + metadatos + código de destino.
"""

from __future__ import annotations

import hashlib
import os
import secrets
from datetime import datetime
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

DEFAULT_TIMEZONE = 'America/Panama'
STATUS_ACTIVE = 'active'
STATUS_REVOKED = 'revoked'


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

        row = EposoneProvisioningCode(
            organization_id=oid,
            branch_ref=branch.unit_ref,
            pos_ref=pos.unit_ref,
            register_ref=reg.unit_ref,
            code=code,
            status=STATUS_ACTIVE,
            label=(label or '').strip() or f'{pos.name} / {reg.name}',
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
        return (
            EposoneProvisioningCode.query.filter_by(
                organization_id=int(organization_id),
                register_ref=(register_ref or '').strip(),
                status=STATUS_ACTIVE,
            )
            .order_by(EposoneProvisioningCode.id.desc())
            .first()
        )

    @staticmethod
    def resolve_destination_by_code(code: str | None) -> EposoneProvisioningCode:
        provided = (code or '').strip()
        if not provided:
            DeviceProvisioningService._audit_auth_failed(None, reason='provisioning_code_missing')
            raise DeviceProvisioningError('provisioning_code_required', http_status=401)
        row = EposoneProvisioningCode.query.filter_by(code=provided, status=STATUS_ACTIVE).first()
        if row is None:
            DeviceProvisioningService._audit_auth_failed(None, reason='provisioning_code_invalid')
            raise DeviceProvisioningError('provisioning_code_invalid', http_status=401)
        return row

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
        return {
            'access_token': access_token,
            'token_type': 'Bearer',
            'device': DeviceProvisioningService.device_public_dict(row),
            'config': config,
        }

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
        }

    @staticmethod
    def build_config(
        row: CorePosTerminal,
        *,
        org: SaasOrganization | None = None,
    ) -> dict[str, Any]:
        from nodeone.modules.eposone.settings_service import EposoneSettingsService

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
            'timezone': (os.environ.get('EPOSONE_DEFAULT_TIMEZONE') or DEFAULT_TIMEZONE).strip(),
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
            },
            'device': {
                'uuid': str(row.terminal_ref),
                'name': row.device_label,
                'status': str(row.status),
                'app_version': row.app_version,
                'last_seen_at': _iso(row.last_seen_at),
            },
        }

    @staticmethod
    def list_devices(organization_id: int, *, limit: int = 100) -> list[CorePosTerminal]:
        return (
            CorePosTerminal.query.filter_by(organization_id=int(organization_id))
            .order_by(CorePosTerminal.created_at.desc(), CorePosTerminal.id.asc())
            .limit(max(1, int(limit)))
            .all()
        )
