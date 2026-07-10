"""Provider Memory — Modo Local en proceso (tests / sketch sin disco)."""

from __future__ import annotations

import copy
import uuid
from dataclasses import replace

from nodeone.core.eposone_domain.models import (
    Branch,
    BusinessConfig,
    CashShift,
    Customer,
    Device,
    Employee,
    InventoryBalance,
    Order,
    Payment,
    Product,
    Promotion,
    Register,
)


def _new_id() -> str:
    return str(uuid.uuid4())


class MemoryStore:
    """Almacén compartido entre repos Memory del mismo negocio."""

    def __init__(self) -> None:
        self.business: BusinessConfig | None = None
        self.branches: dict[str, Branch] = {}
        self.registers: dict[str, Register] = {}
        self.products: dict[str, Product] = {}
        self.customers: dict[str, Customer] = {}
        self.employees: dict[str, Employee] = {}
        self.orders: dict[str, Order] = {}
        self.orders_by_idempotency: dict[str, str] = {}
        self.shifts: dict[str, CashShift] = {}
        self.inventory: dict[str, InventoryBalance] = {}  # key product_id|branch_id
        self.promotions: dict[str, Promotion] = {}
        self.devices: dict[str, Device] = {}


def _inv_key(product_id: str, branch_id: str) -> str:
    return f'{product_id}|{branch_id}'


class MemoryProductRepository:
    def __init__(self, store: MemoryStore) -> None:
        self._s = store

    def get(self, product_id: str) -> Product | None:
        return self._s.products.get(product_id)

    def list(self, *, active_only: bool = True, limit: int = 200) -> list[Product]:
        items = list(self._s.products.values())
        if active_only:
            items = [p for p in items if p.active]
        return items[: max(1, min(int(limit), 1000))]

    def upsert(self, product: Product) -> Product:
        pid = product.id or _new_id()
        saved = replace(product, id=pid) if product.id != pid else product
        self._s.products[saved.id] = saved
        return saved

    def deactivate(self, product_id: str) -> Product | None:
        p = self._s.products.get(product_id)
        if p is None:
            return None
        saved = replace(p, active=False)
        self._s.products[product_id] = saved
        return saved


class MemoryCustomerRepository:
    def __init__(self, store: MemoryStore) -> None:
        self._s = store

    def get(self, customer_id: str) -> Customer | None:
        return self._s.customers.get(customer_id)

    def list(self, *, active_only: bool = True, limit: int = 200) -> list[Customer]:
        items = list(self._s.customers.values())
        if active_only:
            items = [c for c in items if c.active]
        return items[: max(1, min(int(limit), 1000))]

    def upsert(self, customer: Customer) -> Customer:
        cid = customer.id or _new_id()
        saved = replace(customer, id=cid) if customer.id != cid else customer
        self._s.customers[saved.id] = saved
        return saved


class MemoryEmployeeRepository:
    def __init__(self, store: MemoryStore) -> None:
        self._s = store

    def get(self, employee_id: str) -> Employee | None:
        return self._s.employees.get(employee_id)

    def list(self, *, active_only: bool = True, limit: int = 200) -> list[Employee]:
        items = list(self._s.employees.values())
        if active_only:
            items = [e for e in items if e.active]
        return items[: max(1, min(int(limit), 1000))]

    def upsert(self, employee: Employee) -> Employee:
        eid = employee.id or _new_id()
        saved = replace(employee, id=eid) if employee.id != eid else employee
        self._s.employees[saved.id] = saved
        return saved


