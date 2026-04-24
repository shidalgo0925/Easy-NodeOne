"""Acciones de negocio sobre ``ServiceRequest`` (vincular cita, cotización, factura)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from flask import session

from nodeone.core.db import db

if TYPE_CHECKING:
    from models.service_request import ServiceRequest


def _next_quotation_number(model, org_id: int) -> str:
    cnt = model.query.filter_by(organization_id=org_id).count() + 1
    return f'Q-{cnt:04d}'


def attach_pending_service_request_to_appointment(
    *,
    user_id: int,
    service_id: int,
    appointment_id: int,
    organization_id: int,
) -> None:
    """
    Toma ``session['pending_service_request_id']`` o la solicitud abierta más reciente
    (status ``requested``) y la vincula a la cita.
    """
    from models.service_request import ServiceRequest

    sr_id = session.pop('pending_service_request_id', None)
    sr = None
    if sr_id:
        sr = ServiceRequest.query.filter_by(id=int(sr_id)).first()
    if sr is None:
        sr = (
            ServiceRequest.query.filter_by(
                user_id=int(user_id),
                service_id=int(service_id),
                organization_id=int(organization_id),
                status='requested',
                appointment_id=None,
            )
            .order_by(ServiceRequest.id.desc())
            .first()
        )
    if sr is None:
        return
    if int(sr.user_id) != int(user_id) or int(sr.service_id) != int(service_id):
        return
    sr.appointment_id = int(appointment_id)
    sr.status = 'appointment_scheduled'
    db.session.add(sr)


def sync_service_request_on_quotation_created(quotation_id: int, service_request_id: int | None = None) -> None:
    from models.service_request import ServiceRequest

    if service_request_id:
        sr = ServiceRequest.query.filter_by(id=int(service_request_id)).first()
    else:
        sr = ServiceRequest.query.filter_by(quotation_id=int(quotation_id)).first()
    if not sr:
        return
    sr.quotation_id = int(quotation_id)
    if (sr.status or '') in ('requested', 'appointment_scheduled', 'in_consultation'):
        sr.status = 'quoted'
    db.session.add(sr)


def sync_service_request_on_quotation_confirmed(quotation_id: int) -> None:
    from models.service_request import ServiceRequest

    sr = ServiceRequest.query.filter_by(quotation_id=int(quotation_id)).first()
    if not sr:
        return
    prev = (sr.status or '').strip().lower()
    if prev in ('quoted', 'in_consultation'):
        sr.status = 'approved'
    db.session.add(sr)


def sync_service_request_on_invoice_from_quotation(quotation_id: int, invoice_id: int) -> None:
    from models.service_request import ServiceRequest

    sr = ServiceRequest.query.filter_by(quotation_id=int(quotation_id)).first()
    if not sr:
        return
    sr.invoice_id = int(invoice_id)
    if (sr.status or '').strip().lower() != 'cancelled':
        sr.status = 'in_progress'
    db.session.add(sr)


def create_quotation_for_appointment(
    *,
    appointment,
    actor_user_id: int | None,
) -> tuple[int | None, str | None]:
    """
    Crea borrador de cotización para el cliente de la cita y una línea con el servicio del catálogo.
    Devuelve (quotation_id, error_message).
    """
    from datetime import datetime as _dt

    from app import default_organization_id
    from models.catalog import Service
    from models.service_request import ServiceRequest
    from nodeone.modules.accounting.models import Tax
    from nodeone.modules.sales.models import Quotation, QuotationLine
    from nodeone.modules.sales.routes import _recompute_quote_totals

    oid = int(getattr(appointment, 'organization_id', None) or default_organization_id())
    appt_org = int(getattr(appointment, 'organization_id', None) or 0)
    if appt_org and appt_org != oid:
        return None, 'La cita no pertenece a la organización activa.'

    svc = None
    sid = getattr(appointment, 'service_id', None)
    if sid:
        svc = Service.query.filter_by(id=int(sid), organization_id=oid).first()

    sr = ServiceRequest.query.filter_by(appointment_id=int(appointment.id)).first()
    if svc is None:
        return None, 'La cita no tiene un servicio de catálogo vinculado (service_id).'
    if sr:
        from nodeone.services.service_request_integrity import assert_appointment_matches_service_request

        _m = assert_appointment_matches_service_request(appointment=appointment, service_request=sr)
        if _m:
            return None, f'Incoherencia solicitud/cita: {_m}'

    tax = Tax.query.filter_by(organization_id=oid).order_by(Tax.id.asc()).first()
    tax_id = tax.id if tax else None

    q = Quotation(
        organization_id=oid,
        number=_next_quotation_number(Quotation, oid),
        customer_id=int(appointment.user_id),
        crm_lead_id=(int(sr.crm_lead_id) if sr and sr.crm_lead_id else None),
        date=_dt.utcnow(),
        validity_date=None,
        payment_terms=None,
        status='draft',
        created_by=actor_user_id,
    )
    if getattr(appointment, 'advisor_id', None):
        from app import Advisor

        adv = Advisor.query.get(int(appointment.advisor_id))
        if adv and getattr(adv, 'user_id', None):
            q.salesperson_user_id = int(adv.user_id)
    db.session.add(q)
    db.session.flush()

    desc = (svc.name or 'Servicio').strip() or 'Servicio'
    if getattr(appointment, 'reference', None):
        desc = f'{desc} (cita {appointment.reference})'
    ln = QuotationLine(
        quotation_id=q.id,
        product_id=int(svc.id),
        description=desc,
        quantity=1.0,
        price_unit=float(svc.base_price or 0.0),
        tax_id=tax_id,
        subtotal=float(svc.base_price or 0.0),
        total=float(svc.base_price or 0.0),
    )
    db.session.add(ln)
    _recompute_quote_totals(q)

    if sr:
        sr.quotation_id = int(q.id)
        sr.status = 'quoted'
        db.session.add(sr)
    else:
        sr_new = ServiceRequest(
            organization_id=oid,
            user_id=int(appointment.user_id),
            service_id=int(svc.id),
            appointment_id=int(appointment.id),
            quotation_id=int(q.id),
            advisor_id=getattr(appointment, 'advisor_id', None),
            status='quoted',
            notes='Creado desde panel de citas.',
        )
        db.session.add(sr_new)

    db.session.commit()
    return int(q.id), None
