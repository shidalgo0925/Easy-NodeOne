"""OrderService — pedidos comerciales (Etapa 14)."""

from __future__ import annotations

from typing import Any

from models.commercial_core import CoreCommercialOrder, CoreCommercialOrderLine
from nodeone.core.commerce.constants import (
    ORDER_FISCAL_STATUS_NOT_REQUIRED,
    ORDER_LINE_STATUS_CANCELLED,
    ORDER_LINE_STATUS_PENDING,
    ORDER_PAYMENT_STATUS_PAID,
    ORDER_PAYMENT_STATUS_UNPAID,
    ORDER_STATUS_CANCELLED,
    ORDER_STATUS_CONFIRMED,
    ORDER_STATUS_DRAFT,
    ORDER_STATUS_REFUNDED,
    can_transition_order_status,
)
from nodeone.core.master.constants import PRODUCT_STATUS_ACTIVE
from nodeone.core.commerce.dtos import OrderDTO
from nodeone.core.commerce.events import (
    COMMERCE_ORDER_CANCELLED,
    COMMERCE_ORDER_CONFIRMED,
    COMMERCE_ORDER_CREATED,
    COMMERCE_ORDER_FISCAL_STATUS_CHANGED,
    COMMERCE_ORDER_PAYMENT_STATUS_CHANGED,
    COMMERCE_ORDER_STATUS_CHANGED,
    COMMERCE_ORDER_TRANSFERRED,
)
from nodeone.core.commerce.persistence import order_to_dto
from nodeone.core.services.audit import AuditService

class CommerceNotReadyError(NotImplementedError):
    """Reservado — tablas comerciales no disponibles."""


class OrderValidationError(ValueError):
    pass


def _resolve_branch_org_unit_id(organization_id: int, data: dict[str, Any]) -> int | None:
    from nodeone.core.master.constants import ORG_UNIT_TYPE_BRANCH
    from nodeone.core.services.org_unit import OrgUnitService

    if data.get('branch_org_unit_id') is not None:
        branch_id = int(data['branch_org_unit_id'])
        items = OrgUnitService.list_units(int(organization_id), unit_type=ORG_UNIT_TYPE_BRANCH)
        if not any(u.id == branch_id for u in items):
            raise OrderValidationError('invalid_branch_org_unit_id')
        return branch_id

    branch_ref = (str(data.get('branch_ref') or '')).strip()
    if branch_ref:
        unit = OrgUnitService.get_by_ref(int(organization_id), branch_ref)
        if unit is None or unit.unit_type != ORG_UNIT_TYPE_BRANCH:
            raise OrderValidationError('invalid_branch_ref')
        return int(unit.id)
    return None


def _recalculate_order_totals(row: CoreCommercialOrder) -> None:
    subtotal = round(sum(float(line.line_total or 0) for line in (row.lines or [])), 2)
    row.subtotal = subtotal
    row.grand_total = round(subtotal + float(row.tax_total or 0), 2)


def _validate_parent_order(organization_id: int, parent_order_id: int) -> CoreCommercialOrder:
    parent = CoreCommercialOrder.query.filter_by(
        organization_id=int(organization_id),
        id=int(parent_order_id),
    ).first()
    if parent is None:
        raise OrderValidationError('parent_order_not_found')
    return parent


def _resolve_order_contact_id(organization_id: int, data: dict[str, Any]) -> int | None:
    from nodeone.core.services.contacts import ContactService

    oid = int(organization_id)
    contact_ref = (str(data.get('contact_ref') or '')).strip() or None
    if contact_ref:
        try:
            contact = ContactService.resolve_ref(oid, contact_ref)
        except ContactService.ValidationError as exc:
            reason = str(exc)
            if reason == 'contact_inactive':
                raise OrderValidationError(f'inactive_contact_ref:{contact_ref}') from exc
            raise OrderValidationError(f'invalid_contact_ref:{contact_ref}') from exc
        return int(contact.id)

    if data.get('contact_id') is not None:
        contact = ContactService.get(oid, int(data['contact_id']))
        if contact is None or not contact.active:
            raise OrderValidationError('invalid_contact_id')
        return int(contact.id)
    return None


def _resolve_pos_terminal_id(organization_id: int, data: dict[str, Any]) -> int | None:
    from nodeone.core.commerce.pos import PosTerminalService

    return PosTerminalService.resolve_id(int(organization_id), data)


