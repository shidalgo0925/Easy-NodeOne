"""Hito 3 — Order Domain service (Spec v1.0). Sin inventario."""

from __future__ import annotations

import json
import secrets
import uuid
from datetime import datetime
from typing import Any

from models.commercial_core import CorePosTerminal
from models.eposone_order import (
    EposoneOrder,
    EposoneOrderCancellation,
    EposoneOrderEvent,
    EposoneOrderItem,
    EposoneOrderPayment,
    EposoneOrderReturn,
)

ALLOWED_EVENT_TYPES = frozenset(
    {
        'pedido.creado',
        'pedido.actualizado',
        'pedido.dividido',
        'producto.agregado',
        'producto.eliminado',
        'cantidad.modificada',
        'pedido.enviado',
        'linea.lista',
        'pedido.listo',
        'linea.entregada',
        'pedido.entregado',
        'pago.registrado',
        'pedido.cobrado',
        'linea.cancelada',
        'pedido.anulado',
        'pedido.devuelto',
    }
)

EDITABLE_STATUSES = frozenset({'open', 'draft', 'sent', 'ready'})
OPEN_FOR_TABLE = frozenset({'open', 'draft', 'sent', 'ready'})


class OrderDomainError(Exception):
    def __init__(self, code: str, *, http_status: int = 400):
        super().__init__(code)
        self.code = code
        self.http_status = http_status


def _iso(dt: datetime | None) -> str | None:
    return dt.isoformat() + 'Z' if dt else None


def _recalc(order: EposoneOrder) -> None:
    sub = 0.0
    tax = 0.0
    disc = 0.0
    for it in order.items or []:
        if str(it.line_status) == 'cancelled':
            continue
        line = float(it.qty or 0) * float(it.unit_price or 0)
        sub += line
        tax += float(it.tax or 0)
        disc += float(it.discount or 0)
    order.subtotal = round(sub, 4)
    order.tax = round(tax, 4)
    order.discount = round(disc, 4)
    tip = float(order.tip or 0)
    order.total = round(sub + tax - disc + tip, 4)
    paid = float(order.amount_paid or 0)
    if paid <= 0:
        order.payment_status = 'unpaid'
        order.financially_closed = False
    elif paid + 1e-9 < float(order.total or 0):
        order.payment_status = 'partial'
        order.financially_closed = False
    else:
        order.payment_status = 'paid'
        order.financially_closed = True


def order_to_dict(order: EposoneOrder, *, include_events: bool = False) -> dict[str, Any]:
    payload: dict[str, Any] = {
        'id': order.id,
        'local_number': order.local_number,
        'en1_number': order.en1_number,
        'organization_id': order.organization_id,
        'branch_ref': order.branch_ref,
        'pos_ref': order.pos_ref,
        'register_ref': order.register_ref,
        'owner_device_uuid': order.owner_device_uuid,
        'owner_pos_ref': order.owner_pos_ref,
        'user_ref': order.user_ref,
        'customer_ref': order.customer_ref,
        'table_ref': order.table_ref,
        'status': order.status,
        'payment_status': order.payment_status,
        'financially_closed': bool(order.financially_closed),
        'subtotal': float(order.subtotal or 0),
        'tax': float(order.tax or 0),
        'discount': float(order.discount or 0),
        'tip': float(order.tip or 0),
        'total': float(order.total or 0),
        'amount_paid': float(order.amount_paid or 0),
        'notes': order.notes,
        'parent_order_id': order.parent_order_id,
        'opened_at': _iso(order.opened_at),
        'updated_at': _iso(order.updated_at),
        'items': [
            {
                'id': it.id,
                'line_ref': it.line_ref,
                'product_ref': it.product_ref,
                'qty': float(it.qty or 0),
                'unit_price': float(it.unit_price or 0),
                'tax': float(it.tax or 0),
                'discount': float(it.discount or 0),
                'notes': it.notes,
                'line_status': it.line_status,
            }
            for it in (order.items or [])
        ],
        'payments': [
            {
                'id': p.id,
                'payment_ref': p.payment_ref,
                'amount': float(p.amount or 0),
                'method': p.method,
                'kind': p.kind,
                'currency': p.currency,
                'created_at': _iso(p.created_at),
                'payment_method_id': p.payment_method_id,
                'reference': getattr(p, 'reference', None),
                'authorization_code': getattr(p, 'authorization_code', None),
                'received_by': getattr(p, 'received_by', None),
                'paid_at': _iso(getattr(p, 'paid_at', None)),
                'status': getattr(p, 'status', None) or 'captured',
            }
            for p in (order.payments or [])
        ],
    }
    if include_events:
        payload['events'] = [
            {
                'event_id': ev.event_id,
                'type': ev.type,
                'sequence': ev.sequence,
                'occurred_at': _iso(ev.occurred_at),
                'actor_user_ref': ev.actor_user_ref,
                'actor_device_uuid': ev.actor_device_uuid,
                'payload': json.loads(ev.payload_json) if ev.payload_json else None,
            }
            for ev in (order.events or [])
        ]
    return payload


