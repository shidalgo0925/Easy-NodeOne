"""Estados operativos de pagos pendientes (integraciones + Yappy manual)."""

from __future__ import annotations

from nodeone.services.yappy_manual_status import (
    PENDING_ADMIN_REVIEW_STATUSES,
    PENDING_RECEIPT_STATUSES,
    is_pending_admin_review,
    is_pending_receipt,
    yappy_status_label,
)

# PayPal / transferencia / demo checkout
INTEGRATION_PENDING_STATUSES = frozenset(('pending', 'awaiting_confirmation'))

# Todos los estados que el miembro debe ver como «pago en curso»
MEMBER_PENDING_PAYMENT_STATUSES = frozenset(
    INTEGRATION_PENDING_STATUSES
    | PENDING_RECEIPT_STATUSES
    | PENDING_ADMIN_REVIEW_STATUSES
    | frozenset(('manual_review', 'partially_paid'))
)

# Cola admin general (OCR / transferencias legacy)
ADMIN_OCR_PENDING_STATUSES = frozenset(('pending',))
ADMIN_OCR_REVIEW_STATUSES = frozenset(('pending', 'needs_review'))

# Cola Yappy manual (panel dedicado)
ADMIN_YAPPY_OPEN_STATUSES = frozenset(
    PENDING_RECEIPT_STATUSES
    | PENDING_ADMIN_REVIEW_STATUSES
    | frozenset(('manual_review', 'partially_paid'))
)


def is_member_pending_payment(status: str | None, payment_method: str | None = None) -> bool:
    st = (status or '').strip()
    if st in MEMBER_PENDING_PAYMENT_STATUSES:
        return True
    if (payment_method or '').strip() == 'yappy_manual' and st in ('rejected',):
        return False
    return False


def member_pending_action_url(payment_id: int, payment_method: str | None, status: str | None) -> str:
    """URL donde el usuario continúa el flujo según método y estado."""
    from flask import url_for

    method = (payment_method or '').strip()
    st = (status or '').strip()
    if method == 'yappy_manual':
        if is_pending_receipt(st) or st == 'rejected':
            return url_for('payments_checkout.payment_yappy_manual_instructions', payment_id=int(payment_id))
        return url_for('payments_checkout.payment_yappy_manual_order_status', payment_id=int(payment_id))
    return url_for('payments_checkout.payment_status', payment_id=int(payment_id))


def member_pending_status_label(status: str | None, payment_method: str | None = None) -> str:
    method = (payment_method or '').strip()
    if method == 'yappy_manual':
        return yappy_status_label(status)
    st = (status or '').strip()
    if st == 'awaiting_confirmation':
        return 'Esperando confirmación'
    if st == 'pending':
        return 'Pendiente'
    return st or '—'
