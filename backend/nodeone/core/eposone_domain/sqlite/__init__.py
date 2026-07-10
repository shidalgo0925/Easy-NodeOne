"""Provider SQLite — Modo Local en disco (stdlib sqlite3; sin ORM).

Esquema mínimo alineado a contratos Sprint 2. El dominio no importa este módulo.
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import contextmanager
from dataclasses import asdict, replace
from pathlib import Path
from typing import Any, Iterator

from nodeone.core.eposone_domain.models import (
    Address,
    Branch,
    BusinessConfig,
    CashShift,
    Customer,
    Device,
    Employee,
    InventoryBalance,
    KitLine,
    Order,
    OrderLine,
    Payment,
    Product,
    Promotion,
    Register,
    TaxRate,
)

SCHEMA = """
CREATE TABLE IF NOT EXISTS business (
  id TEXT PRIMARY KEY,
  payload TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS branch (
  id TEXT PRIMARY KEY,
  business_id TEXT NOT NULL,
  payload TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS register (
  id TEXT PRIMARY KEY,
  branch_id TEXT NOT NULL,
  payload TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS product (
  id TEXT PRIMARY KEY,
  active INTEGER NOT NULL,
  payload TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS customer (
  id TEXT PRIMARY KEY,
  active INTEGER NOT NULL,
  payload TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS employee (
  id TEXT PRIMARY KEY,
  active INTEGER NOT NULL,
  payload TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS "order" (
  id TEXT PRIMARY KEY,
  operational_status TEXT NOT NULL,
  created_at TEXT NOT NULL,
  idempotency_key TEXT,
  payload TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS ux_order_idem ON "order"(idempotency_key)
  WHERE idempotency_key IS NOT NULL AND idempotency_key != '';
CREATE TABLE IF NOT EXISTS cash_shift (
  id TEXT PRIMARY KEY,
  register_id TEXT NOT NULL,
  status TEXT NOT NULL,
  payload TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS inventory (
  id TEXT PRIMARY KEY,
  product_id TEXT NOT NULL,
  branch_id TEXT NOT NULL,
  quantity_on_hand REAL NOT NULL,
  quantity_reserved REAL NOT NULL,
  updated_at TEXT NOT NULL,
  UNIQUE(product_id, branch_id)
);
CREATE TABLE IF NOT EXISTS promotion (
  id TEXT PRIMARY KEY,
  active INTEGER NOT NULL,
  payload TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS device (
  id TEXT PRIMARY KEY,
  status TEXT NOT NULL,
  payload TEXT NOT NULL
);
"""


def _new_id() -> str:
    return str(uuid.uuid4())


def _dumps(obj: Any) -> str:
    if hasattr(obj, '__dataclass_fields__'):
        return json.dumps(asdict(obj), ensure_ascii=False, default=str)
    return json.dumps(obj, ensure_ascii=False, default=str)


def _address(d: dict[str, Any] | None) -> Address | None:
    if not d:
        return None
    return Address(
        line1=d.get('line1'),
        city=d.get('city'),
        region=d.get('region'),
        postal_code=d.get('postal_code'),
    )


def _product_from(d: dict[str, Any]) -> Product:
    kits = tuple(
        KitLine(component_product_id=str(k['component_product_id']), quantity=float(k['quantity']))
        for k in (d.get('kit_lines') or [])
    )
    return Product(
        id=str(d['id']),
        name=str(d['name']),
        unit_price=float(d['unit_price']),
        currency=str(d['currency']),
        product_type=str(d['product_type']),
        active=bool(d['active']),
        track_stock=bool(d['track_stock']),
        created_at=str(d['created_at']),
        sku=d.get('sku'),
        description=d.get('description'),
        tax_rate_id=d.get('tax_rate_id'),
        kit_lines=kits,
        updated_at=d.get('updated_at'),
    )


def _customer_from(d: dict[str, Any]) -> Customer:
    return Customer(
        id=str(d['id']),
        display_name=str(d['display_name']),
        active=bool(d['active']),
        created_at=str(d['created_at']),
        email=d.get('email'),
        phone=d.get('phone'),
        document_id=d.get('document_id'),
        tax_id=d.get('tax_id'),
        notes=d.get('notes'),
        updated_at=d.get('updated_at'),
    )


def _employee_from(d: dict[str, Any]) -> Employee:
    roles = tuple(str(r) for r in (d.get('operational_roles') or ()))
    return Employee(
        id=str(d['id']),
        display_name=str(d['display_name']),
        has_pin=bool(d['has_pin']),
        operational_roles=roles,
        active=bool(d['active']),
        created_at=str(d['created_at']),
        email=d.get('email'),
        pin_hint=d.get('pin_hint'),
    )


def _order_from(d: dict[str, Any]) -> Order:
    lines = tuple(
        OrderLine(
            id=str(ln['id']),
            description=str(ln['description']),
            quantity=float(ln['quantity']),
            unit_price=float(ln['unit_price']),
            line_total=float(ln['line_total']),
            line_status=str(ln['line_status']),
            product_id=ln.get('product_id'),
            tax_rate_id=ln.get('tax_rate_id'),
        )
        for ln in (d.get('lines') or [])
    )
    payments = tuple(
        Payment(
            id=str(p['id']),
            order_id=str(p['order_id']),
            payment_ref=str(p['payment_ref']),
            status=str(p['status']),
            payment_type=str(p['payment_type']),
            amount=float(p['amount']),
            currency=str(p['currency']),
            refunded_amount=float(p.get('refunded_amount') or 0),
            captured_at=p.get('captured_at'),
            idempotency_key=p.get('idempotency_key'),
        )
        for p in (d.get('payments') or [])
    )
    return Order(
        id=str(d['id']),
        order_ref=str(d['order_ref']),
        business_id=str(d['business_id']),
        branch_id=str(d['branch_id']),
        operational_status=str(d['operational_status']),
        payment_status=str(d['payment_status']),
        fiscal_status=str(d['fiscal_status']),
        currency=str(d['currency']),
        subtotal=float(d['subtotal']),
        tax_total=float(d['tax_total']),
        discount_total=float(d.get('discount_total') or 0),
        grand_total=float(d['grand_total']),
        amount_paid=float(d.get('amount_paid') or 0),
        version=int(d.get('version') or 1),
        lines=lines,
        created_at=str(d['created_at']),
        register_id=d.get('register_id'),
        terminal_id=d.get('terminal_id'),
        customer_id=d.get('customer_id'),
        created_by_employee_id=d.get('created_by_employee_id'),
        cashier_employee_id=d.get('cashier_employee_id'),
        promotion_id=d.get('promotion_id'),
        parent_order_id=d.get('parent_order_id'),
        payments=payments,
        updated_at=d.get('updated_at'),
        idempotency_key=d.get('idempotency_key'),
    )


def _shift_from(d: dict[str, Any]) -> CashShift:
    return CashShift(
        id=str(d['id']),
        register_id=str(d['register_id']),
        branch_id=str(d['branch_id']),
        opened_by_employee_id=str(d['opened_by_employee_id']),
        status=str(d['status']),
        opening_float=float(d['opening_float']),
        currency=str(d['currency']),
        opened_at=str(d['opened_at']),
        closed_by_employee_id=d.get('closed_by_employee_id'),
        closing_counted=d.get('closing_counted'),
        expected_cash=d.get('expected_cash'),
        closed_at=d.get('closed_at'),
    )


def _business_from(d: dict[str, Any]) -> BusinessConfig:
    rates = tuple(
        TaxRate(
            id=str(t['id']),
            name=str(t['name']),
            rate=float(t['rate']),
            inclusive=bool(t.get('inclusive', False)),
        )
        for t in (d.get('tax_rates') or [])
    )
    return BusinessConfig(
        id=str(d['id']),
        name=str(d['name']),
        currency=str(d['currency']),
        created_at=str(d['created_at']),
        legal_name=d.get('legal_name'),
        tax_id=d.get('tax_id'),
        country_code=d.get('country_code'),
        timezone=d.get('timezone'),
        address=_address(d.get('address')),
        tax_rates=rates,
        updated_at=d.get('updated_at'),
    )


def _promo_from(d: dict[str, Any]) -> Promotion:
    return Promotion(
        id=str(d['id']),
        name=str(d['name']),
        active=bool(d['active']),
        rules=dict(d.get('rules') or {}),
        valid_from=d.get('valid_from'),
        valid_to=d.get('valid_to'),
    )


def _device_from(d: dict[str, Any]) -> Device:
    return Device(
        id=str(d['id']),
        profile=str(d.get('profile') or 'fixed'),
        name=d.get('name'),
        business_id=d.get('business_id'),
        branch_id=d.get('branch_id'),
        register_id=d.get('register_id'),
        app_version=d.get('app_version'),
        platform=d.get('platform'),
        device_model=d.get('device_model'),
        status=str(d.get('status') or 'active'),
        sync_enabled=bool(d.get('sync_enabled', True)),
        last_seen_at=d.get('last_seen_at'),
        created_at=d.get('created_at'),
    )


class SqliteConnection:
    def __init__(self, path: str | Path) -> None:
        self.path = str(path)
        self._init_schema()

    def _init_schema(self) -> None:
        with self.connect() as conn:
            conn.executescript(SCHEMA)
            conn.commit()

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()


class SqliteProductRepository:
    def __init__(self, db: SqliteConnection) -> None:
        self._db = db

    def get(self, product_id: str) -> Product | None:
        with self._db.connect() as conn:
            row = conn.execute('SELECT payload FROM product WHERE id = ?', (product_id,)).fetchone()
        return _product_from(json.loads(row['payload'])) if row else None

    def list(self, *, active_only: bool = True, limit: int = 200) -> list[Product]:
        lim = max(1, min(int(limit), 1000))
        sql = 'SELECT payload FROM product'
        args: tuple[Any, ...] = ()
        if active_only:
            sql += ' WHERE active = 1'
        sql += ' LIMIT ?'
        args = (lim,)
        with self._db.connect() as conn:
            rows = conn.execute(sql, args).fetchall()
        return [_product_from(json.loads(r['payload'])) for r in rows]

    def upsert(self, product: Product) -> Product:
        pid = product.id or _new_id()
        saved = replace(product, id=pid) if product.id != pid else product
        with self._db.connect() as conn:
            conn.execute(
                'INSERT INTO product(id, active, payload) VALUES(?,?,?) '
                'ON CONFLICT(id) DO UPDATE SET active=excluded.active, payload=excluded.payload',
                (saved.id, 1 if saved.active else 0, _dumps(saved)),
            )
            conn.commit()
        return saved

    def deactivate(self, product_id: str) -> Product | None:
        p = self.get(product_id)
        if p is None:
            return None
        return self.upsert(replace(p, active=False))


class SqliteCustomerRepository:
    def __init__(self, db: SqliteConnection) -> None:
        self._db = db

    def get(self, customer_id: str) -> Customer | None:
        with self._db.connect() as conn:
            row = conn.execute('SELECT payload FROM customer WHERE id = ?', (customer_id,)).fetchone()
        return _customer_from(json.loads(row['payload'])) if row else None

    def list(self, *, active_only: bool = True, limit: int = 200) -> list[Customer]:
        lim = max(1, min(int(limit), 1000))
        sql = 'SELECT payload FROM customer'
        if active_only:
            sql += ' WHERE active = 1'
        sql += ' LIMIT ?'
        with self._db.connect() as conn:
            rows = conn.execute(sql, (lim,)).fetchall()
        return [_customer_from(json.loads(r['payload'])) for r in rows]

    def upsert(self, customer: Customer) -> Customer:
        cid = customer.id or _new_id()
        saved = replace(customer, id=cid) if customer.id != cid else customer
        with self._db.connect() as conn:
            conn.execute(
                'INSERT INTO customer(id, active, payload) VALUES(?,?,?) '
                'ON CONFLICT(id) DO UPDATE SET active=excluded.active, payload=excluded.payload',
                (saved.id, 1 if saved.active else 0, _dumps(saved)),
            )
            conn.commit()
        return saved


class SqliteEmployeeRepository:
    def __init__(self, db: SqliteConnection) -> None:
        self._db = db

    def get(self, employee_id: str) -> Employee | None:
        with self._db.connect() as conn:
            row = conn.execute('SELECT payload FROM employee WHERE id = ?', (employee_id,)).fetchone()
        return _employee_from(json.loads(row['payload'])) if row else None

    def list(self, *, active_only: bool = True, limit: int = 200) -> list[Employee]:
        lim = max(1, min(int(limit), 1000))
        sql = 'SELECT payload FROM employee'
        if active_only:
            sql += ' WHERE active = 1'
        sql += ' LIMIT ?'
        with self._db.connect() as conn:
            rows = conn.execute(sql, (lim,)).fetchall()
        return [_employee_from(json.loads(r['payload'])) for r in rows]

    def upsert(self, employee: Employee) -> Employee:
        eid = employee.id or _new_id()
        saved = replace(employee, id=eid) if employee.id != eid else employee
        with self._db.connect() as conn:
            conn.execute(
                'INSERT INTO employee(id, active, payload) VALUES(?,?,?) '
                'ON CONFLICT(id) DO UPDATE SET active=excluded.active, payload=excluded.payload',
                (saved.id, 1 if saved.active else 0, _dumps(saved)),
            )
            conn.commit()
        return saved


class SqliteOrderRepository:
    def __init__(self, db: SqliteConnection) -> None:
        self._db = db

    def get(self, order_id: str) -> Order | None:
        with self._db.connect() as conn:
            row = conn.execute('SELECT payload FROM "order" WHERE id = ?', (order_id,)).fetchone()
        return _order_from(json.loads(row['payload'])) if row else None

    def list(
        self,
        *,
        operational_status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Order]:
        lim = max(1, min(int(limit), 200))
        off = max(0, int(offset))
        sql = 'SELECT payload FROM "order"'
        args: list[Any] = []
        if operational_status:
            sql += ' WHERE operational_status = ?'
            args.append(operational_status.strip().lower())
        sql += ' ORDER BY created_at DESC LIMIT ? OFFSET ?'
        args.extend([lim, off])
        with self._db.connect() as conn:
            rows = conn.execute(sql, args).fetchall()
        return [_order_from(json.loads(r['payload'])) for r in rows]

    def create(self, order: Order, *, idempotency_key: str | None = None) -> Order:
        key = (idempotency_key or order.idempotency_key or '').strip() or None
        if key:
            with self._db.connect() as conn:
                row = conn.execute(
                    'SELECT payload FROM "order" WHERE idempotency_key = ?', (key,)
                ).fetchone()
            if row:
                return _order_from(json.loads(row['payload']))
        oid = order.id or _new_id()
        saved = replace(order, id=oid, idempotency_key=key)
        with self._db.connect() as conn:
            conn.execute(
                'INSERT INTO "order"(id, operational_status, created_at, idempotency_key, payload) '
                'VALUES(?,?,?,?,?)',
                (saved.id, saved.operational_status, saved.created_at, key, _dumps(saved)),
            )
            conn.commit()
        return saved

    def update_status(self, order_id: str, operational_status: str) -> Order:
        o = self.get(order_id)
        if o is None:
            raise KeyError(f'order_not_found:{order_id}')
        saved = replace(
            o,
            operational_status=operational_status.strip().lower(),
            version=int(o.version) + 1,
        )
        with self._db.connect() as conn:
            conn.execute(
                'UPDATE "order" SET operational_status = ?, payload = ? WHERE id = ?',
                (saved.operational_status, _dumps(saved), order_id),
            )
            conn.commit()
        return saved

    def add_payment(self, order_id: str, payment: Payment) -> Order:
        o = self.get(order_id)
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
        with self._db.connect() as conn:
            conn.execute(
                'UPDATE "order" SET payload = ? WHERE id = ?',
                (_dumps(saved), order_id),
            )
            conn.commit()
        return saved


class SqliteCashShiftRepository:
    def __init__(self, db: SqliteConnection) -> None:
        self._db = db

    def get_open(self, register_id: str) -> CashShift | None:
        with self._db.connect() as conn:
            row = conn.execute(
                'SELECT payload FROM cash_shift WHERE register_id = ? AND status = ?',
                (register_id, 'open'),
            ).fetchone()
        return _shift_from(json.loads(row['payload'])) if row else None

    def open(self, shift: CashShift) -> CashShift:
        if self.get_open(shift.register_id) is not None:
            raise ValueError('shift_already_open')
        sid = shift.id or _new_id()
        saved = replace(shift, id=sid, status='open')
        with self._db.connect() as conn:
            conn.execute(
                'INSERT INTO cash_shift(id, register_id, status, payload) VALUES(?,?,?,?)',
                (saved.id, saved.register_id, 'open', _dumps(saved)),
            )
            conn.commit()
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
        with self._db.connect() as conn:
            row = conn.execute('SELECT payload FROM cash_shift WHERE id = ?', (shift_id,)).fetchone()
        if row is None:
            raise KeyError(f'shift_not_found:{shift_id}')
        s = _shift_from(json.loads(row['payload']))
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
        with self._db.connect() as conn:
            conn.execute(
                'UPDATE cash_shift SET status = ?, payload = ? WHERE id = ?',
                ('closed', _dumps(saved), shift_id),
            )
            conn.commit()
        return saved


class SqliteInventoryRepository:
    def __init__(self, db: SqliteConnection) -> None:
        self._db = db

    def get_balance(self, product_id: str, branch_id: str) -> InventoryBalance | None:
        with self._db.connect() as conn:
            row = conn.execute(
                'SELECT id, product_id, branch_id, quantity_on_hand, quantity_reserved, updated_at '
                'FROM inventory WHERE product_id = ? AND branch_id = ?',
                (product_id, branch_id),
            ).fetchone()
        if row is None:
            return None
        return InventoryBalance(
            id=str(row['id']),
            product_id=str(row['product_id']),
            branch_id=str(row['branch_id']),
            quantity_on_hand=float(row['quantity_on_hand']),
            quantity_reserved=float(row['quantity_reserved']),
            updated_at=str(row['updated_at']),
        )

    def list_alerts(self, *, below: float = 0.0, limit: int = 100) -> list[InventoryBalance]:
        lim = max(1, min(int(limit), 500))
        with self._db.connect() as conn:
            rows = conn.execute(
                'SELECT id, product_id, branch_id, quantity_on_hand, quantity_reserved, updated_at '
                'FROM inventory WHERE (quantity_on_hand - quantity_reserved) <= ? LIMIT ?',
                (float(below), lim),
            ).fetchall()
        return [
            InventoryBalance(
                id=str(r['id']),
                product_id=str(r['product_id']),
                branch_id=str(r['branch_id']),
                quantity_on_hand=float(r['quantity_on_hand']),
                quantity_reserved=float(r['quantity_reserved']),
                updated_at=str(r['updated_at']),
            )
            for r in rows
        ]

    def adjust(
        self,
        product_id: str,
        branch_id: str,
        *,
        delta_on_hand: float,
        updated_at: str,
    ) -> InventoryBalance:
        cur = self.get_balance(product_id, branch_id)
        if cur is None:
            saved = InventoryBalance(
                id=_new_id(),
                product_id=product_id,
                branch_id=branch_id,
                quantity_on_hand=round(float(delta_on_hand), 4),
                quantity_reserved=0.0,
                updated_at=updated_at,
            )
            with self._db.connect() as conn:
                conn.execute(
                    'INSERT INTO inventory(id, product_id, branch_id, quantity_on_hand, '
                    'quantity_reserved, updated_at) VALUES(?,?,?,?,?,?)',
                    (
                        saved.id,
                        saved.product_id,
                        saved.branch_id,
                        saved.quantity_on_hand,
                        saved.quantity_reserved,
                        saved.updated_at,
                    ),
                )
                conn.commit()
            return saved
        saved = replace(
            cur,
            quantity_on_hand=round(float(cur.quantity_on_hand) + float(delta_on_hand), 4),
            updated_at=updated_at,
        )
        with self._db.connect() as conn:
            conn.execute(
                'UPDATE inventory SET quantity_on_hand = ?, updated_at = ? '
                'WHERE product_id = ? AND branch_id = ?',
                (saved.quantity_on_hand, saved.updated_at, product_id, branch_id),
            )
            conn.commit()
        return saved


class SqliteConfigRepository:
    def __init__(self, db: SqliteConnection) -> None:
        self._db = db

    def get_business(self) -> BusinessConfig | None:
        with self._db.connect() as conn:
            row = conn.execute('SELECT payload FROM business LIMIT 1').fetchone()
        return _business_from(json.loads(row['payload'])) if row else None

    def get_branches(self) -> list[Branch]:
        with self._db.connect() as conn:
            rows = conn.execute('SELECT payload FROM branch').fetchall()
        out: list[Branch] = []
        for r in rows:
            d = json.loads(r['payload'])
            out.append(
                Branch(
                    id=str(d['id']),
                    business_id=str(d['business_id']),
                    name=str(d['name']),
                    is_default=bool(d.get('is_default', False)),
                    address=_address(d.get('address')),
                )
            )
        return out

    def get_registers(self, *, branch_id: str | None = None) -> list[Register]:
        with self._db.connect() as conn:
            if branch_id:
                rows = conn.execute(
                    'SELECT payload FROM register WHERE branch_id = ?', (branch_id,)
                ).fetchall()
            else:
                rows = conn.execute('SELECT payload FROM register').fetchall()
        out: list[Register] = []
        for r in rows:
            d = json.loads(r['payload'])
            out.append(
                Register(
                    id=str(d['id']),
                    branch_id=str(d['branch_id']),
                    name=str(d['name']),
                    is_default=bool(d.get('is_default', False)),
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
        bid = business.id or _new_id()
        saved = replace(business, id=bid) if business.id != bid else business
        with self._db.connect() as conn:
            conn.execute('DELETE FROM business')
            conn.execute(
                'INSERT INTO business(id, payload) VALUES(?,?)',
                (saved.id, _dumps(saved)),
            )
            if branches is not None:
                conn.execute('DELETE FROM branch')
                for b in branches:
                    conn.execute(
                        'INSERT INTO branch(id, business_id, payload) VALUES(?,?,?)',
                        (b.id, b.business_id, _dumps(b)),
                    )
            if registers is not None:
                conn.execute('DELETE FROM register')
                for reg in registers:
                    conn.execute(
                        'INSERT INTO register(id, branch_id, payload) VALUES(?,?,?)',
                        (reg.id, reg.branch_id, _dumps(reg)),
                    )
            conn.commit()
        return saved


class SqlitePromotionRepository:
    def __init__(self, db: SqliteConnection) -> None:
        self._db = db

    def get(self, promotion_id: str) -> Promotion | None:
        with self._db.connect() as conn:
            row = conn.execute(
                'SELECT payload FROM promotion WHERE id = ?', (promotion_id,)
            ).fetchone()
        return _promo_from(json.loads(row['payload'])) if row else None

    def list_active(self, *, as_of: str | None = None, limit: int = 100) -> list[Promotion]:
        lim = max(1, min(int(limit), 500))
        with self._db.connect() as conn:
            rows = conn.execute(
                'SELECT payload FROM promotion WHERE active = 1 LIMIT ?', (lim,)
            ).fetchall()
        items = [_promo_from(json.loads(r['payload'])) for r in rows]
        if as_of:
            filtered: list[Promotion] = []
            for p in items:
                if p.valid_from and as_of < p.valid_from:
                    continue
                if p.valid_to and as_of > p.valid_to:
                    continue
                filtered.append(p)
            items = filtered
        return items

    def put(self, promotion: Promotion) -> Promotion:
        pid = promotion.id or _new_id()
        saved = replace(promotion, id=pid) if promotion.id != pid else promotion
        with self._db.connect() as conn:
            conn.execute(
                'INSERT INTO promotion(id, active, payload) VALUES(?,?,?) '
                'ON CONFLICT(id) DO UPDATE SET active=excluded.active, payload=excluded.payload',
                (saved.id, 1 if saved.active else 0, _dumps(saved)),
            )
            conn.commit()
        return saved


class SqliteDeviceRepository:
    def __init__(self, db: SqliteConnection) -> None:
        self._db = db

    def get(self, device_id: str) -> Device | None:
        with self._db.connect() as conn:
            row = conn.execute('SELECT payload FROM device WHERE id = ?', (device_id,)).fetchone()
        return _device_from(json.loads(row['payload'])) if row else None

    def list(self, *, active_only: bool = True, limit: int = 100) -> list[Device]:
        lim = max(1, min(int(limit), 500))
        sql = 'SELECT payload FROM device'
        args: list[Any] = []
        if active_only:
            sql += " WHERE status = 'active'"
        sql += ' LIMIT ?'
        args.append(lim)
        with self._db.connect() as conn:
            rows = conn.execute(sql, args).fetchall()
        return [_device_from(json.loads(r['payload'])) for r in rows]

    def upsert(self, device: Device) -> Device:
        did = device.id or _new_id()
        saved = replace(device, id=did) if device.id != did else device
        with self._db.connect() as conn:
            conn.execute(
                'INSERT INTO device(id, status, payload) VALUES(?,?,?) '
                'ON CONFLICT(id) DO UPDATE SET status=excluded.status, payload=excluded.payload',
                (saved.id, saved.status, _dumps(saved)),
            )
            conn.commit()
        return saved

    def heartbeat(
        self, device_id: str, *, last_seen_at: str, app_version: str | None = None
    ) -> Device | None:
        d = self.get(device_id)
        if d is None:
            return None
        return self.upsert(
            replace(
                d,
                last_seen_at=last_seen_at,
                app_version=app_version if app_version is not None else d.app_version,
            )
        )


class SqliteProviderBundle:
    def __init__(self, path: str | Path) -> None:
        self.db = SqliteConnection(path)
        self.products = SqliteProductRepository(self.db)
        self.customers = SqliteCustomerRepository(self.db)
        self.employees = SqliteEmployeeRepository(self.db)
        self.orders = SqliteOrderRepository(self.db)
        self.cash_shifts = SqliteCashShiftRepository(self.db)
        self.inventory = SqliteInventoryRepository(self.db)
        self.config = SqliteConfigRepository(self.db)
        self.promotions = SqlitePromotionRepository(self.db)
        self.devices = SqliteDeviceRepository(self.db)
