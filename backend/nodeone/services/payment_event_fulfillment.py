"""Tras pago aprobado: inscripción al evento + participante, sin duplicar pagos/inscripciones."""

from __future__ import annotations

import json
from typing import Any


def build_cart_items_snapshot(cart) -> list[dict]:
    """Copia serializable de ítems del carrito para payment_metadata."""
    rows: list[dict] = []
    for item in getattr(cart, 'items', []) or []:
        rows.append(
            {
                'product_type': item.product_type,
                'product_id': int(item.product_id),
                'product_name': item.product_name,
                'product_description': getattr(item, 'product_description', None),
                'unit_price': int(item.unit_price),
                'quantity': int(item.quantity or 1),
                'item_metadata': getattr(item, 'item_metadata', None),
            }
        )
    return rows


def restore_cart_items_from_payment(payment, cart) -> int:
    """Rehidrata el carrito desde payment_metadata si quedó vacío tras el checkout."""
    if int(getattr(cart, 'get_items_count', lambda: 0)() or 0) > 0:
        return 0
    try:
        meta = json.loads(getattr(payment, 'payment_metadata', None) or '{}')
    except (TypeError, ValueError, json.JSONDecodeError):
        return 0
    items = meta.get('cart_items') or []
    if not items:
        return 0

    from app import CartItem, db

    restored = 0
    for row in items:
        ptype = (row.get('product_type') or '').strip()
        pid = row.get('product_id')
        if not ptype or pid is None:
            continue
        exists = CartItem.query.filter_by(
            cart_id=int(cart.id),
            product_type=ptype,
            product_id=int(pid),
        ).first()
        if exists:
            continue
        db.session.add(
            CartItem(
                cart_id=int(cart.id),
                product_type=ptype,
                product_id=int(pid),
                product_name=(row.get('product_name') or ptype)[:200],
                product_description=row.get('product_description'),
                unit_price=int(row.get('unit_price') or 0),
                quantity=int(row.get('quantity') or 1),
                item_metadata=row.get('item_metadata'),
            )
        )
        restored += 1
    if restored:
        db.session.flush()
    return restored


def cart_event_ids(cart) -> list[int]:
    """IDs de evento presentes en ítems del carrito."""
    ids: list[int] = []
    for item in getattr(cart, 'items', []) or []:
        if getattr(item, 'product_type', None) != 'event':
            continue
        eid = getattr(item, 'product_id', None)
        if eid is None and getattr(item, 'item_metadata', None):
            try:
                meta = json.loads(item.item_metadata)
                eid = meta.get('event_id')
            except (TypeError, ValueError, json.JSONDecodeError):
                eid = None
        if eid is not None:
            try:
                ids.append(int(eid))
            except (TypeError, ValueError):
                pass
    return list(dict.fromkeys(ids))


def _event_ids_from_cart_items_rows(rows: list) -> list[int]:
    ids: list[int] = []
    for row in rows or []:
        if (row.get('product_type') or '').strip() != 'event':
            continue
        eid = row.get('product_id')
        if eid is None and row.get('item_metadata'):
            try:
                raw = row.get('item_metadata')
                meta = json.loads(raw) if isinstance(raw, str) else raw
                eid = (meta or {}).get('event_id')
            except (TypeError, ValueError, json.JSONDecodeError):
                eid = None
        if eid is not None:
            try:
                ids.append(int(eid))
            except (TypeError, ValueError):
                pass
    return ids


def payment_event_ids(payment, cart=None) -> list[int]:
    """Eventos del pedido: carrito vivo + snapshot en payment_metadata."""
    ids: list[int] = []
    if cart is not None:
        ids.extend(cart_event_ids(cart))
    try:
        meta = json.loads(getattr(payment, 'payment_metadata', None) or '{}')
    except (TypeError, ValueError, json.JSONDecodeError):
        meta = {}
    ids.extend(_event_ids_from_cart_items_rows(meta.get('cart_items') or []))
    return list(dict.fromkeys(ids))


def _paid_registration_for_event(user_id: int, event_id: int):
    from app import EventRegistration

    return (
        EventRegistration.query.filter_by(
            user_id=int(user_id),
            event_id=int(event_id),
            registration_status='confirmed',
            payment_status='paid',
        )
        .order_by(EventRegistration.id.desc())
        .first()
    )


def _other_paid_payment_for_event(user_id: int, event_id: int, exclude_payment_id: int):
    """Otro pago ya aprobado (paid) vinculado al mismo evento."""
    from app import Payment

    pay_q = Payment.query.filter_by(user_id=int(user_id), status='paid')
    if exclude_payment_id:
        pay_q = pay_q.filter(Payment.id != int(exclude_payment_id))
    for pay in pay_q.order_by(Payment.id.desc()).all():
        if int(event_id) in payment_event_ids(pay, cart=None):
            return pay
    reg = _paid_registration_for_event(user_id, event_id)
    if not reg:
        return None
    pref = (getattr(reg, 'payment_reference', None) or '').strip()
    for pay in pay_q.order_by(Payment.id.desc()).all():
        if str(pay.id) == pref:
            return pay
        if pref and (getattr(pay, 'payment_reference', None) or '').strip() == pref:
            return pay
    return reg


def _paid_registrations_for_user(user_id: int) -> list:
    from app import EventRegistration

    return (
        EventRegistration.query.filter_by(
            user_id=int(user_id),
            registration_status='confirmed',
            payment_status='paid',
        )
        .order_by(EventRegistration.id.desc())
        .all()
    )


