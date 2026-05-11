from __future__ import annotations

"""Estados Yappy manual (directorio + comprobante + validación admin).

Compatibilidad: se aceptan nombres legacy ``pending_payment`` / ``pending_validation``
junto a los nuevos ``pending_receipt`` / ``pending_admin_review``.
"""

# Tras crear la orden: usuario aún no sube comprobante
PENDING_RECEIPT_STATUSES = frozenset(('pending_receipt', 'pending_payment'))

# Comprobante recibido, esperando admin
PENDING_ADMIN_REVIEW_STATUSES = frozenset(('pending_admin_review', 'pending_validation'))


def is_pending_receipt(status: str | None) -> bool:
    return (status or '').strip() in PENDING_RECEIPT_STATUSES


def is_pending_admin_review(status: str | None) -> bool:
    return (status or '').strip() in PENDING_ADMIN_REVIEW_STATUSES


def yappy_status_label(status: str | None) -> str:
    s = (status or '').strip()
    mapping = {
        'pending_receipt': 'Pendiente de comprobante',
        'pending_payment': 'Pendiente de comprobante',
        'pending_admin_review': 'Pendiente de validación',
        'pending_validation': 'Pendiente de validación',
        'manual_review': 'En revisión manual',
        'partially_paid': 'Pago incompleto',
        'paid': 'Pagado',
        'rejected': 'Rechazado',
        'cancelled': 'Cancelado',
    }
    return mapping.get(s, s or '—')
