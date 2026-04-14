"""Notificaciones transaccionales para ventas/accounting."""

from __future__ import annotations

import html as html_module
import logging
import os
import re
from typing import Any

logger = logging.getLogger(__name__)

_MAX_ATTACHMENTS = 35
_MAX_BYTES_PER_FILE = 4 * 1024 * 1024
_MAX_TOTAL_ATTACH_BYTES = 18 * 1024 * 1024

_COND_ES = {
    'ok': 'OK',
    'leve': 'Leve',
    'medio': 'Medio',
    'severo': 'Severo',
}
_DAMAGE_ES = {
    'scratch': 'Rayón',
    'swirl': 'Swirl',
    'dent': 'Golpe / abolladura',
    'stain': 'Mancha',
    'chip': 'Descascarado',
}
_SEV_ES = {'low': 'baja', 'medium': 'media', 'high': 'alta'}


def _h(s: Any) -> str:
    return html_module.escape(str(s) if s is not None else '', quote=False)


def _fs_from_static_url(url: str) -> str | None:
    if not url or not isinstance(url, str):
        return None
    if '/..' in url or url.startswith('//'):
        return None
    u = url.split('?', 1)[0].strip()
    if not u.startswith('/static/'):
        return None
    rel = u[len('/static/') :].lstrip('/').replace('/', os.sep)
    try:
        from flask import current_app

        static_folder = os.path.abspath(current_app.static_folder)
        full = os.path.abspath(os.path.join(static_folder, rel))
        common = os.path.commonpath([static_folder, full])
        if common != static_folder:
            return None
    except (ValueError, RuntimeError, OSError):
        return None
    return full if os.path.isfile(full) else None


def _read_attachment_candidate(url: str, filename: str) -> dict[str, Any] | None:
    path = _fs_from_static_url(url)
    if not path:
        return None
    try:
        sz = os.path.getsize(path)
        if sz > _MAX_BYTES_PER_FILE or sz < 1:
            return None
        with open(path, 'rb') as f:
            data = f.read()
    except OSError as e:
        logger.warning('No se pudo leer adjunto taller %s: %s', path, e)
        return None
    ext = os.path.splitext(path)[1].lower() or '.jpg'
    safe_fn = re.sub(r'[^a-zA-Z0-9._-]', '_', filename) or f'foto{ext}'
    if not safe_fn.lower().endswith(('.jpg', '.jpeg', '.png', '.webp', '.gif')):
        safe_fn = f'{safe_fn}{ext}'
    return {'filename': safe_fn, 'content_type': '', 'data': data}