def validate_no_duplicate_event_payment(
    payment,
    cart,
    *,
    exclude_payment_id: int | None = None,
) -> str | None:
    """
    Si el usuario ya tiene inscripción pagada al evento, no aprobar otro pago pendiente.
    Cubre carrito vacío (reintentos de checkout) y snapshot en payment_metadata.
    Devuelve mensaje de error o None si puede aprobarse.
    """
    from app import Event, Payment

    uid = int(getattr(payment, 'user_id', 0) or 0)
    if not uid:
        return 'Pago sin usuario asociado.'
    pid = int(exclude_payment_id or getattr(payment, 'id', 0) or 0)
    event_ids = payment_event_ids(payment, cart)
    paid_regs = _paid_registrations_for_user(uid)
    paid_reg_by_event = {int(r.event_id): r for r in paid_regs if getattr(r, 'event_id', None)}

    def _dup_message(event_id: int, conflict) -> str:
        event = Event.query.get(int(event_id))
        title = (getattr(event, 'title', None) or f'evento #{event_id}').strip()
        if hasattr(conflict, 'id') and hasattr(conflict, 'payment_method'):
            return (
                f'El usuario ya tiene pago aprobado (pedido #{conflict.id}) e inscripción pagada '
                f'a «{title}». Rechace este pedido como duplicado; no vuelva a aprobar.'
            )
        return (
            f'El usuario ya está inscrito y pagado en «{title}». '
            f'Rechace este pedido como duplicado.'
        )

    for event_id in event_ids:
        if int(event_id) not in paid_reg_by_event:
            continue
        conflict = _other_paid_payment_for_event(uid, int(event_id), pid)
        if conflict is not None:
            return _dup_message(int(event_id), conflict)

    other_paid_count = (
        Payment.query.filter_by(user_id=uid, status='paid').filter(Payment.id != pid).count()
    )
    if not event_ids and other_paid_count > 0 and paid_regs:
        titles = []
        for reg in paid_regs:
            eid = int(reg.event_id)
            ev = Event.query.get(eid)
            titles.append((getattr(ev, 'title', None) or f'evento #{eid}').strip())
        joined = ', '.join(f'«{t}»' for t in titles[:3])
        last_paid = (
            Payment.query.filter_by(user_id=uid, status='paid')
            .filter(Payment.id != pid)
            .order_by(Payment.id.desc())
            .first()
        )
        ref = f' (pedido #{last_paid.id})' if last_paid else ''
        return (
            f'El usuario ya tiene pago aprobado{ref} e inscripción pagada en {joined}. '
            f'Este pedido pendiente parece un reintento duplicado (carrito vacío). Rechácelo.'
        )

    return None


def ensure_participants_for_event_ids(event_ids: list[int]) -> dict[str, Any]:
    """Crea participantes desde registros confirmados (sin duplicar por email/user_id)."""
    from nodeone.modules.events.services.participants_from_registrations import (
        import_participants_from_registrations,
    )

    totals = {'created': 0, 'skipped': 0, 'cancelled_skipped': 0, 'events': []}
    for eid in event_ids:
        stats = import_participants_from_registrations(int(eid), only_confirmed=True)
        totals['created'] += stats.get('created', 0)
        totals['skipped'] += stats.get('skipped', 0)
        totals['cancelled_skipped'] += stats.get('cancelled_skipped', 0)
        totals['events'].append({'event_id': int(eid), **stats})
    return totals


def event_ids_for_paid_payment(payment) -> list[int]:
    """Eventos ligados a un pago ya aprobado (carrito pendiente o registro con su referencia)."""
    from app import EventRegistration, get_or_create_cart

    cart = get_or_create_cart(int(payment.user_id))
    ids = cart_event_ids(cart)
    pref = (getattr(payment, 'payment_reference', None) or '').strip()
    pid_s = str(int(payment.id))
    refs = {pid_s}
    if pref:
        refs.add(pref)
    q = EventRegistration.query.filter_by(
        user_id=int(payment.user_id),
        registration_status='confirmed',
        payment_status='paid',
    )
    for reg in q.all():
        rpref = (getattr(reg, 'payment_reference', None) or '').strip()
        if rpref in refs:
            ids.append(int(reg.event_id))
    return list(dict.fromkeys(ids))


def fulfill_paid_payment_events(payment, cart=None) -> dict[str, Any]:
    """
    Idempotente: procesa carrito si aplica, asegura participantes en eventos del pago.
    Usar tras aprobar o para reparar pagos paid sin participante.
    """
    from app import db, get_or_create_cart
    from nodeone.services.manual_payment_flow import is_manual_validation_method
    from nodeone.services.payment_post_process import process_cart_after_payment

    result: dict[str, Any] = {
        'payment_id': int(payment.id),
        'cart_processed': False,
        'participant_stats': None,
    }
    st = (getattr(payment, 'status', None) or '').strip()
    method = (getattr(payment, 'payment_method', None) or '').strip()
    if is_manual_validation_method(method) and st != 'paid':
        result['error'] = 'Solo pagos manuales en estado paid.'
        return result
    if not is_manual_validation_method(method) and st != 'succeeded':
        result['error'] = 'Solo pagos confirmados (succeeded/paid).'
        return result

    cart = cart or get_or_create_cart(int(payment.user_id))
    restored = restore_cart_items_from_payment(payment, cart)
    if restored:
        result['cart_restored'] = restored

    if cart.get_items_count() > 0:
        process_cart_after_payment(cart, payment)
        cart.clear()
        db.session.commit()
        result['cart_processed'] = True
    else:
        db.session.commit()

    event_ids = event_ids_for_paid_payment(payment)
    if event_ids:
        result['participant_stats'] = ensure_participants_for_event_ids(event_ids)
        db.session.commit()
    return result
