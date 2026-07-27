"""Puertos (Protocol) — Sprint 3. Firma estable; implementaciones en memory/sqlite/api."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

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


@runtime_checkable
class ProductRepository(Protocol):
    def get(self, product_id: str) -> Product | None: ...

    def list(self, *, active_only: bool = True, limit: int = 200) -> list[Product]: ...

    def upsert(self, product: Product) -> Product: ...

    def deactivate(self, product_id: str) -> Product | None: ...


@runtime_checkable
class CustomerRepository(Protocol):
    def get(self, customer_id: str) -> Customer | None: ...

    def list(self, *, active_only: bool = True, limit: int = 200) -> list[Customer]: ...

    def upsert(self, customer: Customer) -> Customer: ...


@runtime_checkable
class EmployeeRepository(Protocol):
    def get(self, employee_id: str) -> Employee | None: ...

    def list(self, *, active_only: bool = True, limit: int = 200) -> list[Employee]: ...

    def upsert(self, employee: Employee) -> Employee: ...


@runtime_checkable
class OrderRepository(Protocol):
    def get(self, order_id: str) -> Order | None: ...

    def list(
        self,
        *,
        operational_status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Order]: ...

    def create(self, order: Order, *, idempotency_key: str | None = None) -> Order: ...

    def update_status(self, order_id: str, operational_status: str) -> Order: ...

    def add_payment(self, order_id: str, payment: Payment) -> Order: ...


@runtime_checkable
class CashShiftRepository(Protocol):
    def get_open(self, register_id: str) -> CashShift | None: ...

    def open(self, shift: CashShift) -> CashShift: ...

    def close(
        self,
        shift_id: str,
        *,
        closed_by_employee_id: str,
        closing_counted: float,
        expected_cash: float | None = None,
        closed_at: str,
    ) -> CashShift: ...


@runtime_checkable
class InventoryRepository(Protocol):
    def get_balance(self, product_id: str, branch_id: str) -> InventoryBalance | None: ...

    def list_alerts(self, *, below: float = 0.0, limit: int = 100) -> list[InventoryBalance]: ...

    def adjust(
        self,
        product_id: str,
        branch_id: str,
        *,
        delta_on_hand: float,
        updated_at: str,
    ) -> InventoryBalance: ...


@runtime_checkable
class ConfigRepository(Protocol):
    def get_business(self) -> BusinessConfig | None: ...

    def get_branches(self) -> list[Branch]: ...

    def get_registers(self, *, branch_id: str | None = None) -> list[Register]: ...

    def upsert_config(
        self,
        business: BusinessConfig,
        *,
        branches: list[Branch] | None = None,
        registers: list[Register] | None = None,
    ) -> BusinessConfig: ...


@runtime_checkable
class PromotionRepository(Protocol):
    def get(self, promotion_id: str) -> Promotion | None: ...

    def list_active(self, *, as_of: str | None = None, limit: int = 100) -> list[Promotion]: ...


@runtime_checkable
class DeviceRepository(Protocol):
    def get(self, device_id: str) -> Device | None: ...

    def list(self, *, active_only: bool = True, limit: int = 100) -> list[Device]: ...

    def upsert(self, device: Device) -> Device: ...

    def heartbeat(self, device_id: str, *, last_seen_at: str, app_version: str | None = None) -> Device | None: ...
