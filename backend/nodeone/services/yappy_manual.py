"""Yappy manual (QR sin API): auditoría, emails y utilidades.

Un futuro webhook/API bancaria puede llamar a las mismas rutas de validación
o actualizar ``Payment.status`` siguiendo las reglas documentadas en el panel admin.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, List, Optional


def audit_log_list(payment) -> List[dict]:
    raw = getattr(payment, "yappy_manual_audit_json", None) or ""
    if not raw.strip():
        return []
    try:
        data = json.loads(raw)
        return data if isinstance(data, list) else []
    except Exception:
        return []


def append_yappy_manual_audit(payment, event: dict) -> None:
    """Añade un evento al JSON de auditoría (sin commit)."""
    log = audit_log_list(payment)
    entry = dict(event)
    entry.setdefault("at", datetime.utcnow().isoformat() + "Z")
    log.append(entry)
    payment.yappy_manual_audit_json = json.dumps(log, ensure_ascii=False)


def _split_admin_emails(config) -> List[str]:
    raw = (getattr(config, "yappy_manual_admin_emails", None) or "").strip()
    if not raw:
        return []
    return [e.strip() for e in raw.replace(";", ",").split(",") if e.strip()]


def _brand_name():
    import app as M

    try:
        return (M.app.config.get("APP_BRAND_NAME") or "Easy NodeOne").strip()
    except Exception:
        return "Easy NodeOne"


def _yappy_status_page_url(payment_id: int) -> str:
    try:
        from flask import url_for

        return url_for("payments_checkout.payment_yappy_manual_order_status", payment_id=payment_id, _external=True)
    except Exception:
        return f"/payment/yappy-manual/{int(payment_id)}/estado"


def _tx_email_html(title: str, inner: str, cta_url: str | None = None, cta_label: str | None = None) -> str:
    cta_block = ""
    if cta_url and cta_label:
        cta_block = (
            f'<p style="margin:20px 0 0;"><a href="{cta_url}" '
            'style="display:inline-block;background:#0d6efd;color:#ffffff;padding:12px 22px;'
            'border-radius:8px;text-decoration:none;font-weight:600;font-size:15px;">'
            f"{cta_label}</a></p>"
        )
    return f"""<!DOCTYPE html>