class MemoryOrderRepository:
    def __init__(self, store: MemoryStore) -> None:
        self._s = store

    def get(self, order_id: str) -> Order | None:
        return self._s.orders.get(order_id)

    def list(
        self,
        *,
        operational_status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Order]:
        items = list(self._s.orders.values())
        if operational_status:
            st = operational_status.strip().lower()
            items = [o for o in items if o.operational_status == st]
        items.sort(key=lambda o: o.created_at, reverse=True)
        start = max(0, int(offset))
        end = start + max(1, min(int(limit), 200))
        return items[start:end]

    def create(self, order: Order, *, idempotency_key: str | None = None) -> Order:
        key = (idempotency_key or order.idempotency_key or '').strip()
        if key and key in self._s.orders_by_idempotency:
            existing = self._s.orders.get(self._s.orders_by_idempotency[key])
            if existing is not None:
                return existing
        oid = order.id or _new_id()
        saved = replace(order, id=oid, idempotency_key=key or order.idempotency_key)
        self._s.orders[saved.id] = saved
        if key:
            self._s.orders_by_idempotency[key] = saved.id
        return saved

    def update_status(self, order_id: str, operational_status: str) -> Order:
        o = self._s.orders.get(order_id)
        if o is None:
            raise KeyError(f'order_not_found:{order_id}')
        saved = replace(
            o,
            operational_status=operational_status.strip().lower(),
            version=int(o.version) + 1,
        )
        self._s.orders[order_id] = saved
        return saved

    def add_payment(self, order_id: str, payment: Payment) -> Order:
        o = self._s.orders.get(order_id)
        if o is None:
            raise KeyError(f'order_not_found:{order_id}')
        pay = replace(payment, id=payment.id or _new_id(), order_id=order_id)
        payments = tuple(list(o.payments) + [pay])
        amount_paid = round(sum(p.amount - p.refunded_amount for p in payments), 2)
        if amount_paid <= 0:
            pay_status = 'unpaid'
        elif amount_paid < o.grand_total:
            pay_status = 'partial'
        elif amount_paid == o.grand_total:
            pay_status = 'paid'
        else:
            pay_status = 'overpaid'
        saved = replace(
            o,
            payments=payments,
            amount_paid=amount_paid,
            payment_status=pay_status,
            version=int(o.version) + 1,
        )
        self._s.orders[order_id] = saved
        return saved


class MemoryCashShiftRepository:
    def __init__(self, store: MemoryStore) -> None:
        self._s = store

    def get_open(self, register_id: str) -> CashShift | None:
        for s in self._s.shifts.values():
            if s.register_id == register_id and s.status == 'open':
                return s
        return None

    def open(self, shift: CashShift) -> CashShift:
        if self.get_open(shift.register_id) is not None:
            raise ValueError('shift_already_open')
        sid = shift.id or _new_id()
        saved = replace(shift, id=sid, status='open')
        self._s.shifts[saved.id] = saved
        return saved

    def close(
        self,
        shift_id: str,
        *,
        closed_by_employee_id: str,
        closing_counted: float,
        expected_cash: float | None = None,
        closed_at: str,
    ) -> CashShift:
        s = self._s.shifts.get(shift_id)
        if s is None:
            raise KeyError(f'shift_not_found:{shift_id}')
        if s.status != 'open':
            raise ValueError('shift_not_open')
        saved = replace(
            s,
            status='closed',
            closed_by_employee_id=closed_by_employee_id,
            closing_counted=float(closing_counted),
            expected_cash=expected_cash,
            closed_at=closed_at,
        )
        self._s.shifts[shift_id] = saved
        return saved


class MemoryInventoryRepository:
    def __init__(self, store: MemoryStore) -> None:
        self._s = store

    def get_balance(self, product_id: str, branch_id: str) -> InventoryBalance | None:
        return self._s.inventory.get(_inv_key(product_id, branch_id))

    def list_alerts(self, *, below: float = 0.0, limit: int = 100) -> list[InventoryBalance]:
        items = [
            b
            for b in self._s.inventory.values()
            if (b.quantity_on_hand - b.quantity_reserved) <= float(below)
        ]
        return items[: max(1, min(int(limit), 500))]

    def adjust(
        self,
        product_id: str,
        branch_id: str,
        *,
        delta_on_hand: float,
        updated_at: str,
    ) -> InventoryBalance:
        key = _inv_key(product_id, branch_id)
        cur = self._s.inventory.get(key)
        if cur is None:
            cur = InventoryBalance(
                id=_new_id(),
                product_id=product_id,
                branch_id=branch_id,
                quantity_on_hand=0.0,
                quantity_reserved=0.0,
                updated_at=updated_at,
            )
        saved = replace(
            cur,
            quantity_on_hand=round(float(cur.quantity_on_hand) + float(delta_on_hand), 4),
            updated_at=updated_at,
        )
        self._s.inventory[key] = saved
        return saved


