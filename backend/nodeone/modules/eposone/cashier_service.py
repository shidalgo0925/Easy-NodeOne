"""Catálogo de cajeros EPosOne sobre el maestro canónico de contactos."""

from __future__ import annotations

import base64
import hashlib
import hmac
import re
import secrets
from datetime import datetime
from typing import Any

from models.contact import Contact
from models.eposone_cashier import EposoneCashierCredential
from nodeone.core.services.contacts import ContactDTO, ContactService

PIN_ITERATIONS = 310_000
PIN_PATTERN = re.compile(r'[0-9]{4,8}\Z')


class CashierValidationError(ValueError):
    pass


def _b64encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b'=').decode('ascii')


def _b64decode(raw: str) -> bytes:
    return base64.urlsafe_b64decode(raw + ('=' * (-len(raw) % 4)))


def _build_pin_verifier(pin: str) -> str:
    normalized = str(pin or '').strip()
    if not PIN_PATTERN.fullmatch(normalized):
        raise CashierValidationError('El PIN debe contener entre 4 y 8 dígitos.')
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        'sha256',
        normalized.encode('ascii'),
        salt,
        PIN_ITERATIONS,
        dklen=32,
    )
    return f'pbkdf2_sha256${PIN_ITERATIONS}${_b64encode(salt)}${_b64encode(digest)}'


def verify_pin(pin: str, verifier: str) -> bool:
    """Verifica el formato portable usado también por la APK."""
    try:
        algorithm, iterations, salt, expected = str(verifier or '').split('$', 3)
        if algorithm != 'pbkdf2_sha256':
            return False
        candidate = hashlib.pbkdf2_hmac(
            'sha256',
            str(pin or '').encode('ascii'),
            _b64decode(salt),
            int(iterations),
            dklen=32,
        )
        return hmac.compare_digest(candidate, _b64decode(expected))
    except (TypeError, ValueError, UnicodeEncodeError):
        return False


def _iso_utc(value: datetime) -> str:
    return value.isoformat(timespec='milliseconds') + ('Z' if value.tzinfo is None else '')


def _audit(organization_id: int, event_type: str, payload: dict[str, Any]) -> None:
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