class OrderDomainService:
    @staticmethod
    def _require_owner(order: EposoneOrder, device: CorePosTerminal, *, for_payment: bool = False) -> None:
        if for_payment:
            # Etapa cobro: cualquier dispositivo activo de la misma org.
            if int(device.organization_id) != int(order.organization_id):
                raise OrderDomainError('forbidden', http_status=403)
            return
        if str(order.owner_device_uuid) != str(device.terminal_ref):
            raise OrderDomainError('not_owner', http_status=403)

    @staticmethod
    def _next_sequence(order_id: int) -> int:
        last = (
            EposoneOrderEvent.query.filter_by(order_id=order_id)
            .order_by(EposoneOrderEvent.sequence.desc())
            .first()
        )
        return int(last.sequence) + 1 if last else 1

    @staticmethod
    def _append_event(
        order: EposoneOrder,
        *,
        event_id: str,
        event_type: str,
        device: CorePosTerminal,
        user_ref: str | None,
        payload: dict[str, Any] | None,
    ) -> EposoneOrderEvent:
        from app import db

        if event_type not in ALLOWED_EVENT_TYPES:
            raise OrderDomainError('event_type_invalid', http_status=400)
        existing = EposoneOrderEvent.query.filter_by(
            organization_id=int(order.organization_id), event_id=event_id
        ).first()
        if existing is not None:
            return existing  # idempotente
        ev = EposoneOrderEvent(
            order_id=int(order.id),
            organization_id=int(order.organization_id),
            event_id=event_id,
            type=event_type,
            sequence=OrderDomainService._next_sequence(int(order.id)),
            occurred_at=datetime.utcnow(),
            actor_user_ref=user_ref,
            actor_device_uuid=str(device.terminal_ref),
            payload_json=json.dumps(payload or {}, ensure_ascii=False),
        )
        db.session.add(ev)
        return ev

    @staticmethod
    def list_orders(
        device: CorePosTerminal,
        *,
        status: str | None = None,
        table_ref: str | None = None,
        limit: int = 50,
    ) -> list[EposoneOrder]:
        q = EposoneOrder.query.filter_by(organization_id=int(device.organization_id))
        if status:
            q = q.filter_by(status=status.strip().lower())
        if table_ref:
            q = q.filter_by(table_ref=table_ref.strip())
        return q.order_by(EposoneOrder.id.desc()).limit(min(limit, 200)).all()

    @staticmethod
    def get_order(device: CorePosTerminal, order_id: int) -> EposoneOrder:
        order = EposoneOrder.query.filter_by(
            id=int(order_id), organization_id=int(device.organization_id)
        ).first()
        if order is None:
            raise OrderDomainError('order_not_found', http_status=404)
        return order

    @staticmethod
    def create_order(device: CorePosTerminal, body: dict[str, Any]) -> EposoneOrder:
        from app import db

        oid = int(device.organization_id)
        table_ref = (body.get('table_ref') or '').strip() or None
        # Modo mesa: reutilizar pedido abierto.
        if table_ref:
            existing = (
                EposoneOrder.query.filter_by(organization_id=oid, table_ref=table_ref)
                .filter(EposoneOrder.status.in_(tuple(OPEN_FOR_TABLE)))
                .order_by(EposoneOrder.id.desc())
                .first()
            )
            if existing is not None:
                return existing

        order = EposoneOrder(
            organization_id=oid,
            local_number=(body.get('local_number') or '').strip() or None,
            en1_number='pending',
            branch_ref=(body.get('branch_ref') or device.branch_ref or None),
            pos_ref=(body.get('pos_ref') or device.pos_ref or None),
            register_ref=(body.get('register_ref') or device.register_ref or None),
            owner_device_uuid=str(device.terminal_ref),
            owner_pos_ref=device.pos_ref,
            user_ref=(body.get('user_ref') or '').strip() or None,
            customer_ref=(body.get('customer_ref') or '').strip() or None,
            table_ref=table_ref,
            status='open',
            notes=(body.get('notes') or None),
            tip=float(body.get('tip') or 0),
        )
        db.session.add(order)
        db.session.flush()
        order.en1_number = f'EN1-{oid}-{order.id}'
        event_id = str(body.get('event_id') or uuid.uuid4())
        OrderDomainService._append_event(
            order,
            event_id=event_id,
            event_type='pedido.creado',
            device=device,
            user_ref=order.user_ref,
            payload={'local_number': order.local_number, 'table_ref': table_ref},
        )
        db.session.commit()
        return order

    @staticmethod
    def patch_order(device: CorePosTerminal, order_id: int, body: dict[str, Any]) -> EposoneOrder:
        from app import db

        order = OrderDomainService.get_order(device, order_id)
        OrderDomainService._require_owner(order, device)
        if str(order.status) not in EDITABLE_STATUSES:
            raise OrderDomainError('order_not_editable', http_status=409)
        if 'user_ref' in body:
            order.user_ref = (body.get('user_ref') or '').strip() or None
        if 'customer_ref' in body:
            order.customer_ref = (body.get('customer_ref') or '').strip() or None
        if 'notes' in body:
            order.notes = body.get('notes')
        if 'tip' in body:
            order.tip = float(body.get('tip') or 0)
        if 'local_number' in body:
            order.local_number = (body.get('local_number') or '').strip() or None
        _recalc(order)
        order.updated_at = datetime.utcnow()
        event_id = str(body.get('event_id') or uuid.uuid4())
        OrderDomainService._append_event(
            order,
            event_id=event_id,
            event_type='pedido.actualizado',
            device=device,
            user_ref=order.user_ref,
            payload={k: body.get(k) for k in ('user_ref', 'customer_ref', 'notes', 'tip', 'local_number') if k in body},
        )
        db.session.commit()
        return order

    @staticmethod
    def apply_event(device: CorePosTerminal, order_id: int, body: dict[str, Any]) -> EposoneOrder:
        from app import db

        order = OrderDomainService.get_order(device, order_id)
        event_type = str(body.get('type') or '').strip()
        event_id = str(body.get('event_id') or '').strip()
        if not event_id:
            raise OrderDomainError('event_id_required', http_status=400)
        if event_type not in ALLOWED_EVENT_TYPES:
            raise OrderDomainError('event_type_invalid', http_status=400)

        # Idempotencia temprana
        preexisting = EposoneOrderEvent.query.filter_by(
            organization_id=int(order.organization_id), event_id=event_id
        ).first()
        if preexisting is not None:
            return order

        payload = body.get('payload') if isinstance(body.get('payload'), dict) else {}
        user_ref = (body.get('actor_user_ref') or body.get('user_ref') or order.user_ref)

        needs_owner = event_type not in ('pago.registrado', 'pedido.cobrado')
        if needs_owner:
            OrderDomainService._require_owner(order, device)
        else:
            OrderDomainService._require_owner(order, device, for_payment=True)

        if event_type == 'producto.agregado':
            line_ref = str(payload.get('line_ref') or secrets.token_hex(6))
            product_ref = str(payload.get('product_ref') or '').strip()
            if not product_ref:
                raise OrderDomainError('product_ref_required', http_status=400)
            item = EposoneOrderItem(
                order_id=order.id,
                line_ref=line_ref,
                product_ref=product_ref,
                qty=float(payload.get('qty') or 1),
                unit_price=float(payload.get('unit_price') or 0),
                tax=float(payload.get('tax') or 0),
                discount=float(payload.get('discount') or 0),
                notes=payload.get('notes'),
                line_status='pending',
            )
            order.items.append(item)
            db.session.flush()
            _recalc(order)
        elif event_type == 'producto.eliminado':
            line_ref = str(payload.get('line_ref') or '').strip()
            item = next((i for i in order.items if i.line_ref == line_ref), None)
            if item is None:
                raise OrderDomainError('line_not_found', http_status=404)
            db.session.delete(item)
            db.session.flush()
            _recalc(order)
        elif event_type == 'cantidad.modificada':
            line_ref = str(payload.get('line_ref') or '').strip()
            item = next((i for i in order.items if i.line_ref == line_ref), None)
            if item is None:
                raise OrderDomainError('line_not_found', http_status=404)
            item.qty = float(payload.get('qty') or item.qty)
            _recalc(order)
        elif event_type == 'pedido.enviado':
            order.status = 'sent'
        elif event_type == 'linea.lista':
            line_ref = str(payload.get('line_ref') or '').strip()
            item = next((i for i in order.items if i.line_ref == line_ref), None)
            if item is None:
                raise OrderDomainError('line_not_found', http_status=404)
            item.line_status = 'ready'
        elif event_type == 'pedido.listo':
            order.status = 'ready'
            for it in order.items:
                if it.line_status != 'cancelled':
                    it.line_status = 'ready'
        elif event_type == 'linea.entregada':
            line_ref = str(payload.get('line_ref') or '').strip()
            item = next((i for i in order.items if i.line_ref == line_ref), None)
            if item is None:
                raise OrderDomainError('line_not_found', http_status=404)
            item.line_status = 'delivered'
        elif event_type == 'pedido.entregado':
            order.status = 'delivered'
            for it in order.items:
                if it.line_status != 'cancelled':
                    it.line_status = 'delivered'
        elif event_type == 'linea.cancelada':
            line_ref = str(payload.get('line_ref') or '').strip()
            item = next((i for i in order.items if i.line_ref == line_ref), None)
            if item is None:
                raise OrderDomainError('line_not_found', http_status=404)
            item.line_status = 'cancelled'
            _recalc(order)
        elif event_type == 'pedido.anulado':
            reason = str(payload.get('reason') or body.get('reason') or '').strip()
            if not reason:
                raise OrderDomainError('reason_required', http_status=400)
            if str(order.status) in ('open', 'draft'):
                raise OrderDomainError('use_modify_not_cancel', http_status=409)
            order.status = 'cancelled'
            db.session.add(
                EposoneOrderCancellation(order_id=order.id, reason=reason, user_ref=user_ref)
            )
        elif event_type == 'pedido.devuelto':
            reason = str(payload.get('reason') or body.get('reason') or '').strip()
            if not reason:
                raise OrderDomainError('reason_required', http_status=400)
            order.status = 'returned'
            db.session.add(EposoneOrderReturn(order_id=order.id, reason=reason, user_ref=user_ref))
        elif event_type == 'pedido.actualizado':
            if 'user_ref' in payload:
                order.user_ref = (payload.get('user_ref') or '').strip() or None
            if 'notes' in payload:
                order.notes = payload.get('notes')
            if 'tip' in payload:
                order.tip = float(payload.get('tip') or 0)
                _recalc(order)
        elif event_type == 'pedido.cobrado':
            if float(order.amount_paid or 0) + 1e-9 < float(order.total or 0):
                raise OrderDomainError('balance_not_zero', http_status=409)
            order.financially_closed = True
            order.payment_status = 'paid'
        elif event_type in ('pago.registrado', 'pedido.creado', 'pedido.dividido'):
            # pago via /payments; creado/dividido en otros endpoints
            pass

        order.updated_at = datetime.utcnow()
        OrderDomainService._append_event(
            order,
            event_id=event_id,
            event_type=event_type,
            device=device,
            user_ref=user_ref,
            payload=payload,
        )
        db.session.commit()
        return order

    @staticmethod
    def add_payment(device: CorePosTerminal, order_id: int, body: dict[str, Any]) -> EposoneOrder:
        from nodeone.modules.eposone.order_payment_service import OrderPaymentService

        return OrderPaymentService.add_payment(device, order_id, body)

    @staticmethod
    def split_order(device: CorePosTerminal, order_id: int, body: dict[str, Any]) -> dict[str, Any]:
        from app import db

        order = OrderDomainService.get_order(device, order_id)
        OrderDomainService._require_owner(order, device)
        line_refs = body.get('line_refs') or []
        if not isinstance(line_refs, list) or not line_refs:
            raise OrderDomainError('line_refs_required', http_status=400)
        refs = {str(r) for r in line_refs}
        moving = [i for i in order.items if i.line_ref in refs and i.line_status != 'cancelled']
        if not moving:
            raise OrderDomainError('lines_not_found', http_status=404)

        child = EposoneOrder(
            organization_id=order.organization_id,
            local_number=(body.get('local_number') or None),
            en1_number='pending',
            branch_ref=order.branch_ref,
            pos_ref=order.pos_ref,
            register_ref=order.register_ref,
            # Spec: hijo hereda ownership del origen
            owner_device_uuid=order.owner_device_uuid,
            owner_pos_ref=order.owner_pos_ref,
            user_ref=order.user_ref,
            customer_ref=order.customer_ref,
            table_ref=None,  # split no comparte mesa abierta
            status='open',
            tip=0,
            parent_order_id=order.id,
            notes=body.get('notes'),
        )
        db.session.add(child)
        db.session.flush()
        child.en1_number = f'EN1-{child.organization_id}-{child.id}'
        for it in moving:
            it.order_id = child.id
        db.session.flush()
        db.session.expire(order, ['items'])
        db.session.expire(child, ['items'])
        db.session.refresh(order)
        db.session.refresh(child)
        _recalc(order)
        _recalc(child)
        event_id = str(body.get('event_id') or uuid.uuid4())
        OrderDomainService._append_event(
            order,
            event_id=event_id,
            event_type='pedido.dividido',
            device=device,
            user_ref=order.user_ref,
            payload={'child_order_id': child.id, 'child_en1_number': child.en1_number, 'line_refs': list(refs)},
        )
        OrderDomainService._append_event(
            child,
            event_id=str(uuid.uuid4()),
            event_type='pedido.creado',
            device=device,
            user_ref=child.user_ref,
            payload={'split_from': order.id, 'en1_number': order.en1_number},
        )
        order.updated_at = datetime.utcnow()
        child.updated_at = datetime.utcnow()
        db.session.commit()
        return {'parent': order_to_dict(order), 'child': order_to_dict(child)}