class MemoryConfigRepository:
    def __init__(self, store: MemoryStore) -> None:
        self._s = store

    def get_business(self) -> BusinessConfig | None:
        return self._s.business

    def get_branches(self) -> list[Branch]:
        return list(self._s.branches.values())

    def get_registers(self, *, branch_id: str | None = None) -> list[Register]:
        regs = list(self._s.registers.values())
        if branch_id:
            regs = [r for r in regs if r.branch_id == branch_id]
        return regs

    def upsert_config(
        self,
        business: BusinessConfig,
        *,
        branches: list[Branch] | None = None,
        registers: list[Register] | None = None,
    ) -> BusinessConfig:
        bid = business.id or _new_id()
        saved = replace(business, id=bid) if business.id != bid else business
        self._s.business = saved
        if branches is not None:
            self._s.branches = {b.id: b for b in branches}
        if registers is not None:
            self._s.registers = {r.id: r for r in registers}
        return saved


class MemoryPromotionRepository:
    def __init__(self, store: MemoryStore) -> None:
        self._s = store

    def get(self, promotion_id: str) -> Promotion | None:
        return self._s.promotions.get(promotion_id)

    def list_active(self, *, as_of: str | None = None, limit: int = 100) -> list[Promotion]:
        items = [p for p in self._s.promotions.values() if p.active]
        if as_of:
            filtered: list[Promotion] = []
            for p in items:
                if p.valid_from and as_of < p.valid_from:
                    continue
                if p.valid_to and as_of > p.valid_to:
                    continue
                filtered.append(p)
            items = filtered
        return items[: max(1, min(int(limit), 500))]

    def put(self, promotion: Promotion) -> Promotion:
        """Helper de seed/tests (no en puerto v1)."""
        pid = promotion.id or _new_id()
        saved = replace(promotion, id=pid) if promotion.id != pid else promotion
        self._s.promotions[saved.id] = saved
        return saved


class MemoryDeviceRepository:
    def __init__(self, store: MemoryStore) -> None:
        self._s = store

    def get(self, device_id: str) -> Device | None:
        return self._s.devices.get(device_id)

    def list(self, *, active_only: bool = True, limit: int = 100) -> list[Device]:
        items = list(self._s.devices.values())
        if active_only:
            items = [d for d in items if d.status == 'active']
        return items[: max(1, min(int(limit), 500))]

    def upsert(self, device: Device) -> Device:
        did = device.id or _new_id()
        saved = replace(device, id=did) if device.id != did else device
        self._s.devices[saved.id] = saved
        return saved

    def heartbeat(
        self, device_id: str, *, last_seen_at: str, app_version: str | None = None
    ) -> Device | None:
        d = self._s.devices.get(device_id)
        if d is None:
            return None
        saved = replace(
            d,
            last_seen_at=last_seen_at,
            app_version=app_version if app_version is not None else d.app_version,
        )
        self._s.devices[device_id] = saved
        return saved


class MemoryProviderBundle:
    """Factory conveniente: un store + todos los repos Memory."""

    def __init__(self, store: MemoryStore | None = None) -> None:
        self.store = store or MemoryStore()
        self.products = MemoryProductRepository(self.store)
        self.customers = MemoryCustomerRepository(self.store)
        self.employees = MemoryEmployeeRepository(self.store)
        self.orders = MemoryOrderRepository(self.store)
        self.cash_shifts = MemoryCashShiftRepository(self.store)
        self.inventory = MemoryInventoryRepository(self.store)
        self.config = MemoryConfigRepository(self.store)
        self.promotions = MemoryPromotionRepository(self.store)
        self.devices = MemoryDeviceRepository(self.store)

    def clone_store(self) -> MemoryStore:
        return copy.deepcopy(self.store)