class CashierService:
    @staticmethod
    def list_cashiers(organization_id: int, *, active_only: bool | None = None) -> list[ContactDTO]:
        rows, _ = ContactService.search(
            int(organization_id),
            role='cashier',
            active_only=active_only,
            limit=500,
        )
        return rows

    @staticmethod
    def get(organization_id: int, cashier_id: int) -> ContactDTO | None:
        dto = ContactService.get(int(organization_id), int(cashier_id))
        if dto is None or not dto.is_cashier:
            return None
        return dto

    @staticmethod
    def create(organization_id: int, data: dict[str, Any]) -> ContactDTO:
        from app import db

        name = str(data.get('display_name') or '').strip()
        if not name:
            raise CashierValidationError('El nombre del cajero es obligatorio.')
        pin_verifier = _build_pin_verifier(str(data.get('pin') or ''))
        payload = {
            'contact_type': 'person',
            'display_name': name,
            'email': str(data.get('email') or '').strip() or None,
            'phone': str(data.get('phone') or '').strip() or None,
            'identification_type': 'consumer_final',
            'is_employee': True,
            'is_cashier': True,
            'active': True,
        }
        try:
            dto = ContactService.create(int(organization_id), payload)
            db.session.add(
                EposoneCashierCredential(
                    organization_id=int(organization_id),
                    cashier_contact_id=int(dto.id),
                    pin_verifier=pin_verifier,
                    pin_version=1,
                    pin_updated_at=datetime.utcnow(),
                )
            )
            db.session.commit()
        except ContactService.ValidationError as exc:
            db.session.rollback()
            raise CashierValidationError(str(exc)) from exc
        _audit(
            int(organization_id),
            'eposone.cashier.created',
            {'cashier_id': dto.id, 'display_name': dto.display_name},
        )
        return dto

    @staticmethod
    def update(organization_id: int, cashier_id: int, data: dict[str, Any]) -> ContactDTO:
        from app import db

        row = Contact.query.filter_by(
            organization_id=int(organization_id),
            id=int(cashier_id),
            is_cashier=True,
        ).first()
        if row is None:
            raise CashierValidationError('Cajero no encontrado.')
        name = str(data.get('display_name') or '').strip()
        if not name:
            raise CashierValidationError('El nombre del cajero es obligatorio.')
        pin = str(data.get('pin') or '').strip()
        verifier = _build_pin_verifier(pin) if pin else None
        row.display_name = name[:300]
        row.email = str(data.get('email') or '').strip()[:255] or None
        row.phone = str(data.get('phone') or '').strip()[:50] or None
        row.is_employee = True
        row.is_cashier = True
        if verifier is not None:
            credential = EposoneCashierCredential.query.filter_by(
                organization_id=int(organization_id),
                cashier_contact_id=int(cashier_id),
            ).first()
            if credential is None:
                credential = EposoneCashierCredential(
                    organization_id=int(organization_id),
                    cashier_contact_id=int(cashier_id),
                    pin_verifier=verifier,
                    pin_version=1,
                )
                db.session.add(credential)
            else:
                credential.pin_verifier = verifier
                credential.pin_version = int(credential.pin_version or 0) + 1
            credential.pin_updated_at = datetime.utcnow()
        db.session.commit()
        dto = ContactService.get(int(organization_id), int(row.id))
        if dto is None:
            raise CashierValidationError('Cajero no encontrado.')
        _audit(
            int(organization_id),
            'eposone.cashier.updated',
            {'cashier_id': dto.id, 'display_name': dto.display_name},
        )
        return dto

    @staticmethod
    def require_cashier(
        organization_id: int,
        cashier_id: int | str | None,
        *,
        active: bool = False,
    ) -> Contact:
        if cashier_id is None or str(cashier_id).strip() == '':
            raise CashierValidationError('cashier_contact_id_required')
        try:
            normalized_id = int(cashier_id)
        except (TypeError, ValueError) as exc:
            raise CashierValidationError('cashier_contact_id_invalid') from exc
        row = Contact.query.filter_by(
            organization_id=int(organization_id),
            id=normalized_id,
            is_cashier=True,
        ).first()
        if row is None:
            raise CashierValidationError('cashier_not_found')
        if active and not bool(row.active):
            raise CashierValidationError('cashier_inactive')
        return row

    @staticmethod
    def snapshot(organization_id: int) -> tuple[list[dict[str, Any]], int]:
        rows = (
            Contact.query.filter_by(
                organization_id=int(organization_id),
                is_cashier=True,
            )
            .order_by(Contact.display_name.asc(), Contact.id.asc())
            .all()
        )
        credentials = {
            int(item.cashier_contact_id): item
            for item in EposoneCashierCredential.query.filter_by(
                organization_id=int(organization_id)
            ).all()
        }
        snapshot: list[dict[str, Any]] = []
        version = 0
        for row in rows:
            credential = credentials.get(int(row.id))
            updated_at = row.updated_at or row.created_at or datetime.utcnow()
            pin_version = 0
            pin_verifier = None
            if credential is not None:
                pin_version = int(credential.pin_version or 0)
                pin_updated_at = credential.pin_updated_at or credential.updated_at
                if pin_updated_at and pin_updated_at > updated_at:
                    updated_at = pin_updated_at
                if bool(row.active):
                    pin_verifier = str(credential.pin_verifier)
            version = max(version, int(updated_at.timestamp() * 1000))
            snapshot.append(
                {
                    'cashier_contact_id': int(row.id),
                    'cashier_name': str(row.display_name),
                    'cashier_code': f'CJR-{int(row.id):04d}',
                    'is_active': bool(row.active),
                    'pin_verifier': pin_verifier,
                    'pin_version': pin_version,
                    'updated_at': _iso_utc(updated_at),
                }
            )
        return snapshot, version

    @staticmethod
    def set_active(organization_id: int, cashier_id: int, *, active: bool) -> ContactDTO:
        from app import db

        row = Contact.query.filter_by(
            organization_id=int(organization_id),
            id=int(cashier_id),
            is_cashier=True,
        ).first()
        if row is None:
            raise CashierValidationError('Cajero no encontrado.')
        row.active = bool(active)
        db.session.commit()
        dto = ContactService.get(int(organization_id), int(row.id))
        if dto is None:
            raise CashierValidationError('Cajero no encontrado.')
        _audit(
            int(organization_id),
            'eposone.cashier.status_changed',
            {'cashier_id': dto.id, 'active': dto.active},
        )
        return dto
