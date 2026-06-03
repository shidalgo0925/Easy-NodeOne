"""Flujo unificado: comprobante + validación admin + correo + notificación in-app.

Aplica a yappy_manual, wire_international, banco_general y manual_payment.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, List, Optional, Tuple

from nodeone.services.organization_payment_methods import (
    MANUAL_VALIDATION_METHOD_KEYS,
    METHOD_CATALOG,
    get_method_row,
)
from nodeone.services.yappy_manual import (
    YAPPY_MANUAL_EMAIL_FAILURE_USER_MESSAGE,
    append_yappy_manual_audit,
    notify_client_receipt_received,
    split_yappy_manual_admin_email_tokens,
)
from nodeone.services.yappy_manual_status import (
    is_pending_admin_review,
    is_pending_receipt,
)

# Reutilizado en UI y APIs
MANUAL_PAYMENT_EMAIL_FAILURE_USER_MESSAGE = YAPPY_MANUAL_EMAIL_FAILURE_USER_MESSAGE


def is_manual_validation_method(method_key: str | None) -> bool:
    return (method_key or '').strip() in MANUAL_VALIDATION_METHOD_KEYS


def method_display_label(method_key: str | None) -> str:
    key = (method_key or '').strip()
    meta = METHOD_CATALOG.get(key) or {}
    return meta.get('label') or key.replace('_', ' ').title()


def method_requires_receipt(organization_id: int, method_key: str) -> bool:
    row = get_method_row(int(organization_id), method_key)
    if row is not None:
        return bool(row.requires_receipt)
    return bool(METHOD_CATALOG.get(method_key, {}).get('requires_receipt', True))


def admin_review_detail_url(payment_id: int, payment_method: str | None = None) -> str:
    try:
        from flask import url_for

        return url_for('payments_admin.admin_yappy_manual_detail', payment_id=payment_id, _external=True)
    except Exception:
        return f'/admin/payments/yappy-manual/{int(payment_id)}'


def _split_admin_alert_emails(config) -> List[str]:
    if not config:
        return []
    return split_yappy_manual_admin_email_tokens(getattr(config, 'yappy_manual_admin_emails', None))


def _payment_org_id(payment) -> Optional[int]:
    oid = getattr(payment, 'organization_id', None)
    if oid is not None:
        return int(oid)
    try:
        import json

        raw = getattr(payment, 'payment_metadata', None) or ''
        if raw:
            meta = json.loads(raw)
            if isinstance(meta, dict) and meta.get('organization_id') is not None:
                return int(meta['organization_id'])
    except Exception:
        pass
    return None


def _users_to_notify_in_app(organization_id: Optional[int]) -> List[Any]:
    """Usuarios con permiso payments.manage o is_admin legacy (activos)."""
    import app as M

    users = M.User.query.filter_by(is_active=True).all()
    out: List[Any] = []
    seen: set[int] = set()
    for u in users:
        if u.id in seen:
            continue
        if organization_id is not None:
            u_org = getattr(u, 'organization_id', None)
            if u_org is not None and int(u_org) != int(organization_id):
                if not getattr(u, 'is_admin', False):
                    continue
        if getattr(u, 'is_admin', False) or u.has_permission('payments.manage'):
            out.append(u)
            seen.add(u.id)
    return out


def notify_admins_in_app(
    payment,
    *,
    title: str,
    message: str,
    notification_type: str = 'payment_admin_review',
) -> int:
    """Crea Notification por cada admin con payments.manage. Retorna cantidad creada."""
    import app as M

    oid = _payment_org_id(payment)
    admins = _users_to_notify_in_app(oid)
    if not admins:
        return 0
    link = admin_review_detail_url(payment.id, payment.payment_method)
    full_message = f'{message}\n\nRevisar: {link}'
    count = 0
    for admin in admins:
        n = M.Notification(
            user_id=admin.id,
            notification_type=notification_type,
            title=title,
            message=full_message,
        )
        M.db.session.add(n)
        count += 1
    return count


def notify_admin_email(payment, payer_user, config, *, event: str) -> bool:
    """Correo a yappy_manual_admin_emails (alertas de pagos manuales)."""
    from nodeone.services.yappy_manual import _brand_name, _log_yappy_email_issue, _send_html, _tx_email_html

    recipients = _split_admin_alert_emails(config)
    if not recipients:
        _log_yappy_email_issue(
            f"admin: lista de alertas vacía; payment_id={payment.id} event={event}"
        )
        return False
    amount = (payment.amount or 0) / 100.0
    ref = payment.payment_reference or ''
    client_name = f"{payer_user.first_name or ''} {payer_user.last_name or ''}".strip() or payer_user.email
    method_lbl = method_display_label(payment.payment_method)
    link = admin_review_detail_url(payment.id, payment.payment_method)

    if event == 'order_created':
        subject_title = f'Nuevo pedido pendiente — {method_lbl}'
        body_extra = 'El cliente inició un pago y debe adjuntar el comprobante (o está pendiente de revisión).'
        email_type = 'manual_payment_admin_order'
    else:
        subject_title = f'Nuevo comprobante pendiente de validación — {method_lbl}'
        body_extra = 'El cliente subió un comprobante. Requiere validación administrativa antes de activar la compra.'
        email_type = 'manual_payment_admin_receipt'

    inner = f"""
    <p style="margin:0 0 16px;line-height:1.6;">
      <strong>Cliente:</strong> {client_name}<br>
      <strong>Pedido:</strong> #{payment.id}<br>
      <strong>Monto:</strong> USD {amount:.2f}<br>
      <strong>Método:</strong> {method_lbl}
    </p>
    <p style="margin:0 0 16px;">{body_extra}</p>
    <p style="margin:0 0 8px;"><strong>Referencia:</strong>
      <code style="background:#f1f3f5;padding:2px 6px;border-radius:4px;">{ref}</code></p>
    """
    html = _tx_email_html(subject_title, inner, link, 'Revisar en el panel')
    return bool(
        _send_html(
            recipients,
            f"[{_brand_name()}] {subject_title}",
            html,
            email_type=email_type,
            related_entity_type='payment',
            related_entity_id=payment.id,
        )
    )


def notify_after_manual_payment_event(
    payment,
    payer_user,
    config,
    *,
    event: str,
) -> Tuple[bool, bool]:
    """
    event: 'order_created' | 'receipt_submitted'
    Retorna (email_ok, in_app_count > 0 como bool simplificado).
    """
    email_ok = True
    if event == 'receipt_submitted':
        email_ok = bool(notify_admin_email(payment, payer_user, config, event=event))
        if payer_user:
            email_ok = bool(notify_client_receipt_received(payment, payer_user)) and email_ok
    elif event == 'order_created':
        if is_pending_admin_review(payment.status):
            email_ok = bool(notify_admin_email(payment, payer_user, config, event='receipt_submitted'))
        else:
            email_ok = bool(notify_admin_email(payment, payer_user, config, event='order_created'))

    if event == 'receipt_submitted':
        title = f'Comprobante pendiente — pedido #{payment.id}'
        msg = (
            f'{payer_user.first_name or ""} {payer_user.last_name or ""}'.strip()
            or payer_user.email
        )
        msg = f'Nuevo comprobante ({method_display_label(payment.payment_method)}). Cliente: {msg}. Monto USD {(payment.amount or 0) / 100:.2f}.'
    else:
        title = f'Pago pendiente — pedido #{payment.id}'
        msg = (
            f'Nuevo pedido {method_display_label(payment.payment_method)} '
            f'(ref. {payment.payment_reference or "—"}). '
            f'Monto USD {(payment.amount or 0) / 100:.2f}.'
        )
    in_app = notify_admins_in_app(payment, title=title, message=msg) > 0
    return email_ok, in_app


def resolve_initial_status(
    organization_id: int,
    method_key: str,
    *,
    has_receipt: bool,
) -> str:
    """Estado tras crear pedido en checkout (sin auto-aprobación)."""
    if has_receipt:
        return 'pending_admin_review'
    if method_requires_receipt(organization_id, method_key):
        return 'pending_receipt'
    return 'pending_admin_review'


def email_warning_if_needed(mail_flags: List[bool]) -> Optional[str]:
    if mail_flags and not all(mail_flags):
        return MANUAL_PAYMENT_EMAIL_FAILURE_USER_MESSAGE
    return None


# Alias de auditoría (campo legacy yappy_manual_audit_json)
append_payment_audit = append_yappy_manual_audit