def _workshop_addon_html_and_attachments(quotation) -> tuple[str, list[dict[str, Any]], str]:
    """
    Si existe orden de taller vinculada a esta cotización, devuelve (html, attachments, nota_pie).
    """
    from nodeone.modules.workshop.models import (
        VehicleInspectionPhoto,
        VehicleInspectionPoint,
        VehicleZone,
        WorkshopChecklistItem,
        WorkshopInspection,
        WorkshopLine,
        WorkshopOrder,
        WorkshopPhoto,
        WorkshopVehicle,
    )

    order = (
        WorkshopOrder.query.filter_by(
            quotation_id=quotation.id,
            organization_id=quotation.organization_id,
        )
        .order_by(WorkshopOrder.id.desc())
        .first()
    )
    if not order:
        return '', [], ''

    vehicle = WorkshopVehicle.query.filter_by(id=order.vehicle_id).first()
    v = vehicle
    veh_lines: list[str] = []
    if v:
        if getattr(v, 'plate', None):
            veh_lines.append(f"Placa: {_h(v.plate)}")
        parts = [x for x in [getattr(v, 'brand', '') or '', getattr(v, 'model', '') or ''] if x]
        if parts:
            veh_lines.append(_h(' '.join(parts).strip()))
        if getattr(v, 'year', None):
            veh_lines.append(f"Año: {_h(v.year)}")
        if getattr(v, 'color', None):
            veh_lines.append(f"Color: {_h(v.color)}")
        if getattr(v, 'mileage', None) is not None and float(v.mileage or 0) > 0:
            veh_lines.append(f"Kilometraje: {_h(v.mileage)}")
        if getattr(v, 'vin', None):
            veh_lines.append(f"VIN: {_h(v.vin)}")
    veh_block = '<br>'.join(veh_lines) if veh_lines else '—'

    lines_html = ''
    wlines = WorkshopLine.query.filter_by(order_id=order.id).order_by(WorkshopLine.id).all()
    if wlines:
        rows = []
        for ln in wlines:
            rows.append(
                '<tr>'
                f'<td>{_h(ln.description or "")}</td>'
                f'<td style="text-align:right">{float(ln.quantity or 0):.2f}</td>'
                f'<td style="text-align:right">B/. {float(ln.price_unit or 0):.2f}</td>'
                f'<td style="text-align:right">B/. {float(ln.total or 0):.2f}</td>'
                '</tr>'
            )
        lines_html = (
            '<h3 style="margin:1.25em 0 0.5em;font-size:1rem">Líneas de la orden de trabajo</h3>'
            '<table style="border-collapse:collapse;width:100%;font-size:0.9rem" border="1" cellpadding="6">'
            '<thead><tr style="background:#f3f4f6"><th>Descripción</th><th>Cant.</th><th>Precio u.</th><th>Total</th></tr></thead>'
            f'<tbody>{"".join(rows)}</tbody></table>'
        )

    chk_html = ''
    chrows = WorkshopChecklistItem.query.filter_by(order_id=order.id).order_by(WorkshopChecklistItem.id).all()
    if chrows:
        crows = []
        for c in chrows:
            cond = _COND_ES.get((c.condition or 'ok').lower(), _h(c.condition or ''))
            note = (c.notes or '').strip()
            crows.append(
                '<tr>'
                f'<td>{_h(c.item or "")}</td>'
                f'<td>{_h(cond)}</td>'
                f'<td>{_h(note) if note else "—"}</td>'
                '</tr>'
            )
        chk_html = (
            '<h3 style="margin:1.25em 0 0.5em;font-size:1rem">Checklist de recepción</h3>'
            '<table style="border-collapse:collapse;width:100%;font-size:0.9rem" border="1" cellpadding="6">'
            '<thead><tr style="background:#f3f4f6"><th>Ítem</th><th>Condición</th><th>Notas</th></tr></thead>'
            f'<tbody>{"".join(crows)}</tbody></table>'
        )

    insp_html = ''
    zone_names: dict[str, str] = {}
    insp = WorkshopInspection.query.filter_by(order_id=order.id).first()
    if insp:
        pts = VehicleInspectionPoint.query.filter_by(inspection_id=insp.id).order_by(VehicleInspectionPoint.id).all()
        codes = list({p.zone_code for p in pts if p.zone_code})
        if codes:
            for z in VehicleZone.query.filter(VehicleZone.code.in_(codes)).all():
                zone_names[z.code] = z.name or z.code
        if pts:
            pr = []
            for p in pts:
                zlab = _h(zone_names.get(p.zone_code, p.zone_code or ''))
                dt = _DAMAGE_ES.get((p.damage_type or '').lower(), _h(p.damage_type or ''))
                sev = _SEV_ES.get((p.severity or 'low').lower(), _h(p.severity or ''))
                note = (p.notes or '').strip()
                pr.append(
                    '<tr>'
                    f'<td>{zlab}</td>'
                    f'<td>{dt}</td>'
                    f'<td>{_h(sev)}</td>'
                    f'<td>{_h(note) if note else "—"}</td>'
                    '</tr>'
                )
            insp_html = (
                '<h3 style="margin:1.25em 0 0.5em;font-size:1rem">Inspección (body map)</h3>'
                '<table style="border-collapse:collapse;width:100%;font-size:0.9rem" border="1" cellpadding="6">'
                '<thead><tr style="background:#f3f4f6"><th>Zona</th><th>Tipo</th><th>Severidad</th><th>Notas</th></tr></thead>'
                f'<tbody>{"".join(pr)}</tbody></table>'
            )
        if (insp.notes or '').strip():
            insp_html += f'<p style="margin-top:0.5em"><strong>Notas inspección:</strong> {_h(insp.notes)}</p>'

    notes_parts = []
    if (order.notes or '').strip():
        notes_parts.append(f'<p><strong>Notas orden:</strong> {_h(order.notes)}</p>')
    if (order.qc_notes or '').strip():
        notes_parts.append(f'<p><strong>Notas control de calidad:</strong> {_h(order.qc_notes)}</p>')
    notes_html = ''.join(notes_parts)

    section = (
        '<hr style="margin:1.5em 0;border:none;border-top:1px solid #dee2e6">'
        '<h2 style="margin:0 0 0.5em;font-size:1.1rem;color:#1a3dcc">Orden de trabajo '
        f'{_h(order.code)}</h2>'
        f'<p style="margin:0.35em 0"><strong>Vehículo</strong><br>{veh_block}</p>'
        f'{notes_html}'
        f'{lines_html}'
        f'{chk_html}'
        f'{insp_html}'
        '<p style="margin-top:1em;font-size:0.85rem;color:#6c757d">Las fotos de la orden e inspección se envían como archivos adjuntos.</p>'
    )

    attachments: list[dict[str, Any]] = []
    total_bytes = 0
    n = 0
    code_safe = re.sub(r'[^a-zA-Z0-9_-]', '_', order.code or str(order.id))[:40]

    def try_add(url: str, fname: str) -> bool:
        nonlocal total_bytes, n
        if n >= _MAX_ATTACHMENTS or total_bytes >= _MAX_TOTAL_ATTACH_BYTES:
            return False
        att = _read_attachment_candidate(url, fname)
        if not att:
            return False
        sz = len(att['data'])
        if total_bytes + sz > _MAX_TOTAL_ATTACH_BYTES:
            return False
        attachments.append(att)
        total_bytes += sz
        n += 1
        return True

    for i, ph in enumerate(
        WorkshopPhoto.query.filter_by(order_id=order.id).order_by(WorkshopPhoto.id.asc()).all(), start=1
    ):
        ext = os.path.splitext((ph.url or '').split('/')[-1])[1] or '.jpg'
        try_add(ph.url or '', f'{code_safe}-orden-foto-{i}{ext}')

    if insp:
        iphoto_i = 0
        for p in VehicleInspectionPoint.query.filter_by(inspection_id=insp.id).order_by(VehicleInspectionPoint.id).all():
            for ph in VehicleInspectionPhoto.query.filter_by(point_id=p.id).order_by(VehicleInspectionPhoto.id).all():
                iphoto_i += 1
                ext = os.path.splitext((ph.url or '').split('/')[-1])[1] or '.jpg'
                z = re.sub(r'[^a-zA-Z0-9_-]', '_', p.zone_code or 'z')[:20]
                try_add(
                    ph.url or '',
                    f'{code_safe}-inspeccion-{z}-{iphoto_i}{ext}',
                )

    total_wp = WorkshopPhoto.query.filter_by(order_id=order.id).count()
    total_vip = 0
    if insp:
        total_vip = (
            VehicleInspectionPhoto.query.join(
                VehicleInspectionPoint,
                VehicleInspectionPhoto.point_id == VehicleInspectionPoint.id,
            )
            .filter(VehicleInspectionPoint.inspection_id == insp.id)
            .count()
        )
    expected_photos = total_wp + total_vip
    note_pie = ''
    if expected_photos > len(attachments):
        note_pie = (
            f'<p style="font-size:0.8rem;color:#856404">Fotos: se adjuntaron {len(attachments)} archivo(s) de '
            f'{expected_photos} disponible(s) (límite de tamaño del correo).</p>'
        )

    return section, attachments, note_pie


