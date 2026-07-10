"""Regeneración masiva de certificados de membresía (formatos PLAN-*)."""

from __future__ import annotations

import json
import time
from datetime import datetime
from typing import Any

_MAX_ERRORS = 12


def is_membership_certificate_format(cert_event) -> bool:
    """Solo formatos de membresía (no seminarios ni huérfanos de evento)."""
    return (
        getattr(cert_event, 'membership_required_id', None) is not None
        and getattr(cert_event, 'event_required_id', None) is None
    )


def _format_date(value) -> str:
    if value is None:
        return ''
    if hasattr(value, 'strftime'):
        return value.strftime('%Y-%m-%d')
    return str(value)[:10]


def user_document_id(user) -> str:
    """
    Documento para certificados de membresía.
    El perfil guarda `cedula_or_passport`; attrs legacy `document_id` / `cedula` por compat.
    """
    for attr in ('document_id', 'cedula_or_passport', 'cedula'):
        val = getattr(user, attr, None)
        if val is None:
            continue
        text = str(val).strip()
        if text:
            return text
    return ''


def refresh_snapshot_document_id(snapshot: dict[str, Any] | None, user) -> dict[str, Any]:
    """Actualiza document_id del snapshot con la cédula vigente del perfil."""
    snap = dict(snapshot or {})
    snap['document_id'] = user_document_id(user)
    return snap


def build_emission_snapshot(user, cert_event) -> dict[str, Any]:
    """Snapshot congelado al emitir (nombre, membresía, fecha)."""
    full_name = f"{getattr(user, 'first_name', '')} {getattr(user, 'last_name', '')}".strip()
    membership = user.get_active_membership() if hasattr(user, 'get_active_membership') else None
    membership_type = getattr(membership, 'membership_type', None) if membership else None
    if not membership_type and getattr(cert_event, 'membership_plan', None):
        membership_type = getattr(cert_event.membership_plan, 'slug', None)
    return {
        'participant_name': full_name or getattr(user, 'email', None) or '',
        'document_id': user_document_id(user),
        'issue_date': datetime.utcnow().strftime('%Y-%m-%d'),
        'membership_type': (membership_type or '').strip(),
        'membership_start': _format_date(getattr(membership, 'start_date', None) if membership else None),
        'membership_end': _format_date(getattr(membership, 'end_date', None) if membership else None),
    }


def legacy_emission_snapshot(cert, user, cert_event) -> dict[str, Any]:
    """Emisiones sin snapshot: congela en la primera regeneración (fecha original en BD)."""
    full_name = f"{getattr(user, 'first_name', '')} {getattr(user, 'last_name', '')}".strip()
    membership_type = ''
    if getattr(cert_event, 'membership_plan', None):
        membership_type = (getattr(cert_event.membership_plan, 'slug', None) or '').strip()
    issue = cert.generated_at if getattr(cert, 'generated_at', None) else datetime.utcnow()
    return {
        'participant_name': full_name or getattr(user, 'email', None) or '',
        'document_id': user_document_id(user),
        'issue_date': _format_date(issue),
        'membership_type': membership_type,
        'membership_start': '',
        'membership_end': '',
        'legacy_inferred': True,
    }


def parse_emission_snapshot(cert) -> dict[str, Any] | None:
    raw = getattr(cert, 'emission_snapshot', None)
    if not raw:
        return None
    try:
        data = json.loads(raw)
        return data if isinstance(data, dict) else None
    except (TypeError, ValueError, json.JSONDecodeError):
        return None


def ensure_emission_snapshot(cert, user, cert_event, *, persist: bool = True) -> dict[str, Any]:
    """Devuelve snapshot guardado o crea uno legacy y opcionalmente persiste."""
    existing = parse_emission_snapshot(cert)
    if existing:
        return existing
    snap = legacy_emission_snapshot(cert, user, cert_event)
    if persist:
        cert.emission_snapshot = json.dumps(snap, ensure_ascii=False)
    return snap


def regenerate_one_membership_certificate(
    cert,
    cert_event,
    user,
    *,
    force: bool = False,
    persist_snapshot: bool = True,
    refresh_document: bool = True,
) -> tuple[bool, str | None]:
    """
    Reconfecciona un certificado de membresía con plantilla vigente.
    force=True siempre reescribe el PDF (regeneración admin).
    refresh_document=True actualiza document_id desde el perfil (cedula_or_passport).
    """
    from nodeone.modules.certificates import api_routes as routes

    if not force:
        from nodeone.services.certificate_http import resolve_membership_certificate_pdf_path

        if resolve_membership_certificate_pdf_path(cert.pdf_path, cert.certificate_code):
            return True, None

    snapshot = ensure_emission_snapshot(cert, user, cert_event, persist=persist_snapshot)
    if refresh_document:
        snapshot = refresh_snapshot_document_id(snapshot, user)
        if persist_snapshot:
            cert.emission_snapshot = json.dumps(snapshot, ensure_ascii=False)
    path = routes._regenerate_membership_certificate_pdf(
        cert, cert_event, user, emission_snapshot=snapshot, force=True
    )
    if not path:
        return False, 'No se pudo generar el PDF'
    return True, None


def regenerate_membership_certificates_for_format(cert_event, *, issued_by_user_id: int | None = None) -> dict:
    """
    Regenera todos los PDF emitidos de un formato de membresía.
    No borra filas ni cambia códigos; solo reconfecciona archivos.
    """
    from app import Certificate, User, db

    if not is_membership_certificate_format(cert_event):
        return {
            'found': 0,
            'regenerated': 0,
            'skipped': 0,
            'errors': ['El formato no es de membresía'],
            'elapsed_ms': 0,
        }

    t0 = time.perf_counter()
    rows = (
        Certificate.query.filter_by(certificate_event_id=int(cert_event.id))
        .order_by(Certificate.id.asc())
        .all()
    )
    found = len(rows)
    regenerated = 0
    skipped = 0
    errors: list[str] = []

    for cert in rows:
        user = User.query.get(cert.user_id)
        if user is None:
            skipped += 1
            if len(errors) < _MAX_ERRORS:
                errors.append(f'{cert.certificate_code}: usuario no encontrado')
            continue
        ok, err = regenerate_one_membership_certificate(
            cert, cert_event, user, force=True, persist_snapshot=True
        )
        if ok:
            regenerated += 1
            try:
                db.session.commit()
            except Exception as exc:
                db.session.rollback()
                regenerated -= 1
                skipped += 1
                if len(errors) < _MAX_ERRORS:
                    errors.append(f'{cert.certificate_code}: {exc}')
        else:
            skipped += 1
            if len(errors) < _MAX_ERRORS:
                label = cert.certificate_code or f'#{cert.id}'
                errors.append(f'{label}: {err or "error"}')

    elapsed_ms = int((time.perf_counter() - t0) * 1000)
    return {
        'found': found,
        'regenerated': regenerated,
        'skipped': skipped,
        'errors': errors,
        'elapsed_ms': elapsed_ms,
        'issued_by_user_id': issued_by_user_id,
    }
