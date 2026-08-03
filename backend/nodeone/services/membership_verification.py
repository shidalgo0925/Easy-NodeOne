"""Verificación de membresía para API Center (type/value)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import func

from models.benefits import Membership
from models.payments import Subscription
from models.users import User
from nodeone.modules.membership_verification.catalog import (
    SUPPORTED_VERIFICATION_TYPES,
)
from nodeone.services.user_organization import active_organization_ids_for_user


class MembershipVerificationError(Exception):
    def __init__(self, message: str, *, http_status: int = 400, extra: dict | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.http_status = http_status
        self.extra = extra or {}


def _iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    return dt.replace(microsecond=0).isoformat() + 'Z'


def _normalize_email(value: str) -> str:
    return (value or '').strip().lower()


def _user_in_org(user: User, organization_id: int) -> bool:
    return int(organization_id) in active_organization_ids_for_user(user)


def _collect_records(user_id: int) -> list[dict[str, Any]]:
    """Lista unificada de membresías/suscripciones del usuario."""
    now = datetime.utcnow()
    rows: list[dict[str, Any]] = []

    for sub in Subscription.query.filter_by(user_id=int(user_id)).all():
        status_raw = (sub.status or '').strip().lower()
        end = sub.end_date
        if status_raw == 'active' and (end is None or end >= now):
            canon = 'ACTIVE'
        elif status_raw in ('expired', 'cancelled') or (end is not None and end < now):
            canon = 'EXPIRED'
        else:
            canon = 'INACTIVE'
        rows.append(
            {
                'canon': canon,
                'membership_type': sub.membership_type,
                'end_date': end,
                'created_at': getattr(sub, 'created_at', None) or end,
                'payment_status': 'paid' if canon == 'ACTIVE' else None,
            }
        )

    for mem in Membership.query.filter_by(user_id=int(user_id)).all():
        end = mem.end_date
        if bool(mem.is_active) and (end is None or end >= now):
            canon = 'ACTIVE'
        elif end is not None and end < now:
            canon = 'EXPIRED'
        else:
            canon = 'INACTIVE'
        rows.append(
            {
                'canon': canon,
                'membership_type': mem.membership_type,
                'end_date': end,
                'created_at': getattr(mem, 'created_at', None) or end,
                'payment_status': getattr(mem, 'payment_status', None),
            }
        )
    return rows


def _pick_membership(records: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not records:
        return None
    active = [r for r in records if r['canon'] == 'ACTIVE']
    if active:
        active.sort(key=lambda r: r.get('end_date') or datetime.max, reverse=True)
        return active[0]

    def _sort_key(r: dict[str, Any]):
        return r.get('end_date') or r.get('created_at') or datetime.min

    records.sort(key=_sort_key, reverse=True)
    return records[0]


def _member_payload(email: str, record: dict[str, Any] | None, *, never_had: bool) -> dict[str, Any]:
    if never_had or record is None:
        return {
            'email': email,
            'is_active_member': False,
            'membership': {'status': 'INACTIVE'},
        }
    status = record['canon']
    membership: dict[str, Any] = {'status': status}
    mtype = (record.get('membership_type') or '').strip()
    if mtype:
        membership['membership_type'] = mtype
    expires = _iso(record.get('end_date'))
    if expires:
        membership['expires_at'] = expires
    pay = record.get('payment_status')
    if pay:
        membership['payment_status'] = pay
    return {
        'email': email,
        'is_active_member': status == 'ACTIVE',
        'membership': membership,
    }


def verify_by_email(*, email: str, organization_id: int) -> dict[str, Any]:
    """
    Retorna body de éxito (success True).
    found=false sin member; found=true con member anidado.
    """
    mail = _normalize_email(email)
    if not mail or '@' not in mail:
        raise MembershipVerificationError('validation_error', http_status=400)

    oid = int(organization_id)
    user = User.query.filter(func.lower(User.email) == mail).first()
    if user is None or not _user_in_org(user, oid):
        return {'success': True, 'found': False}

    records = _collect_records(int(user.id))
    # Admins sin filas comerciales → existe en org pero no es "miembro" activo comercial
    if not records:
        return {
            'success': True,
            'found': True,
            'member': _member_payload(mail, None, never_had=True),
        }

    picked = _pick_membership(records)
    return {
        'success': True,
        'found': True,
        'member': _member_payload(mail, picked, never_had=False),
    }


def verify(*, type: str, value: str, organization_id: int) -> dict[str, Any]:
    vtype = (type or '').strip().lower()
    if not vtype or value is None or str(value).strip() == '':
        raise MembershipVerificationError('validation_error', http_status=400)
    if vtype not in SUPPORTED_VERIFICATION_TYPES:
        raise MembershipVerificationError(
            'type_not_supported',
            http_status=400,
            extra={'supported_types': sorted(SUPPORTED_VERIFICATION_TYPES)},
        )
    if vtype == 'email':
        return verify_by_email(email=str(value), organization_id=organization_id)
    raise MembershipVerificationError(
        'type_not_supported',
        http_status=400,
        extra={'supported_types': sorted(SUPPORTED_VERIFICATION_TYPES)},
    )