def send_quotation_email(
    quotation,
    customer,
    html_body=None,
    subject=None,
    recipients=None,
    extra_attachments=None,
):
    import app as M

    nombre = (
        f"{getattr(customer, 'first_name', '') or ''} {getattr(customer, 'last_name', '') or ''}"
    ).strip() or 'Cliente'
    total = float(quotation.grand_total or 0)
    subj = (subject or '').strip() or f'Cotización {quotation.number}'
    base = html_body or (
        f"<p>Hola {_h(nombre)},</p>"
        f"<p>Le enviamos la cotización <strong>{_h(quotation.number)}</strong> por un importe de "
        f"<strong>B/. {total:.2f}</strong>.</p>"
        f"<p>No dude en ponerse en contacto con nosotros si tiene alguna pregunta.</p>"
        f"<p style='color:#6c757d;font-size:0.9em'>— Este mensaje se envió automáticamente desde la plataforma.</p>"
    )

    extra_html, attachments, limit_note = _workshop_addon_html_and_attachments(quotation)
    body = base + extra_html + limit_note

    rec = recipients if recipients else [customer.email]
    att = []
    if extra_attachments:
        att.extend([x for x in extra_attachments if isinstance(x, dict)])
    if attachments:
        att.extend(attachments)

    if not M.email_service:
        return False, 'email_service_unavailable'
    try:
        M.email_service.send_email(
            subject=subj,
            recipients=rec,
            html_content=body,
            email_type='quotation_sent',
            related_entity_type='quotation',
            related_entity_id=quotation.id,
            recipient_id=customer.id,
            recipient_name=f"{getattr(customer, 'first_name', '')} {getattr(customer, 'last_name', '')}".strip(),
            attachments=att or None,
        )
        return True, None
    except Exception as e:
        return False, str(e)
