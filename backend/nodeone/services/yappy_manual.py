"""Yappy manual (QR sin API): auditoría, emails y utilidades.

Un futuro webhook/API bancaria puede llamar a las mismas rutas de validación
o actualizar ``Payment.status`` siguiendo las reglas documentadas en el panel admin.
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any, List, Optional, Tuple

# Validación simple de correo (config admin Yappy manual); suficiente para bloquear typos obvios.
_EMAIL_ADDR_RE = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,63}$")

# Mensaje unificado para UI/API cuando el flujo guardó pero falló al menos un correo.
YAPPY_MANUAL_EMAIL_FAILURE_USER_MESSAGE = (
    "Pago procesado, pero no se pudo enviar el correo de notificación."
)


def split_yappy_manual_admin_email_tokens(raw: str | None) -> List[str]:
    """Tokens separados por coma o punto y coma (sin validar formato)."""
    if not raw or not str(raw).strip():
        return []
    s = str(raw).strip().replace(";", ",")
    return [p.strip() for p in s.split(",") if p.strip()]


def validate_yappy_manual_admin_emails_when_enabled(raw: str | None) -> Tuple[List[str], Optional[str]]:
    """
    Si Yappy manual está habilitado, la lista de correos admin es obligatoria y debe ser válida.
    Retorna (lista normalizada, mensaje de error en español o None si OK).
    """
    parts = split_yappy_manual_admin_email_tokens(raw)
    if not parts:
        return [], "Con Yappy manual activado, debés indicar al menos un correo en «Correos para alertas»."
    normalized: List[str] = []
    for p in parts:
        if not _EMAIL_ADDR_RE.match(p):
            return [], f"Correo inválido en la lista de alertas: {p!r}. Revisá el formato (ej. pagos@empresa.com)."
        low = p.lower()
        if low not in [x.lower() for x in normalized]:
            normalized.append(p)
    return normalized, None


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
    return split_yappy_manual_admin_email_tokens(raw)


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


def _log_yappy_email_issue(message: str) -> None:
    try:
        from flask import current_app, has_request_context

        if has_request_context():
            current_app.logger.warning("yappy_manual email: %s", message)
            return
    except Exception:
        pass
    try:
        print(f"yappy_manual email: {message}")
    except Exception:
        pass


def _send_html(recipients: List[str], subject: str, html: str, **kwargs) -> bool:
    """Envía HTML a cada destinatario. True solo si todos los envíos tuvieron éxito."""
    import app as M

    if not recipients:
        _log_yappy_email_issue(f"sin destinatarios; asunto={subject!r}")
        return False
    if not getattr(M, "EMAIL_TEMPLATES_AVAILABLE", False) or not getattr(M, "email_service", None):
        _log_yappy_email_issue(
            f"servicio de correo no disponible (EMAIL_TEMPLATES_AVAILABLE / email_service); asunto={subject!r}"
        )
        return False
    all_ok = True
    for email in recipients:
        try:
            M.email_service.send_email(
                subject=subject,
                recipients=[email],
                html_content=html,
                **kwargs,
            )
        except Exception as exc:
            _log_yappy_email_issue(f"fallo al enviar a {email!r}: {exc!r}; asunto={subject!r}")
            all_ok = False
    return all_ok


def notify_admin_new_receipt(payment, payer_user, config) -> bool:
    recipients = _split_admin_emails(config)
    if not recipients:
        _log_yappy_email_issue(
            "admin: lista yappy_manual_admin_emails vacía; no se envía aviso de comprobante "
            f"(payment_id={payment.id})"
        )
        return False
    amount = (payment.amount or 0) / 100.0
    ref = payment.payment_reference or ""
    client_name = f"{payer_user.first_name or ''} {payer_user.last_name or ''}".strip() or payer_user.email
    link = ""
    try:
        from flask import url_for

        link = url_for("payments_admin.admin_yappy_manual_detail", payment_id=payment.id, _external=True)
    except Exception:
        link = f"/admin/payments/yappy-manual/{payment.id}"
    inner = f"""
    <p style="margin:0 0 16px;line-height:1.6;">
      <strong>Cliente:</strong> {client_name}<br>
      <strong>Pedido:</strong> #{payment.id}<br>
      <strong>Monto:</strong> USD {amount:.2f}<br>
      <strong>Método:</strong> Yappy Manual
    </p>
    <p style="margin:0 0 16px;">El cliente ha subido un comprobante de pago y está pendiente de validación administrativa.</p>
    <p style="margin:0 0 8px;"><strong>Referencia de pago:</strong> <code style="background:#f1f3f5;padding:2px 6px;border-radius:4px;">{ref}</code></p>
    """
    html = _tx_email_html("Nuevo comprobante Yappy pendiente de validación", inner, link, "Revisar en el panel")
    return bool(
        _send_html(
            recipients,
            f"[{_brand_name()}] Nuevo comprobante Yappy pendiente de validación",
            html,
            email_type="yappy_manual_admin_alert",
            related_entity_type="payment",
            related_entity_id=payment.id,
        )
    )


def notify_client_receipt_received(payment, user) -> bool:
    st_url = _yappy_status_page_url(payment.id)
    inner = f"""
    <p style="margin:0 0 12px;">Hola <strong>{user.first_name}</strong>,</p>
    <p style="margin:0 0 12px;">Hemos recibido tu comprobante (pedido <strong>#{payment.id}</strong>,
    referencia <code style="background:#f1f3f5;padding:2px 6px;border-radius:4px;">{payment.payment_reference or ''}</code>).</p>
    <p style="margin:0 0 12px;">Tu pago será revisado por administración.</p>
    <p style="margin:0;">Te avisaremos por correo cuando haya una resolución.</p>
    """
    html = _tx_email_html("Comprobante recibido", inner, st_url, "Ver estado del pedido")
    if not (user.email or "").strip():
        _log_yappy_email_issue(f"cliente sin email; payment_id={payment.id}")
        return False
    return bool(
        _send_html(
            [user.email],
            f"[{_brand_name()}] Hemos recibido tu comprobante",
            html,
            email_type="yappy_manual_client_receipt",
            related_entity_type="payment",
            related_entity_id=payment.id,
            recipient_id=user.id,
            recipient_name=f"{user.first_name} {user.last_name}",
        )
    )


def notify_client_approved(payment, user) -> bool:
    inner = f"""
    <p style="margin:0 0 12px;">Hola <strong>{user.first_name}</strong>,</p>
    <p style="margin:0 0 12px;">Tu pago ha sido aprobado correctamente (pedido <strong>#{payment.id}</strong>).</p>
    <p style="margin:0;">Tu compra quedó activada según los productos que habías seleccionado.</p>
    """
    html = _tx_email_html("Pago aprobado", inner, None, None)
    if not (user.email or "").strip():
        _log_yappy_email_issue(f"cliente sin email; payment_id={payment.id}")
        return False
    return bool(
        _send_html(
            [user.email],
            f"[{_brand_name()}] Tu pago ha sido aprobado",
            html,
            email_type="yappy_manual_client_approved",
            related_entity_type="payment",
            related_entity_id=payment.id,
            recipient_id=user.id,
            recipient_name=f"{user.first_name} {user.last_name}",
        )
    )


def notify_client_partial(payment, user, notes: Optional[str] = None) -> bool:
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
    if not (user.email or "").strip():
        _log_yappy_email_issue(f"cliente sin email; payment_id={payment.id}")
        return False
    return bool(
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
    )


def notify_client_rejected(payment, user, notes: Optional[str] = None) -> bool:
    inner = f"""
    <p style="margin:0 0 12px;">Hola <strong>{user.first_name}</strong>,</p>
    <p style="margin:0 0 12px;">Tu comprobante fue rechazado (pedido <strong>#{payment.id}</strong>).</p>
    {f'<p style="margin:0 0 12px;"><strong>Observaciones:</strong> {notes}</p>' if notes else ''}
    <p style="margin:0 0 12px;">Por favor contacte administración o suba un nuevo comprobante.</p>
    <p style="margin:0;">Puedes intentar de nuevo desde la página de tu pago Yappy.</p>
    """
    st = _yappy_status_page_url(payment.id)
    html = _tx_email_html("Comprobante no aprobado", inner, st, "Ir a mi pago Yappy")
    if not (user.email or "").strip():
        _log_yappy_email_issue(f"cliente sin email; payment_id={payment.id}")
        return False
    return bool(
        _send_html(
            [user.email],
            f"[{_brand_name()}] Tu comprobante fue rechazado",
            html,
            email_type="yappy_manual_client_rejected",
            related_entity_type="payment",
            related_entity_id=payment.id,
            recipient_id=user.id,
            recipient_name=f"{user.first_name} {user.last_name}",
        )
    )


def effective_yappy_display_name(config) -> str:
    """Nombre visible en checkout: yappy_display_name o, si vacío, yappy_business_name."""
    if not config:
        return ''
    dn = (getattr(config, 'yappy_display_name', None) or '').strip()
    if dn:
        return dn
    return ((getattr(config, 'yappy_business_name', None) or '') or '').strip()


def effective_yappy_phone_or_identifier(config) -> str:
    """Teléfono/identificador para checkout y validación: yappy_phone_or_identifier o teléfono del comercio."""
    if not config:
        return ''
    a = (getattr(config, 'yappy_phone_or_identifier', None) or '').strip()
    if a:
        return a
    return ((getattr(config, 'yappy_merchant_phone', None) or '') or '').strip()


def effective_yappy_instructions_html(config) -> str:
    """Texto/HTML de instrucciones: yappy_instructions o, si vacío, yappy_manual_instructions."""
    if not config:
        return ''
    yi = (getattr(config, 'yappy_instructions', None) or '').strip()
    if yi:
        return yi
    return ((getattr(config, 'yappy_manual_instructions', None) or '') or '').strip()


def notify_client_manual_review(payment, user, notes: Optional[str] = None) -> bool:
    """Monto mayor al esperado u otro caso que requiere revisión antes de activar."""
    inner = f"""
    <p style="margin:0 0 12px;">Hola <strong>{user.first_name}</strong>,</p>
    <p style="margin:0 0 12px;">Tu comprobante del pago <strong>#{payment.id}</strong> está en <strong>revisión manual</strong>
    por un posible desajuste de monto u otra observación.</p>
    {f'<p style="margin:0 0 12px;"><strong>Detalle:</strong> {notes}</p>' if notes else ''}
    <p style="margin:0;">Te contactaremos cuando haya una resolución.</p>
    """
    html = _tx_email_html("Pago en revisión", inner, _yappy_status_page_url(payment.id), "Ver estado del pedido")
    if not (user.email or "").strip():
        _log_yappy_email_issue(f"cliente sin email; payment_id={payment.id}")
        return False
    return bool(
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
    )