def _build_order_line(organization_id: int, raw: dict[str, Any]) -> CoreCommercialOrderLine:
    from nodeone.core.services.product import ProductService

    product_ref = (str(raw.get('product_ref') or '')).strip() or None
    description = (str(raw.get('description') or '')).strip()
    qty = float(raw.get('quantity') or 1)
    unit_specified = raw.get('unit_price') is not None
    unit = float(raw.get('unit_price') or 0)

    if product_ref:
        product = ProductService.get_by_ref(int(organization_id), product_ref)
        if product is None or product.status != PRODUCT_STATUS_ACTIVE:
            raise OrderValidationError(f'invalid_product_ref:{product_ref}')
        if not description:
            description = product.name
        if not unit_specified:
            unit = float(product.unit_price or 0)
        product_ref = product.product_ref

    if not description:
        description = 'Ítem'

    line_total = round(qty * unit, 2)
    return CoreCommercialOrderLine(
        description=description[:500],
        quantity=qty,
        unit_price=unit,
        line_total=line_total,
        product_ref=product_ref[:128] if product_ref else None,
        line_status=ORDER_LINE_STATUS_PENDING,
    )


class OrderService:
    """API Core de pedidos — persistencia en core_commercial_order."""

    @staticmethod
    def can_transition(current_status: str, target_status: str) -> bool:
        return can_transition_order_status(current_status, target_status)

    @staticmethod
    def get(organization_id: int, order_id: int) -> OrderDTO | None:
        row = CoreCommercialOrder.query.filter_by(
            organization_id=int(organization_id),
            id=int(order_id),
        ).first()
        return order_to_dto(row) if row is not None else None

    @staticmethod
    def get_by_ref(organization_id: int, order_ref: str) -> OrderDTO | None:
        row = CoreCommercialOrder.query.filter_by(
            organization_id=int(organization_id),
            order_ref=(order_ref or '').strip(),
        ).first()
        return order_to_dto(row) if row is not None else None

    @staticmethod
    def search(
        organization_id: int,
        *,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[OrderDTO], int]:
        q = CoreCommercialOrder.query.filter_by(organization_id=int(organization_id))
        if status:
            q = q.filter_by(operational_status=(status or '').strip().lower())
        total = q.count()
        rows = (
            q.order_by(CoreCommercialOrder.id.desc())
            .offset(max(0, int(offset)))
            .limit(max(1, min(int(limit), 200)))
            .all()
        )
        return [order_to_dto(r) for r in rows], int(total)

    @staticmethod
    def create(organization_id: int, data: dict[str, Any], *, source_app_id: str = 'eposone') -> OrderDTO:
        from app import db

        oid = int(organization_id)
        lines_in = data.get('lines') if isinstance(data.get('lines'), list) else []
        if not lines_in:
            raise OrderValidationError('lines_required')

        order_ref = (data.get('order_ref') or '').strip() or OrderService._next_order_ref(oid)

        subtotal = 0.0
        tax_total = float(data.get('tax_total') or 0)
        line_rows: list[CoreCommercialOrderLine] = []
        for raw in lines_in:
            if not isinstance(raw, dict):
                continue
            line = _build_order_line(oid, raw)
            subtotal += float(line.line_total or 0)
            line_rows.append(line)
        if not line_rows:
            raise OrderValidationError('lines_required')

        grand_total = round(subtotal + tax_total, 2)
        branch_org_unit_id = _resolve_branch_org_unit_id(oid, data)
        parent_order_id = None
        if data.get('parent_order_id') is not None:
            parent = _validate_parent_order(oid, int(data['parent_order_id']))
            parent_order_id = int(parent.id)
            if branch_org_unit_id is None and parent.branch_org_unit_id:
                branch_org_unit_id = int(parent.branch_org_unit_id)
        op_status = (
            str(data.get('operational_status') or data.get('status') or ORDER_STATUS_DRAFT).strip().lower()
            or ORDER_STATUS_DRAFT
        )
        contact_id = _resolve_order_contact_id(oid, data)
        pos_terminal_id = _resolve_pos_terminal_id(oid, data)
        row = CoreCommercialOrder(
            organization_id=oid,
            order_ref=order_ref,
            operational_status=op_status,
            payment_status=ORDER_PAYMENT_STATUS_UNPAID,
            fiscal_status=ORDER_FISCAL_STATUS_NOT_REQUIRED,
            contact_id=contact_id,
            branch_org_unit_id=branch_org_unit_id,
            parent_order_id=parent_order_id,
            pos_terminal_id=pos_terminal_id,
            currency=str(data.get('currency') or 'USD')[:8],
            subtotal=subtotal,
            tax_total=tax_total,
            grand_total=grand_total,
            source_app_id=(source_app_id or 'eposone').strip().lower() or 'eposone',
            notes=(str(data.get('notes')).strip()[:5000] if data.get('notes') else None),
        )
        row.lines = line_rows
        db.session.add(row)
        db.session.commit()

        dto = order_to_dto(row)
        OrderService.publish_created(
            oid,
            order_ref=dto.order_ref,
            status=dto.status,
            payment_status=dto.payment_status,
            grand_total=dto.grand_total,
            source_app_id=source_app_id,
            extra={'order_id': dto.id},
        )
        return dto

    @staticmethod
    def _next_order_ref(organization_id: int) -> str:
        import re

        prefix = 'POS'
        rx = re.compile(rf'^{re.escape(prefix)}-(\d{{1,12}})\Z')
        max_seq = 0
        for (ref,) in (
            CoreCommercialOrder.query.filter_by(organization_id=int(organization_id))
            .with_entities(CoreCommercialOrder.order_ref)
            .all()
        ):
            m = rx.match(str(ref or '').strip())
            if m:
                max_seq = max(max_seq, int(m.group(1)))
        return f'{prefix}-{max_seq + 1:04d}'

    @staticmethod
    def split_order(
        organization_id: int,
        parent_order_id: int,
        line_indexes: list[int],
        *,
        source_app_id: str = 'eposone',
    ) -> OrderDTO:
        """Split bill v1 — mueve líneas seleccionadas a un sub-pedido (§6.4)."""
        from app import db

        oid = int(organization_id)
        parent = _validate_parent_order(oid, int(parent_order_id))
        if str(parent.payment_status or ORDER_PAYMENT_STATUS_UNPAID) != ORDER_PAYMENT_STATUS_UNPAID:
            raise OrderValidationError('parent_order_already_paid')

        parent_lines = list(parent.lines or [])
        if not parent_lines:
            raise OrderValidationError('parent_order_has_no_lines')

        indexes = sorted({int(i) for i in line_indexes})
        if not indexes:
            raise OrderValidationError('line_indexes_required')
        if any(i < 0 or i >= len(parent_lines) for i in indexes):
            raise OrderValidationError('invalid_line_indexes')

        moved_lines: list[CoreCommercialOrderLine] = []
        for idx in reversed(indexes):
            moved_lines.insert(0, parent_lines.pop(idx))

        child = CoreCommercialOrder(
            organization_id=oid,
            order_ref=OrderService._next_order_ref(oid),
            operational_status=ORDER_STATUS_DRAFT,
            payment_status=ORDER_PAYMENT_STATUS_UNPAID,
            fiscal_status=ORDER_FISCAL_STATUS_NOT_REQUIRED,
            contact_id=int(parent.contact_id) if parent.contact_id else None,
            branch_org_unit_id=int(parent.branch_org_unit_id) if parent.branch_org_unit_id else None,
            parent_order_id=int(parent.id),
            currency=str(parent.currency or 'USD')[:8],
            tax_total=0.0,
            source_app_id=(source_app_id or 'eposone').strip().lower() or 'eposone',
        )
        child.lines = [_build_order_line(oid, {
            'description': line.description,
            'quantity': line.quantity,
            'unit_price': line.unit_price,
            'product_ref': line.product_ref,
        }) for line in moved_lines]
        for line in moved_lines:
            db.session.delete(line)

        _recalculate_order_totals(child)
        _recalculate_order_totals(parent)
        if not parent.lines:
            parent.operational_status = ORDER_STATUS_CANCELLED

        db.session.add(child)
        parent.version = int(parent.version or 1) + 1
        db.session.commit()

        dto = order_to_dto(child)
        OrderService.publish_created(
            oid,
            order_ref=dto.order_ref,
            status=dto.status,
            payment_status=dto.payment_status,
            grand_total=dto.grand_total,
            source_app_id=source_app_id,
            extra={'order_id': dto.id, 'parent_order_id': int(parent.id)},
        )
        return dto

    @staticmethod
    def transfer_to_terminal(
        organization_id: int,
        order_id: int,
        data: dict[str, Any],
        *,
        source_app_id: str = 'eposone',
    ) -> OrderDTO:
        """Transferencia a caja v1 — mismo pedido, cambia terminal de cobro (§6.4)."""
        from app import db
        from nodeone.core.commerce.constants import POS_TERMINAL_ACTIVE
        from nodeone.core.commerce.pos import PosTerminalService

        oid = int(organization_id)
        target_terminal_id = PosTerminalService.resolve_id(oid, data)
        if target_terminal_id is None:
            raise OrderValidationError('terminal_ref_or_id_required')

        row = CoreCommercialOrder.query.filter_by(organization_id=oid, id=int(order_id)).first()
        if row is None:
            raise OrderValidationError('order_not_found')

        if str(row.payment_status or ORDER_PAYMENT_STATUS_UNPAID) != ORDER_PAYMENT_STATUS_UNPAID:
            raise OrderValidationError('order_already_paid')

        cur_status = str(row.operational_status or ORDER_STATUS_DRAFT)
        if cur_status in {ORDER_STATUS_CANCELLED, ORDER_STATUS_REFUNDED}:
            raise OrderValidationError(f'order_not_transferable:{cur_status}')

        terminal = PosTerminalService.get(oid, int(target_terminal_id))
        if terminal is None:
            raise OrderValidationError('invalid_terminal_id')
        if str(terminal.status or '') != POS_TERMINAL_ACTIVE:
            raise OrderValidationError('inactive_terminal')

        from_terminal_id = int(row.pos_terminal_id) if row.pos_terminal_id else None
        if from_terminal_id == int(target_terminal_id):
            return order_to_dto(row)

        row.pos_terminal_id = int(target_terminal_id)
        row.version = int(row.version or 1) + 1
        db.session.commit()

        dto = order_to_dto(row)
        OrderService.publish_transferred(
            oid,
            order_ref=str(row.order_ref),
            from_terminal_id=from_terminal_id,
            to_terminal_id=int(target_terminal_id),
            to_terminal_ref=str(terminal.terminal_ref),
            source_app_id=source_app_id,
            order_id=int(row.id),
        )
        return dto

    @staticmethod
    def transition_status(
        organization_id: int,
        order_id: int,
        target_status: str,
        *,
        source_app_id: str = 'eposone',
        reason: str | None = None,
    ) -> OrderDTO:
        from app import db

        row = CoreCommercialOrder.query.filter_by(
            organization_id=int(organization_id),
            id=int(order_id),
        ).first()
        if row is None:
            raise OrderValidationError('order_not_found')
        tgt = (target_status or '').strip().lower()
        cur = str(row.status or '')
        if not OrderService.can_transition(cur, tgt):
            raise OrderValidationError(f'invalid_transition:{cur}->{tgt}')

        if tgt == ORDER_STATUS_CANCELLED:
            for line in row.lines or []:
                if str(line.line_status or '') != ORDER_LINE_STATUS_CANCELLED:
                    line.line_status = ORDER_LINE_STATUS_CANCELLED

        row.status = tgt
        row.version = int(row.version or 1) + 1
        db.session.commit()

        OrderService.publish_status_changed(
            int(organization_id),
            order_ref=str(row.order_ref),
            from_status=cur,
            to_status=tgt,
            source_app_id=source_app_id,
            order_id=int(row.id),
        )
        if tgt == ORDER_STATUS_CONFIRMED:
            OrderService.publish_confirmed(
                int(organization_id), order_ref=str(row.order_ref), source_app_id=source_app_id
            )
        if tgt == ORDER_STATUS_CANCELLED:
            OrderService.publish_cancelled(
                int(organization_id),
                order_ref=str(row.order_ref),
                reason=reason,
                source_app_id=source_app_id,
            )

        from nodeone.modules.eposone.kds_service import KdsService

        try:
            KdsService.maybe_enqueue_for_order_status(int(organization_id), int(order_id), tgt)
        except Exception:
            pass

        try:
            from nodeone.modules.eposone.delivery_service import EposoneDeliveryService

            EposoneDeliveryService.maybe_create_for_order_status(int(organization_id), int(order_id), tgt)
        except Exception:
            pass

        return order_to_dto(row)

    @staticmethod
    def publish_transferred(
        organization_id: int,
        *,
        order_ref: str,
        from_terminal_id: int | None,
        to_terminal_id: int,
        to_terminal_ref: str,
        source_app_id: str = 'eposone',
        order_id: int | None = None,
    ):
        payload: dict[str, Any] = {
            'order_ref': order_ref,
            'from_terminal_id': from_terminal_id,
            'to_terminal_id': to_terminal_id,
            'to_terminal_ref': to_terminal_ref,
        }
        if order_id is not None:
            payload['order_id'] = int(order_id)
        return AuditService.publish_domain_event(
            organization_id,
            COMMERCE_ORDER_TRANSFERRED,
            payload,
            source_app_id=source_app_id,
        )

    @staticmethod
    def publish_created(
        organization_id: int,
        *,
        order_ref: str,
        status: str,
        payment_status: str | None = None,
        grand_total: float | None = None,
        source_app_id: str = 'eposone',
        extra: dict[str, Any] | None = None,
    ):
        payload: dict[str, Any] = {
            'order_ref': order_ref,
            'status': status,
            'operational_status': status,
        }
        if payment_status is not None:
            payload['payment_status'] = payment_status
        if grand_total is not None:
            payload['grand_total'] = grand_total
        if extra:
            payload.update(extra)
        return AuditService.publish_domain_event(
            organization_id,
            COMMERCE_ORDER_CREATED,
            payload,
            source_app_id=source_app_id,
        )

    @staticmethod
    def publish_payment_status_changed(
        organization_id: int,
        *,
        order_ref: str,
        from_status: str,
        to_status: str,
        source_app_id: str = 'eposone',
        order_id: int | None = None,
        inventory_policy: str | None = None,
    ):
        payload: dict[str, Any] = {
            'order_ref': order_ref,
            'from_payment_status': from_status,
            'to_payment_status': to_status,
        }
        if order_id is not None:
            payload['order_id'] = int(order_id)
        if inventory_policy:
            payload['inventory_policy'] = inventory_policy
        return AuditService.publish_domain_event(
            organization_id,
            COMMERCE_ORDER_PAYMENT_STATUS_CHANGED,
            payload,
            source_app_id=source_app_id,
        )

    @staticmethod
    def publish_fiscal_status_changed(
        organization_id: int,
        *,
        order_ref: str,
        from_status: str,
        to_status: str,
        source_app_id: str = 'eposone',
    ):
        return AuditService.publish_domain_event(
            organization_id,
            COMMERCE_ORDER_FISCAL_STATUS_CHANGED,
            {
                'order_ref': order_ref,
                'from_fiscal_status': from_status,
                'to_fiscal_status': to_status,
            },
            source_app_id=source_app_id,
        )

    @staticmethod
    def publish_status_changed(
        organization_id: int,
        *,
        order_ref: str,
        from_status: str,
        to_status: str,
        source_app_id: str = 'eposone',
        order_id: int | None = None,
        inventory_policy: str | None = None,
    ):
        payload: dict[str, Any] = {
            'order_ref': order_ref,
            'from_status': from_status,
            'to_status': to_status,
            'from_operational_status': from_status,
            'to_operational_status': to_status,
        }
        if order_id is not None:
            payload['order_id'] = int(order_id)
        if inventory_policy:
            payload['inventory_policy'] = inventory_policy
        return AuditService.publish_domain_event(
            organization_id,
            COMMERCE_ORDER_STATUS_CHANGED,
            payload,
            source_app_id=source_app_id,
        )

    @staticmethod
    def publish_confirmed(organization_id: int, *, order_ref: str, source_app_id: str = 'eposone'):
        return AuditService.publish_domain_event(
            organization_id,
            COMMERCE_ORDER_CONFIRMED,
            {'order_ref': order_ref},
            source_app_id=source_app_id,
        )

    @staticmethod
    def publish_cancelled(
        organization_id: int,
        *,
        order_ref: str,
        reason: str | None = None,
        source_app_id: str = 'eposone',
    ):
        payload: dict[str, Any] = {'order_ref': order_ref}
        if reason:
            payload['reason'] = reason
        return AuditService.publish_domain_event(
            organization_id,
            COMMERCE_ORDER_CANCELLED,
            payload,
            source_app_id=source_app_id,
        )
