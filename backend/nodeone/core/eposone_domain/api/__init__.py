"""Provider API — Modo Plataforma. Adapta servicios EN1 a contratos portables.

Convención id: string opaca = ``str(int_id)`` EN1 cuando el recurso ya existe en Core.
El dominio de app no importa este módulo.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from nodeone.core.eposone_domain.models import (
    Branch,
    BusinessConfig,
    CashShift,
    Customer,
    Device,
    Employee,
    InventoryBalance,
    Order,
    OrderLine,
    Payment,
    Product,
    Promotion,
    Register,
)


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def _sid(value: Any) -> str:
    return str(value)


def _iid(value: str) -> int:
    return int(str(value).strip())


def _iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    return dt.astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


_PRODUCT_TYPE_TO_PORTABLE = {
    'good': 'simple',
    'simple': 'simple',
    'kit': 'kit',
    'service': 'service',
    'combo': 'kit',
}

_PORTABLE_TO_PRODUCT_TYPE = {
    'simple': 'good',
    'kit': 'kit',
    'service': 'service',
}


def product_dto_to_portable(dto: Any) -> Product:
    ptype = _PRODUCT_TYPE_TO_PORTABLE.get(str(dto.product_type or '').lower(), 'simple')
    return Product(
        id=_sid(dto.id),
        sku=str(dto.product_ref) if getattr(dto, 'product_ref', None) else None,
        name=str(dto.name),
        description=getattr(dto, 'description', None),
        unit_price=float(dto.unit_price or 0),
        currency=str(dto.currency or 'USD'),
        product_type=ptype,
        active=str(getattr(dto, 'status', 'active')).lower() == 'active',
        track_stock=bool(getattr(dto, 'tracks_inventory', False)),
        created_at=_utcnow_iso(),
    )


def order_dto_to_portable(dto: Any, *, business_id: str, payments: list[Payment] | None = None) -> Order:
    lines = tuple(
        OrderLine(
            id=_sid(getattr(ln, 'id', None) or f'{dto.id}-{i}'),
            description=str(ln.description),
            quantity=float(ln.quantity),
            unit_price=float(ln.unit_price),
            line_total=float(ln.line_total),
            line_status=str(getattr(ln, 'line_status', 'pending') or 'pending'),
            product_id=(str(ln.product_ref) if getattr(ln, 'product_ref', None) else None),
        )
        for i, ln in enumerate(getattr(dto, 'lines', ()) or ())
    )
    branch_id = (
        _sid(dto.branch_org_unit_id)
        if getattr(dto, 'branch_org_unit_id', None) is not None
        else business_id
    )
    return Order(
        id=_sid(dto.id),
        order_ref=str(dto.order_ref),
        business_id=business_id,
        branch_id=branch_id,
        operational_status=str(getattr(dto, 'status', None) or dto.operational_status),
        payment_status=str(dto.payment_status),
        fiscal_status=str(dto.fiscal_status),
        currency=str(dto.currency),
        subtotal=float(dto.subtotal),
        tax_total=float(dto.tax_total),
        discount_total=float(getattr(dto, 'discount_total', 0) or 0),
        grand_total=float(dto.grand_total),
        amount_paid=float(dto.amount_paid),
        version=1,
        lines=lines,
        created_at=_iso(getattr(dto, 'created_at', None)) or _utcnow_iso(),
        register_id=None,
        terminal_id=_sid(dto.pos_terminal_id) if getattr(dto, 'pos_terminal_id', None) else None,
        customer_id=_sid(dto.contact_id) if getattr(dto, 'contact_id', None) else None,
        promotion_id=str(dto.promotion_ref) if getattr(dto, 'promotion_ref', None) else None,
        parent_order_id=_sid(dto.parent_order_id) if getattr(dto, 'parent_order_id', None) else None,
        payments=tuple(payments or ()),
    )


def payment_dto_to_portable(dto: Any, *, order_id: str) -> Payment:
    return Payment(
        id=_sid(dto.id),
        order_id=order_id,
        payment_ref=str(dto.payment_ref),
        status=str(dto.status),
        payment_type=str(dto.payment_type),
        amount=float(dto.amount),
        currency=str(dto.currency),
        refunded_amount=float(getattr(dto, 'refunded_amount', 0) or 0),
        captured_at=_iso(getattr(dto, 'captured_at', None)),
    )


def contact_dto_to_customer(dto: Any) -> Customer:
    return Customer(
        id=_sid(dto.id),
        display_name=str(dto.display_name or ''),
        active=bool(dto.active),
        created_at=_utcnow_iso(),
        email=getattr(dto, 'email', None),
        phone=getattr(dto, 'phone', None) or getattr(dto, 'mobile', None),
        document_id=None,
        tax_id=getattr(dto, 'tax_id', None),
    )


def contact_dto_to_employee(dto: Any) -> Employee:
    roles: list[str] = []
    # EN1 roles → operational roles aproximados
    for label in getattr(dto, 'roles', ()) or ():
        low = str(label).lower()
        if 'cajero' in low or 'cashier' in low:
            roles.append('cashier')
        elif 'vendedor' in low or 'seller' in low:
            roles.append('seller')
        elif 'mesero' in low or 'waiter' in low:
            roles.append('waiter')
        elif 'supervisor' in low:
            roles.append('supervisor')
        elif 'manager' in low or 'gerente' in low:
            roles.append('manager')
    if not roles:
        roles = ['cashier']
    return Employee(
        id=_sid(dto.id),
        display_name=str(dto.display_name or ''),
        has_pin=False,
        operational_roles=tuple(roles),
        active=bool(dto.active),
        created_at=_utcnow_iso(),
        email=getattr(dto, 'email', None),
    )


def cash_shift_dto_to_portable(dto: Any, *, branch_id: str = '') -> CashShift:
    status = str(dto.status or '').lower()
    if status not in ('open', 'closed'):
        status = 'open' if status in ('open', 'reconciling') else 'closed'
    return CashShift(
        id=_sid(dto.id),
        register_id=str(dto.register_ref),
        branch_id=branch_id or str(dto.register_ref),
        opened_by_employee_id='',
        status='open' if status == 'open' else 'closed',
        opening_float=float(dto.opening_balance or 0),
        currency='USD',
        opened_at=_iso(dto.opened_at) or _utcnow_iso(),
        closing_counted=float(dto.counted_amount) if dto.counted_amount is not None else None,
        expected_cash=float(dto.expected_balance) if dto.expected_balance is not None else None,
        closed_at=_iso(dto.closed_at),
    )


class ApiProductRepository:
    def __init__(self, organization_id: int) -> None:
        self._oid = int(organization_id)

    def get(self, product_id: str) -> Product | None:
        from models.core_master import CoreProduct
        from nodeone.core.master.product import product_to_dto

        row = CoreProduct.query.filter_by(organization_id=self._oid, id=_iid(product_id)).first()
        return product_dto_to_portable(product_to_dto(row)) if row else None

    def list(self, *, active_only: bool = True, limit: int = 200) -> list[Product]:
        from nodeone.core.master.constants import PRODUCT_STATUS_ACTIVE
        from nodeone.core.master.product import CoreProductService

        status = PRODUCT_STATUS_ACTIVE if active_only else None
        items = CoreProductService.search(self._oid, status=status, limit=limit)
        return [product_dto_to_portable(p) for p in items]

    def upsert(self, product: Product) -> Product:
        from nodeone.core.master.constants import PRODUCT_STATUS_ACTIVE, PRODUCT_STATUS_INACTIVE
        from nodeone.core.master.product import CoreProductService
        from models.core_master import CoreProduct
        from app import db

        en1_type = _PORTABLE_TO_PRODUCT_TYPE.get(product.product_type, 'good')
        if product.id and product.id.isdigit():
            row = CoreProduct.query.filter_by(organization_id=self._oid, id=int(product.id)).first()
            if row is not None:
                row.name = product.name
                row.description = product.description
                row.unit_price = float(product.unit_price)
                row.currency = product.currency[:8]
                row.product_type = en1_type
                row.tracks_inventory = bool(product.track_stock)
                row.status = PRODUCT_STATUS_ACTIVE if product.active else PRODUCT_STATUS_INACTIVE
                if product.sku:
                    row.product_ref = product.sku[:64]
                db.session.commit()
                from nodeone.core.master.product import product_to_dto

                return product_dto_to_portable(product_to_dto(row))

        created = CoreProductService.create(
            self._oid,
            {
                'product_ref': (product.sku or product.id or f'P-{product.name[:20]}')[:64],
                'name': product.name,
                'description': product.description,
                'product_type': en1_type,
                'tracks_inventory': product.track_stock,
                'unit_price': product.unit_price,
                'currency': product.currency,
                'source_app_id': 'eposone',
                'status': PRODUCT_STATUS_ACTIVE if product.active else PRODUCT_STATUS_INACTIVE,
            },
        )
        return product_dto_to_portable(created)

    def deactivate(self, product_id: str) -> Product | None:
        from nodeone.core.master.constants import PRODUCT_STATUS_INACTIVE
        from models.core_master import CoreProduct
        from app import db
        from nodeone.core.master.product import product_to_dto

        row = CoreProduct.query.filter_by(organization_id=self._oid, id=_iid(product_id)).first()
        if row is None:
            return None
        row.status = PRODUCT_STATUS_INACTIVE
        db.session.commit()
        return product_dto_to_portable(product_to_dto(row))


class ApiCustomerRepository:
    def __init__(self, organization_id: int) -> None:
        self._oid = int(organization_id)

    def get(self, customer_id: str) -> Customer | None:
        from nodeone.core.services.contacts import ContactService

        dto = ContactService.get(self._oid, _iid(customer_id))
        return contact_dto_to_customer(dto) if dto else None

    def list(self, *, active_only: bool = True, limit: int = 200) -> list[Customer]:
        from nodeone.core.services.contacts import ContactService

        rows, _ = ContactService.search(
            self._oid, q='', role='customer', active_only=active_only, limit=limit
        )
        out = [contact_dto_to_customer(r) for r in rows if getattr(r, 'is_customer', True)]
        return out[: max(1, min(int(limit), 1000))]

    def upsert(self, customer: Customer) -> Customer:
        from nodeone.core.services.contacts import ContactService

        if customer.id and customer.id.isdigit():
            existing = ContactService.get(self._oid, int(customer.id))
            if existing is not None:
                # update path vía module service si disponible
                try:
                    from nodeone.modules.contacts import service as _contact_svc

                    _contact_svc.update_contact(
                        self._oid,
                        int(customer.id),
                        {
                            'display_name': customer.display_name,
                            'email': customer.email,
                            'phone': customer.phone,
                            'tax_id': customer.tax_id,
                            'active': customer.active,
                            'is_customer': True,
                        },
                    )
                    dto = ContactService.get(self._oid, int(customer.id))
                    return contact_dto_to_customer(dto) if dto else customer
                except Exception:
                    return contact_dto_to_customer(existing)

        created = ContactService.create(
            self._oid,
            {
                'display_name': customer.display_name,
                'email': customer.email,
                'phone': customer.phone,
                'tax_id': customer.tax_id,
                'is_customer': True,
                'active': customer.active,
            },
        )
        return contact_dto_to_customer(created)


class ApiEmployeeRepository:
    """Empleados vía contactos con ``is_employee`` (aprox. v1)."""

    def __init__(self, organization_id: int) -> None:
        self._oid = int(organization_id)

    def get(self, employee_id: str) -> Employee | None:
        from nodeone.core.services.contacts import ContactService

        dto = ContactService.get(self._oid, _iid(employee_id))
        if dto is None or not getattr(dto, 'is_employee', False):
            return None
        return contact_dto_to_employee(dto)

    def list(self, *, active_only: bool = True, limit: int = 200) -> list[Employee]:
        from nodeone.core.services.contacts import ContactService

        rows, _ = ContactService.search(
            self._oid, q='', role='employee', active_only=active_only, limit=limit
        )
        return [contact_dto_to_employee(r) for r in rows][: max(1, min(int(limit), 1000))]

    def upsert(self, employee: Employee) -> Employee:
        from nodeone.core.services.contacts import ContactService

        created = ContactService.create(
            self._oid,
            {
                'display_name': employee.display_name,
                'email': employee.email,
                'is_employee': True,
                'active': employee.active,
            },
        )
        return contact_dto_to_employee(created)


class ApiOrderRepository:
    def __init__(self, organization_id: int, *, business_id: str | None = None) -> None:
        self._oid = int(organization_id)
        self._business_id = business_id or _sid(organization_id)

    def _payments_for(self, order_id: int) -> list[Payment]:
        from nodeone.core.commerce.payment import PaymentService

        return [
            payment_dto_to_portable(p, order_id=_sid(order_id))
            for p in PaymentService.list_for_order(self._oid, order_id)
        ]

    def get(self, order_id: str) -> Order | None:
        from nodeone.core.commerce.order import OrderService

        dto = OrderService.get(self._oid, _iid(order_id))
        if dto is None:
            return None
        return order_dto_to_portable(
            dto,
            business_id=self._business_id,
            payments=self._payments_for(int(dto.id)),
        )

    def list(
        self,
        *,
        operational_status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Order]:
        from nodeone.core.commerce.order import OrderService

        items, _ = OrderService.search(
            self._oid, status=operational_status, limit=limit, offset=offset
        )
        return [
            order_dto_to_portable(o, business_id=self._business_id, payments=self._payments_for(int(o.id)))
            for o in items
        ]

    def create(self, order: Order, *, idempotency_key: str | None = None) -> Order:
        from nodeone.core.commerce.order import OrderService

        data: dict[str, Any] = {
            'order_ref': order.order_ref,
            'currency': order.currency,
            'tax_total': order.tax_total,
            'operational_status': order.operational_status,
            'notes': None,
            'lines': [
                {
                    'description': ln.description,
                    'quantity': ln.quantity,
                    'unit_price': ln.unit_price,
                    'product_ref': ln.product_id,
                    'line_status': ln.line_status,
                }
                for ln in order.lines
            ],
        }
        if order.customer_id and order.customer_id.isdigit():
            data['contact_id'] = int(order.customer_id)
        if order.branch_id and order.branch_id.isdigit():
            data['branch_org_unit_id'] = int(order.branch_id)
        if order.terminal_id and order.terminal_id.isdigit():
            data['pos_terminal_id'] = int(order.terminal_id)
        if order.promotion_id:
            data['promotion_ref'] = order.promotion_id
        if idempotency_key:
            data['idempotency_key'] = idempotency_key
        dto = OrderService.create(self._oid, data, source_app_id='eposone')
        return order_dto_to_portable(dto, business_id=self._business_id)

    def update_status(self, order_id: str, operational_status: str) -> Order:
        from nodeone.core.commerce.order import OrderService

        dto = OrderService.transition_status(
            self._oid, _iid(order_id), operational_status, source_app_id='eposone'
        )
        return order_dto_to_portable(
            dto,
            business_id=self._business_id,
            payments=self._payments_for(int(dto.id)),
        )

    def add_payment(self, order_id: str, payment: Payment) -> Order:
        from nodeone.core.commerce.payment import PaymentService

        PaymentService.capture(
            self._oid,
            {
                'order_id': _iid(order_id),
                'amount': payment.amount,
                'currency': payment.currency,
                'payment_type': payment.payment_type,
                'payment_ref': payment.payment_ref,
                'idempotency_key': payment.idempotency_key,
            },
            source_app_id='eposone',
        )
        got = self.get(order_id)
        if got is None:
            raise KeyError(f'order_not_found:{order_id}')
        return got


class ApiCashShiftRepository:
    def __init__(self, organization_id: int, *, branch_id: str = '') -> None:
        self._oid = int(organization_id)
        self._branch_id = branch_id

    def get_open(self, register_id: str) -> CashShift | None:
        from nodeone.core.commerce.cash import CashRegisterService
        from nodeone.core.commerce.persistence import cash_shift_to_dto

        row = CashRegisterService.get_open_shift(self._oid, register_id)
        if row is None:
            return None
        return cash_shift_dto_to_portable(
            cash_shift_to_dto(row), branch_id=self._branch_id
        )

    def open(self, shift: CashShift) -> CashShift:
        from nodeone.core.commerce.cash import CashRegisterService

        dto = CashRegisterService.open_shift(
            self._oid,
            register_ref=shift.register_id,
            opening_balance=shift.opening_float,
            source_app_id='eposone',
        )
        return cash_shift_dto_to_portable(dto, branch_id=shift.branch_id or self._branch_id)

    def close(
        self,
        shift_id: str,
        *,
        closed_by_employee_id: str,
        closing_counted: float,
        expected_cash: float | None = None,
        closed_at: str,
    ) -> CashShift:
        from nodeone.core.commerce.cash import CashRegisterService

        _ = closed_by_employee_id, expected_cash, closed_at
        # EN1 exige reconciliar (begin_reconcile) antes de close_shift
        CashRegisterService.begin_reconcile(
            self._oid,
            _iid(shift_id),
            counted_amount=float(closing_counted),
            source_app_id='eposone',
        )
        dto = CashRegisterService.close_shift(
            self._oid, _iid(shift_id), source_app_id='eposone'
        )
        return cash_shift_dto_to_portable(dto, branch_id=self._branch_id)


class ApiInventoryRepository:
    def __init__(self, organization_id: int) -> None:
        self._oid = int(organization_id)

    def get_balance(self, product_id: str, branch_id: str) -> InventoryBalance | None:
        from nodeone.core.commerce.stock import StockService
        from models.core_master import CoreProduct

        prod = CoreProduct.query.filter_by(organization_id=self._oid, id=_iid(product_id)).first()
        if prod is None:
            return None
        items = StockService.list_balances(
            self._oid,
            warehouse_org_unit_id=_iid(branch_id) if branch_id.isdigit() else None,
            product_ref=str(prod.product_ref),
            limit=1,
        )
        if not items:
            return None
        b = items[0]
        return InventoryBalance(
            id=_sid(b.id),
            product_id=product_id,
            branch_id=_sid(b.warehouse_org_unit_id),
            quantity_on_hand=float(b.quantity_on_hand),
            quantity_reserved=float(b.quantity_reserved),
            updated_at=_utcnow_iso(),
        )

    def list_alerts(self, *, below: float = 0.0, limit: int = 100) -> list[InventoryBalance]:
        from nodeone.core.commerce.stock import StockService

        items = StockService.list_balances(self._oid, limit=limit)
        out: list[InventoryBalance] = []
        for b in items:
            if float(b.quantity_available) <= float(below):
                out.append(
                    InventoryBalance(
                        id=_sid(b.id),
                        product_id=str(b.product_ref),
                        branch_id=_sid(b.warehouse_org_unit_id),
                        quantity_on_hand=float(b.quantity_on_hand),
                        quantity_reserved=float(b.quantity_reserved),
                        updated_at=_utcnow_iso(),
                    )
                )
        return out[: max(1, min(int(limit), 500))]

    def adjust(
        self,
        product_id: str,
        branch_id: str,
        *,
        delta_on_hand: float,
        updated_at: str,
    ) -> InventoryBalance:
        from nodeone.core.commerce.constants import STOCK_MOVEMENT_ADJUST
        from nodeone.core.commerce.stock import StockService, StockValidationError
        from models.core_master import CoreProduct

        _ = updated_at
        prod = CoreProduct.query.filter_by(organization_id=self._oid, id=_iid(product_id)).first()
        if prod is None:
            raise KeyError(f'product_not_found:{product_id}')
        result = StockService.apply_movement(
            self._oid,
            warehouse_org_unit_id=_iid(branch_id),
            product_ref=str(prod.product_ref),
            movement_type=STOCK_MOVEMENT_ADJUST,
            quantity=float(delta_on_hand),
            allow_negative=True,
        )
        if result.get('status') != 'applied':
            raise StockValidationError(str(result.get('reason') or 'adjust_failed'))
        bal = self.get_balance(product_id, branch_id)
        if bal is None:
            raise KeyError(f'balance_missing:{product_id}:{branch_id}')
        return bal


class ApiConfigRepository:
    def __init__(self, organization_id: int) -> None:
        self._oid = int(organization_id)

    def get_business(self) -> BusinessConfig | None:
        from models.saas import SaasOrganization

        org = SaasOrganization.query.get(self._oid)
        if org is None:
            return BusinessConfig(
                id=_sid(self._oid),
                name=f'Organization {self._oid}',
                currency='USD',
                created_at=_utcnow_iso(),
            )
        return BusinessConfig(
            id=_sid(org.id),
            name=str(org.name or f'Org {org.id}'),
            currency='USD',
            created_at=_iso(getattr(org, 'created_at', None)) or _utcnow_iso(),
            legal_name=getattr(org, 'legal_name', None),
            tax_id=getattr(org, 'tax_id', None),
            country_code=None,
            timezone=None,
        )

    def get_branches(self) -> list[Branch]:
        from nodeone.core.master.constants import ORG_UNIT_TYPE_BRANCH
        from nodeone.core.services.org_unit import OrgUnitService

        units = OrgUnitService.list_units(self._oid, unit_type=ORG_UNIT_TYPE_BRANCH)
        business_id = _sid(self._oid)
        return [
            Branch(
                id=_sid(u.id),
                business_id=business_id,
                name=str(u.name),
                is_default=False,
            )
            for u in units
        ]

    def get_registers(self, *, branch_id: str | None = None) -> list[Register]:
        from nodeone.core.master.constants import ORG_UNIT_TYPE_REGISTER
        from nodeone.core.services.org_unit import OrgUnitService

        units = OrgUnitService.list_units(self._oid, unit_type=ORG_UNIT_TYPE_REGISTER)
        out: list[Register] = []
        for u in units:
            # parent_id de register → branch cuando aplica
            rid_branch = _sid(u.parent_id) if getattr(u, 'parent_id', None) else (branch_id or '')
            if branch_id and rid_branch and rid_branch != branch_id:
                continue
            out.append(
                Register(
                    id=_sid(u.id),
                    branch_id=rid_branch or _sid(u.id),
                    name=str(u.name),
                    is_default=False,
                )
            )
        return out
    def upsert_config(
        self,
        business: BusinessConfig,
        *,
        branches: list[Branch] | None = None,
        registers: list[Register] | None = None,
    ) -> BusinessConfig:
        # Lectura dominante en Plataforma; escritura de org es SaaS admin fuera del POS.
        _ = branches, registers
        return self.get_business() or business


class ApiPromotionRepository:
    def __init__(self, organization_id: int) -> None:
        self._oid = int(organization_id)

    def get(self, promotion_id: str) -> Promotion | None:
        try:
            from nodeone.modules.eposone.promotion_service import PromotionService

            promo = PromotionService.get_by_ref(self._oid, promotion_id)
            if promo is None and promotion_id.isdigit():
                try:
                    promo = PromotionService.resolve_by_id(self._oid, int(promotion_id))
                except Exception:
                    promo = None
            if promo is None or not promo.active:
                return None
            return Promotion(
                id=str(promo.promo_ref),
                name=str(promo.name),
                active=bool(promo.active),
                rules={'promo_type': promo.promo_type, 'value': promo.value},
            )
        except Exception:
            return None

    def list_active(self, *, as_of: str | None = None, limit: int = 100) -> list[Promotion]:
        _ = as_of
        try:
            from nodeone.modules.eposone.promotion_service import PromotionService

            items = [
                p for p in PromotionService.list_promotions(self._oid, limit=limit) if p.active
            ]
            return [
                Promotion(
                    id=str(p.promo_ref),
                    name=str(p.name),
                    active=bool(p.active),
                    rules={'promo_type': p.promo_type, 'value': p.value},
                )
                for p in items
            ]
        except Exception:
            return []


class ApiDeviceRepository:
    """Adapter sobre PosTerminalService — ``device.id`` = ``terminal_ref`` (UUID)."""

    def __init__(self, organization_id: int) -> None:
        self._oid = int(organization_id)

    def get(self, device_id: str) -> Device | None:
        from nodeone.core.commerce.pos import PosTerminalService

        dto = PosTerminalService.get_by_ref(self._oid, device_id)
        return terminal_dto_to_device(dto) if dto else None

    def list(self, *, active_only: bool = True, limit: int = 100) -> list[Device]:
        from nodeone.core.commerce.pos import PosTerminalService

        items = PosTerminalService.list_terminals(self._oid, limit=limit)
        out = [terminal_dto_to_device(t) for t in items]
        if active_only:
            out = [d for d in out if d.status == 'active']
        return out

    def upsert(self, device: Device) -> Device:
        from nodeone.core.commerce.pos import PosTerminalService

        dto = PosTerminalService.register(
            self._oid,
            terminal_ref=device.id,
            device_label=device.name,
            register_ref=device.register_id,
            profile=device.profile,
            platform=device.platform,
            device_model=device.device_model,
            app_version=device.app_version,
            android_version=getattr(device, 'android_version', None),
            branch_ref=device.branch_id,
            pos_ref=getattr(device, 'pos_id', None),
            sync_enabled=device.sync_enabled,
        )
        return terminal_dto_to_device(dto)

    def heartbeat(
        self, device_id: str, *, last_seen_at: str, app_version: str | None = None
    ) -> Device | None:
        from nodeone.core.commerce.pos import PosTerminalService

        dto = PosTerminalService.heartbeat(
            self._oid,
            device_id,
            last_seen_at=last_seen_at,
            app_version=app_version,
        )
        return terminal_dto_to_device(dto) if dto else None


def terminal_dto_to_device(dto: Any) -> Device:
    profile = str(getattr(dto, 'profile', None) or 'fixed')
    if profile not in ('fixed', 'handheld'):
        profile = 'fixed'
    status = str(getattr(dto, 'status', None) or 'active').lower()
    if status not in ('active', 'inactive'):
        status = 'active'
    return Device(
        id=str(dto.terminal_ref),
        profile=profile,
        name=getattr(dto, 'device_label', None),
        business_id=_sid(dto.organization_id) if getattr(dto, 'organization_id', None) else None,
        branch_id=getattr(dto, 'branch_ref', None),
        register_id=getattr(dto, 'register_ref', None),
        pos_id=getattr(dto, 'pos_ref', None),
        app_version=getattr(dto, 'app_version', None),
        android_version=getattr(dto, 'android_version', None),
        platform=getattr(dto, 'platform', None),
        device_model=getattr(dto, 'device_model', None),
        status=status,
        sync_enabled=bool(getattr(dto, 'sync_enabled', True)),
        last_seen_at=_iso(getattr(dto, 'last_seen_at', None)),
        created_at=None,
    )


class ApiProviderBundle:
    def __init__(self, organization_id: int) -> None:
        oid = int(organization_id)
        bid = _sid(oid)
        self.organization_id = oid
        self.products = ApiProductRepository(oid)
        self.customers = ApiCustomerRepository(oid)
        self.employees = ApiEmployeeRepository(oid)
        self.orders = ApiOrderRepository(oid, business_id=bid)
        self.cash_shifts = ApiCashShiftRepository(oid)
        self.inventory = ApiInventoryRepository(oid)
        self.config = ApiConfigRepository(oid)
        self.promotions = ApiPromotionRepository(oid)
        self.devices = ApiDeviceRepository(oid)
