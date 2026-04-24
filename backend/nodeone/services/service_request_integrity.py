"""
Validaciones de coherencia para ``ServiceRequest`` y herramienta de auditoría.
"""

from __future__ import annotations

from typing import Any


def validate_service_request_for_quotation(
    *,
    service_request,
    customer_id: int,
    line_rows: list[dict[str, Any]] | None,
) -> str | None:
    """
    Devuelve código de error o None si OK.
    ``line_rows``: filas de ``data['lines']`` en POST cotización.
    """
    if service_request is None:
        return 'service_request_missing'
    if int(service_request.user_id) != int(customer_id):
        return 'service_request_user_mismatch'
    pids = []
    for row in line_rows or []:
        if row.get('is_note'):
            continue
        pid = row.get('product_id')
        if pid is not None:
            try:
                pids.append(int(pid))
            except (TypeError, ValueError):
                continue
    if pids and int(service_request.service_id) not in pids:
        return 'service_request_service_mismatch'
    return None


def assert_appointment_matches_service_request(
    *,
    appointment,
    service_request,
) -> str | None:
    if not appointment or not service_request:
        return 'missing'
    if int(appointment.user_id) != int(service_request.user_id):
        return 'appointment_user_mismatch'
    if appointment.service_id and int(appointment.service_id) != int(service_request.service_id):
        return 'appointment_service_mismatch'
    return None


def run_integrity_check(printfn=print) -> int:
    """Retorna 0 si no hay problemas, 1 si hay advertencias/errores."""
    from app import Appointment, default_organization_id
    from models.service_request import ServiceRequest
    from nodeone.core.db import db

    issues = 0
    try:
        org = int(default_organization_id())
    except Exception:
        org = 1

    for sr in ServiceRequest.query.filter_by(organization_id=org).all():
        st = (sr.status or '').lower()
        if st in ('cancelled',):
            continue
        if st in ('quoted', 'approved', 'in_progress', 'completed') and not sr.quotation_id:
            printfn(f'[WARN] service_request id={sr.id} status={st!r} sin quotation_id')
            issues += 1
        if st in (
            'appointment_scheduled',
            'in_consultation',
            'quoted',
            'approved',
            'in_progress',
            'completed',
        ) and not sr.appointment_id:
            printfn(f'[WARN] service_request id={sr.id} status={st!r} sin appointment_id')
            issues += 1
        if sr.appointment_id:
            apt = Appointment.query.get(int(sr.appointment_id))
            if not apt:
                printfn(f'[ERR] service_request id={sr.id} appointment_id={sr.appointment_id} inexistente')
                issues += 1
            else:
                err = assert_appointment_matches_service_request(appointment=apt, service_request=sr)
                if err:
                    printfn(f'[ERR] service_request id={sr.id} cita {apt.id}: {err}')
                    issues += 1
    db.session.rollback()
    if issues:
        printfn(f'Resumen: {issues} incidencia(s) (org {org}).')
        return 1
    printfn('OK: sin incidencias obvias de integridad (service_request).')
    return 0