<html><body style="margin:0;padding:0;background:#f4f6f8;font-family:system-ui,Segoe UI,Roboto,sans-serif;">
<table width="100%" cellspacing="0" cellpadding="0" style="background:#f4f6f8;padding:24px 8px;"><tr><td align="center">
<table width="100%" cellspacing="0" cellpadding="0" style="max-width:560px;background:#ffffff;border-radius:12px;border:1px solid #e9ecef;overflow:hidden;">
<tr><td style="padding:24px 24px 8px;font-size:20px;font-weight:700;color:#212529;">{title}</td></tr>
<tr><td style="padding:8px 24px 24px;font-size:15px;line-height:1.55;color:#495057;">{inner}</td></tr>
<tr><td style="padding:0 24px 28px;">{cta_block}</td></tr>
</table></td></tr></table></body></html>"""


def _send_html(recipients: List[str], subject: str, html: str, **kwargs):
    import app as M

    if not recipients or not getattr(M, "EMAIL_TEMPLATES_AVAILABLE", False) or not getattr(M, "email_service", None):
        return
    for email in recipients:
        try:
            M.email_service.send_email(
                subject=subject,
                recipients=[email],
                html_content=html,
                **kwargs,
            )
        except Exception:
            pass


def notify_admin_new_receipt(payment, payer_user, config) -> None:
    import app as M

    recipients = _split_admin_emails(config)
    if not recipients:
        return
    amount = (payment.amount or 0) / 100.0
    ref = payment.payment_reference or ""
    link = ""
    try:
        from flask import url_for

        link = url_for("payments_admin.admin_yappy_manual_detail", payment_id=payment.id, _external=True)
    except Exception:
        link = f"/admin/payments/yappy-manual/{payment.id}"
    inner = f"""
    <p style="margin:0 0 12px;">El cliente <strong>{payer_user.first_name} {payer_user.last_name}</strong> ({payer_user.email})
    subió un comprobante.</p>
    <ul style="margin:0;padding-left:20px;">
      <li><strong>Pago ID:</strong> {payment.id}</li>
      <li><strong>Referencia:</strong> {ref}</li>
      <li><strong>Monto esperado:</strong> USD {amount:.2f}</li>
    </ul>
    """
    html = _tx_email_html("Nuevo comprobante Yappy", inner, link, "Revisar en el panel")
    _send_html(
        recipients,
        f"[{_brand_name()}] Nuevo comprobante Yappy — revisar",
        html,
        email_type="yappy_manual_admin_alert",
        related_entity_type="payment",
        related_entity_id=payment.id,
    )


def notify_client_receipt_received(payment, user) -> None:
    import app as M

    st_url = _yappy_status_page_url(payment.id)
    inner = f"""
    <p style="margin:0 0 12px;">Hola <strong>{user.first_name}</strong>,</p>
    <p style="margin:0 0 12px;">Recibimos tu comprobante para el pago <strong>#{payment.id}</strong>
    (referencia <code style="background:#f1f3f5;padding:2px 6px;border-radius:4px;">{payment.payment_reference or ''}</code>).</p>
    <p style="margin:0;"><strong>Estado:</strong> pendiente de validación por nuestro equipo.</p>
    <p style="margin:16px 0 0;">Te avisaremos por correo cuando sea revisado.</p>
    """
    html = _tx_email_html("Comprobante recibido", inner, st_url, "Ver estado del pedido")
    _send_html(
        [user.email],
        f"[{_brand_name()}] Comprobante recibido — pago pendiente de validación",
        html,
        email_type="yappy_manual_client_receipt",
        related_entity_type="payment",
        related_entity_id=payment.id,
        recipient_id=user.id,
        recipient_name=f"{user.first_name} {user.last_name}",
    )


def notify_client_approved(payment, user) -> None:
    import app as M

    inner = f"""
    <p style="margin:0 0 12px;">Hola <strong>{user.first_name}</strong>,</p>
    <p style="margin:0;">Tu pago Yappy <strong>#{payment.id}</strong> fue <strong>aprobado</strong>.</p>
    <p style="margin:16px 0 0;">Tu compra quedó activada según los productos que habías seleccionado.</p>
    """
    html = _tx_email_html("Pago confirmado", inner, None, None)
    _send_html(
        [user.email],
        f"[{_brand_name()}] Pago confirmado",
        html,
        email_type="yappy_manual_client_approved",
        related_entity_type="payment",
        related_entity_id=payment.id,
        recipient_id=user.id,
        recipient_name=f"{user.first_name} {user.last_name}",
    )


def notify_client_partial(payment, user, notes: Optional[str] = None) -> None:
    import app as M

    exp = (payment.amount or 0) / 100.0
    got = (payment.amount_received_cents or 0) / 100.0
    inner = f"""
    <p style="margin:0 0 12px;">Hola <strong>{user.first_name}</strong>,</p>
    <p style="margin:0 0 12px;">Revisamos tu comprobante del pago <strong>#{payment.id}</strong>.</p>
    <p style="margin:0 0 12px;">El monto recibido (<strong>USD {got:.2f}</strong>) es menor al esperado
    (<strong>USD {exp:.2f}</strong>). Tu compra <strong>no</strong> se activó.</p>
    {f'<p style="margin:0 0 12px;"><strong>Observaciones:</strong> {notes}</p>' if notes else ''}
    <p style="margin:0;">Puedes completar el saldo y contactarnos o iniciar un nuevo pago desde el checkout.</p>
    """
    html = _tx_email_html("Pago incompleto", inner, None, None)
    _send_html(
        [user.email],
        f"[{_brand_name()}] Pago incompleto",
        html,
        email_type="yappy_manual_client_partial",
        related_entity_type="payment",
        related_entity_id=payment.id,
        recipient_id=user.id,
        recipient_name=f"{user.first_name} {user.last_name}",
    )


def notify_client_rejected(payment, user, notes: Optional[str] = None) -> None:
    import app as M

    inner = f"""
    <p style="margin:0 0 12px;">Hola <strong>{user.first_name}</strong>,</p>
    <p style="margin:0 0 12px;">No pudimos validar el comprobante del pago <strong>#{payment.id}</strong>.</p>
    {f'<p style="margin:0 0 12px;"><strong>Motivo:</strong> {notes}</p>' if notes else ''}
    <p style="margin:0;">Si crees que es un error, responde a este correo o sube un nuevo comprobante desde la página de tu pago Yappy.</p>
    """
    st = _yappy_status_page_url(payment.id)
    html = _tx_email_html("Pago no aprobado", inner, st, "Ir a mi pago Yappy")
    _send_html(
        [user.email],
        f"[{_brand_name()}] Pago no aprobado — requiere revisión",
        html,
        email_type="yappy_manual_client_rejected",
        related_entity_type="payment",
        related_entity_id=payment.id,
        recipient_id=user.id,
        recipient_name=f"{user.first_name} {user.last_name}",
    )


def effective_yappy_display_name(config) -> str:
    """Nombre visible en checkout: yappy_display_name o, si vacío, yappy_business_name."""
    if not config:
        return ''
    dn = (getattr(config, 'yappy_display_name', None) or '').strip()
    if dn:
        return dn
    return ((getattr(config, 'yappy_business_name', None) or '') or '').strip()


def effective_yappy_instructions_html(config) -> str:
    """Texto/HTML de instrucciones: yappy_instructions o, si vacío, yappy_manual_instructions."""
    if not config:
        return ''
    yi = (getattr(config, 'yappy_instructions', None) or '').strip()
    if yi:
        return yi
    return ((getattr(config, 'yappy_manual_instructions', None) or '') or '').strip()


def notify_client_manual_review(payment, user, notes: Optional[str] = None) -> None:
    """Monto mayor al esperado u otro caso que requiere revisión antes de activar."""
    import app as M

    inner = f"""
    <p style="margin:0 0 12px;">Hola <strong>{user.first_name}</strong>,</p>
    <p style="margin:0 0 12px;">Tu comprobante del pago <strong>#{payment.id}</strong> está en <strong>revisión manual</strong>
    por un posible desajuste de monto u otra observación.</p>
    {f'<p style="margin:0 0 12px;"><strong>Detalle:</strong> {notes}</p>' if notes else ''}
    <p style="margin:0;">Te contactaremos cuando haya una resolución.</p>
    """
    html = _tx_email_html("Pago en revisión", inner, _yappy_status_page_url(payment.id), "Ver estado del pedido")
    _send_html(
        [user.email],
        f"[{_brand_name()}] Pago en revisión",
        html,
        email_type="yappy_manual_client_review",
        related_entity_type="payment",
        related_entity_id=payment.id,
        recipient_id=user.id,
        recipient_name=f"{user.first_name} {user.last_name}",
    )
