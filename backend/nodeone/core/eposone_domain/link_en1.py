"""Sprint 5 — Vincular con EasyNodeOne (Local → Plataforma). ADR-004.

Copy UI: «Vincular con EasyNodeOne» — nunca «migración».
Reanudable vía estado ``linking``; mapa ``local_id`` ↔ ``en1_id``.
No implementa OAuth ni cablea ``core/sync/`` (Sprint 7).
"""

from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass, field, replace
from datetime import datetime, timezone
from typing import Any, Literal

from nodeone.core.eposone_domain.first_start import (
    MODE_LOCAL,
    MODE_PLATFORM,
    FirstStartState,
)
from nodeone.core.eposone_domain.models import (
    Branch,
    BusinessConfig,
    Customer,
    Employee,
    InventoryBalance,
    Order,
    Product,
    Register,
)

LABEL_LINK_EN1 = 'Vincular con EasyNodeOne'

LinkPhase = Literal[
    'idle',
    'awaiting_login',
    'select_organization',
    'select_enterprise',
    'select_branch',
    'select_register',
    'transferring',
    'completed',
    'failed',
]

EnterpriseOption = Literal['create_en1', 'link_existing']
SkuConflictPolicy = Literal['merge', 'rename', 'supervisor']

ENTITY_BUSINESS = 'business'
ENTITY_BRANCH = 'branch'
ENTITY_REGISTER = 'register'
ENTITY_PRODUCT = 'product'
ENTITY_CUSTOMER = 'customer'
ENTITY_EMPLOYEE = 'employee'
ENTITY_ORDER = 'order'
ENTITY_INVENTORY = 'inventory'


def _utcnow() -> str:
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def _new_id() -> str:
    return str(uuid.uuid4())


@dataclass(frozen=True)
class IdMapping:
    entity_type: str
    local_id: str
    en1_id: str


@dataclass
class IdMappingTable:
    """Tabla de vínculo local_id ↔ en1_id por tipo de entidad."""

    rows: list[IdMapping] = field(default_factory=list)

    def put(self, entity_type: str, local_id: str, en1_id: str) -> None:
        self.rows = [
            r
            for r in self.rows
            if not (r.entity_type == entity_type and r.local_id == local_id)
        ]
        self.rows.append(IdMapping(entity_type=entity_type, local_id=local_id, en1_id=en1_id))

    def get_en1(self, entity_type: str, local_id: str) -> str | None:
        for r in self.rows:
            if r.entity_type == entity_type and r.local_id == local_id:
                return r.en1_id
        return None

    def to_list(self) -> list[dict[str, str]]:
        return [asdict(r) for r in self.rows]

    @classmethod
    def from_list(cls, items: list[dict[str, Any]] | None) -> IdMappingTable:
        table = cls()
        for raw in items or []:
            table.rows.append(
                IdMapping(
                    entity_type=str(raw['entity_type']),
                    local_id=str(raw['local_id']),
                    en1_id=str(raw['en1_id']),
                )
            )
        return table


@dataclass(frozen=True)
class LinkTransferCounts:
    products: int = 0
    customers: int = 0
    employees: int = 0
    orders: int = 0
    inventory: int = 0
    sku_merged: int = 0
    sku_renamed: int = 0

    def to_dict(self) -> dict[str, int]:
        return asdict(self)


@dataclass(frozen=True)
class LinkEn1State:
    """Estado del asistente — reanudable mientras phase != completed/idle tras fallo limpio."""

    phase: LinkPhase
    enabled: bool  # True solo si app está en Modo Local (antes de completar)
    organization_id: str | None = None
    access_granted: bool = False
    enterprise_option: EnterpriseOption | None = None
    en1_business_id: str | None = None
    branch_id: str | None = None
    register_id: str | None = None
    sku_policy: SkuConflictPolicy = 'merge'
    mappings: tuple[dict[str, str], ...] = ()
    transfer: dict[str, int] | None = None
    error: str | None = None
    updated_at: str | None = None
    completed_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def idle_for_local(cls) -> LinkEn1State:
        return cls(phase='idle', enabled=True, updated_at=_utcnow())

    @classmethod
    def disabled_not_local(cls) -> LinkEn1State:
        return cls(phase='idle', enabled=False, updated_at=_utcnow())

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> LinkEn1State:
        if not data:
            return cls.disabled_not_local()
        return cls(
            phase=str(data.get('phase') or 'idle'),  # type: ignore[arg-type]
            enabled=bool(data.get('enabled')),
            organization_id=data.get('organization_id'),
            access_granted=bool(data.get('access_granted')),
            enterprise_option=data.get('enterprise_option'),  # type: ignore[arg-type]
            en1_business_id=data.get('en1_business_id'),
            branch_id=data.get('branch_id'),
            register_id=data.get('register_id'),
            sku_policy=str(data.get('sku_policy') or 'merge'),  # type: ignore[arg-type]
            mappings=tuple(data.get('mappings') or ()),
            transfer=data.get('transfer'),
            error=data.get('error'),
            updated_at=data.get('updated_at'),
            completed_at=data.get('completed_at'),
        )


class LinkEn1Error(ValueError):
    pass


@dataclass(frozen=True)
class LinkEn1Result:
    link_state: LinkEn1State
    first_start_state: FirstStartState
    mappings: IdMappingTable
    transfer: LinkTransferCounts


def build_export_envelope(
    *,
    business: BusinessConfig | None,
    products: list[Product],
    customers: list[Customer],
    employees: list[Employee],
    orders: list[Order],
    inventory: list[InventoryBalance],
    branches: list[Branch],
    cash_shifts: list[Any] | None = None,
) -> dict[str, Any]:
    """Envelope ADR-004 / Sprint 2 para auditoría o transferencia."""
    return {
        'schema_version': 1,
        'exported_at': _utcnow(),
        'mode_at_export': 'local',
        'business': business.to_dict() if business else None,
        'branches': [asdict(b) for b in branches],
        'products': [p.to_dict() for p in products],
        'customers': [c.to_dict() for c in customers],
        'employees': [e.to_dict() for e in employees],
        'inventory_balances': [i.to_dict() for i in inventory],
        'orders': [o.to_dict() for o in orders],
        'cash_shifts': cash_shifts or [],
    }


class LinkEn1Assistant:
    """Asistente Vincular: Local provider → Platform (target) provider.

    ``local`` / ``target`` son bundles con config, products, customers, employees,
    orders, inventory (misma forma Memory/Sqlite/Api).
    """

    def __init__(
        self,
        *,
        local: Any,
        target: Any,
        get_first_start: Any,
        set_first_start: Any,
        get_link_state: Any,
        set_link_state: Any,
    ) -> None:
        self._local = local
        self._target = target
        self._get_fs = get_first_start
        self._set_fs = set_first_start
        self._get_link = get_link_state
        self._set_link = set_link_state

    @staticmethod
    def label() -> str:
        return LABEL_LINK_EN1

    def current_state(self) -> LinkEn1State:
        fs = self._get_fs()
        st = self._get_link()
        if fs.operating_mode == MODE_PLATFORM and st.phase == 'completed':
            return st
        if fs.operating_mode != MODE_LOCAL:
            return LinkEn1State.disabled_not_local()
        if not st.enabled and st.phase == 'idle':
            return LinkEn1State.idle_for_local()
        return st

    def is_available(self) -> bool:
        st = self.current_state()
        return bool(st.enabled) and self._get_fs().operating_mode == MODE_LOCAL

    def start(self) -> LinkEn1State:
        fs = self._get_fs()
        st = self._get_link()
        resumable = st.phase in (
            'awaiting_login',
            'select_organization',
            'select_enterprise',
            'select_branch',
            'select_register',
            'transferring',
            'failed',
        )
        if fs.operating_mode != MODE_LOCAL and not resumable:
            raise LinkEn1Error('link_only_available_in_local_mode')
        if st.phase == 'completed':
            raise LinkEn1Error('link_already_completed')
        st = LinkEn1State(
            phase='awaiting_login',
            enabled=True,
            updated_at=_utcnow(),
        )
        self._set_link(st)
        return st

    def resume(self) -> LinkEn1State:
        st = self._get_link()
        if st.phase in ('idle', 'completed'):
            raise LinkEn1Error('nothing_to_resume')
        if st.phase == 'failed':
            # Reanudar desde login
            st = replace(st, phase='awaiting_login', error=None, updated_at=_utcnow())
            self._set_link(st)
        return st

    def grant_access(self, *, access_granted: bool) -> LinkEn1State:
        st = self._require_phase('awaiting_login')
        if not access_granted:
            raise LinkEn1Error('en1_access_required')
        st = replace(
            st,
            access_granted=True,
            phase='select_organization',
            updated_at=_utcnow(),
        )
        self._set_link(st)
        return st

    def select_organization(self, organization_id: str) -> LinkEn1State:
        st = self._require_phase('select_organization')
        oid = (organization_id or '').strip()
        if not oid:
            raise LinkEn1Error('organization_id_required')
        st = replace(
            st,
            organization_id=oid,
            phase='select_enterprise',
            updated_at=_utcnow(),
        )
        self._set_link(st)
        return st

    def select_enterprise(
        self,
        option: EnterpriseOption,
        *,
        en1_business_id: str | None = None,
    ) -> LinkEn1State:
        st = self._require_phase('select_enterprise')
        if option not in ('create_en1', 'link_existing'):
            raise LinkEn1Error('invalid_enterprise_option')
        if option == 'link_existing' and not (en1_business_id or '').strip():
            raise LinkEn1Error('en1_business_id_required')
        local_biz = self._local.config.get_business()
        if option == 'create_en1':
            if local_biz is None:
                raise LinkEn1Error('local_business_required')
            created = self._target.config.upsert_config(
                BusinessConfig(
                    id=_new_id(),
                    name=local_biz.name,
                    currency=local_biz.currency,
                    created_at=_utcnow(),
                    legal_name=local_biz.legal_name,
                    tax_id=local_biz.tax_id,
                    country_code=local_biz.country_code,
                    timezone=local_biz.timezone,
                    address=local_biz.address,
                    tax_rates=local_biz.tax_rates,
                ),
                branches=[],
                registers=[],
            )
            bid = created.id
        else:
            bid = (en1_business_id or '').strip()
            existing = self._target.config.get_business()
            if existing is None or existing.id != bid:
                name = local_biz.name if local_biz else f'Organización {st.organization_id}'
                currency = local_biz.currency if local_biz else 'USD'
                self._target.config.upsert_config(
                    BusinessConfig(
                        id=bid,
                        name=name,
                        currency=currency,
                        created_at=_utcnow(),
                    ),
                    branches=[],
                    registers=[],
                )
        st = replace(
            st,
            enterprise_option=option,
            en1_business_id=bid,
            phase='select_branch',
            updated_at=_utcnow(),
        )
        self._set_link(st)
        return st

    def select_branch(self, *, branch_id: str | None = None, branch_name: str | None = None) -> LinkEn1State:
        st = self._require_phase('select_branch')
        local_branches = self._local.config.get_branches()
        biz_id = st.en1_business_id or ''
        if branch_id and any(b.id == branch_id for b in self._target.config.get_branches()):
            chosen_id = branch_id
        else:
            # Crear branch en target desde local default o nombre
            src = None
            if branch_id:
                src = next((b for b in local_branches if b.id == branch_id), None)
            if src is None and local_branches:
                src = next((b for b in local_branches if b.is_default), local_branches[0])
            new_id = _new_id()
            branch = Branch(
                id=new_id,
                business_id=biz_id,
                name=(branch_name or (src.name if src else 'Sucursal')).strip() or 'Sucursal',
                is_default=True,
                address=src.address if src else None,
            )
            biz = self._target.config.get_business()
            if biz is None:
                raise LinkEn1Error('en1_business_missing')
            regs = self._target.config.get_registers()
            self._target.config.upsert_config(biz, branches=[branch], registers=regs)
            if src is not None:
                # mapping se completa en transfer; guardamos id elegido
                pass
            chosen_id = new_id
        st = replace(st, branch_id=chosen_id, phase='select_register', updated_at=_utcnow())
        self._set_link(st)
        return st

    def select_register(
        self, *, register_id: str | None = None, register_name: str | None = None
    ) -> LinkEn1State:
        st = self._require_phase('select_register')
        branch_id = st.branch_id or ''
        local_regs = self._local.config.get_registers()
        target_regs = self._target.config.get_registers(branch_id=branch_id)
        if register_id and any(r.id == register_id for r in target_regs):
            chosen_id = register_id
        else:
            src = None
            if register_id:
                src = next((r for r in local_regs if r.id == register_id), None)
            if src is None and local_regs:
                src = next((r for r in local_regs if r.is_default), local_regs[0])
            new_id = _new_id()
            reg = Register(
                id=new_id,
                branch_id=branch_id,
                name=(register_name or (src.name if src else 'Caja 1')).strip() or 'Caja 1',
                is_default=True,
            )
            biz = self._target.config.get_business()
            branches = self._target.config.get_branches()
            if biz is None:
                raise LinkEn1Error('en1_business_missing')
            self._target.config.upsert_config(
                biz, branches=branches, registers=list(target_regs) + [reg]
            )
            chosen_id = new_id
        st = replace(st, register_id=chosen_id, phase='transferring', updated_at=_utcnow())
        self._set_link(st)
        return st

    def run_transfer(self) -> LinkEn1Result:
        st = self._require_phase('transferring')
        if not st.organization_id or not st.en1_business_id or not st.branch_id:
            raise LinkEn1Error('link_prerequisites_missing')

        mappings = IdMappingTable.from_list(list(st.mappings))
        local_biz = self._local.config.get_business()
        if local_biz is not None:
            mappings.put(ENTITY_BUSINESS, local_biz.id, st.en1_business_id)

        # Branches / registers
        for b in self._local.config.get_branches():
            if b.is_default or b.id == (self._get_fs().branch_id or ''):
                mappings.put(ENTITY_BRANCH, b.id, st.branch_id or '')
        for r in self._local.config.get_registers():
            if r.is_default or r.id == (self._get_fs().register_id or ''):
                mappings.put(ENTITY_REGISTER, r.id, st.register_id or '')

        sku_merged = 0
        sku_renamed = 0
        products_n = 0
        for p in self._local.products.list(active_only=False, limit=1000):
            remote_id, merged, renamed = self._upsert_product(p, mappings, st.sku_policy)
            mappings.put(ENTITY_PRODUCT, p.id, remote_id)
            products_n += 1
            sku_merged += merged
            sku_renamed += renamed

        customers_n = 0
        for c in self._local.customers.list(active_only=False, limit=1000):
            remote = self._upsert_customer(c, mappings)
            mappings.put(ENTITY_CUSTOMER, c.id, remote.id)
            customers_n += 1

        employees_n = 0
        for e in self._local.employees.list(active_only=False, limit=1000):
            remote = self._upsert_employee(e, mappings)
            mappings.put(ENTITY_EMPLOYEE, e.id, remote.id)
            employees_n += 1

        orders_n = 0
        for o in self._local.orders.list(limit=500):
            remapped = self._remap_order(o, mappings, st)
            created = self._target.orders.create(remapped, idempotency_key=f'link:{o.id}')
            mappings.put(ENTITY_ORDER, o.id, created.id)
            orders_n += 1

        inventory_n = 0
        # Memory/Sqlite inventory: iterate store keys if available
        inv_items = self._list_local_inventory()
        for bal in inv_items:
            en1_product = mappings.get_en1(ENTITY_PRODUCT, bal.product_id) or bal.product_id
            en1_branch = mappings.get_en1(ENTITY_BRANCH, bal.branch_id) or st.branch_id or bal.branch_id
            # Reset then adjust to target qty
            existing = self._target.inventory.get_balance(en1_product, en1_branch)
            delta = bal.quantity_on_hand - (existing.quantity_on_hand if existing else 0.0)
            if abs(delta) > 1e-9:
                new_bal = self._target.inventory.adjust(
                    en1_product,
                    en1_branch,
                    delta_on_hand=delta,
                    updated_at=_utcnow(),
                )
            else:
                new_bal = existing or bal
            mappings.put(ENTITY_INVENTORY, bal.id, new_bal.id if new_bal else bal.id)
            inventory_n += 1

        counts = LinkTransferCounts(
            products=products_n,
            customers=customers_n,
            employees=employees_n,
            orders=orders_n,
            inventory=inventory_n,
            sku_merged=sku_merged,
            sku_renamed=sku_renamed,
        )

        now = _utcnow()
        link_done = replace(
            st,
            phase='completed',
            enabled=False,
            mappings=tuple(mappings.to_list()),
            transfer=counts.to_dict(),
            error=None,
            updated_at=now,
            completed_at=now,
        )
        self._set_link(link_done)

        fs = self._get_fs()
        fs_plat = FirstStartState(
            completed=True,
            operating_mode=MODE_PLATFORM,
            path=fs.path,
            business_id=st.en1_business_id,
            branch_id=st.branch_id,
            register_id=st.register_id,
            admin_employee_id=fs.admin_employee_id,
            en1_organization_id=st.organization_id,
            has_en1_credentials=True,
            completed_at=now,
        )
        self._set_fs(fs_plat)

        return LinkEn1Result(
            link_state=link_done,
            first_start_state=fs_plat,
            mappings=mappings,
            transfer=counts,
        )

    def mark_failed(self, error: str) -> LinkEn1State:
        st = self._get_link()
        st = replace(
            st,
            phase='failed',
            error=(error or 'link_failed')[:500],
            updated_at=_utcnow(),
        )
        self._set_link(st)
        return st

    def export_local_envelope(self) -> dict[str, Any]:
        return build_export_envelope(
            business=self._local.config.get_business(),
            products=self._local.products.list(active_only=False, limit=1000),
            customers=self._local.customers.list(active_only=False, limit=1000),
            employees=self._local.employees.list(active_only=False, limit=1000),
            orders=self._local.orders.list(limit=500),
            inventory=self._list_local_inventory(),
            branches=self._local.config.get_branches(),
        )

    # --- internals ---

    def _require_phase(self, expected: LinkPhase) -> LinkEn1State:
        st = self._get_link()
        if st.phase != expected:
            raise LinkEn1Error(f'invalid_phase:{st.phase}:expected:{expected}')
        return st

    def _list_local_inventory(self) -> list[InventoryBalance]:
        store = getattr(self._local, 'store', None)
        if store is not None and hasattr(store, 'inventory'):
            return list(store.inventory.values())
        # Sqlite: no direct list-all in port — best-effort via alerts with high threshold
        try:
            return self._local.inventory.list_alerts(below=1e12, limit=500)
        except Exception:
            return []

    def _upsert_product(
        self, product: Product, mappings: IdMappingTable, policy: SkuConflictPolicy
    ) -> tuple[str, int, int]:
        merged = 0
        renamed = 0
        existing = None
        if product.sku:
            for rem in self._target.products.list(active_only=False, limit=1000):
                if rem.sku and rem.sku == product.sku:
                    existing = rem
                    break
        if existing is not None:
            if policy == 'supervisor':
                raise LinkEn1Error(f'sku_conflict_needs_supervisor:{product.sku}')
            if policy == 'merge':
                updated = replace(
                    existing,
                    name=product.name,
                    unit_price=product.unit_price,
                    currency=product.currency,
                    product_type=product.product_type,
                    active=product.active,
                    track_stock=product.track_stock,
                    description=product.description,
                    updated_at=_utcnow(),
                )
                saved = self._target.products.upsert(updated)
                return saved.id, 1, 0
            # rename
            new_sku = f"{product.sku}-local"
            renamed = 1
            product = replace(product, id=_new_id(), sku=new_sku)
        else:
            product = replace(product, id=_new_id())
        saved = self._target.products.upsert(product)
        return saved.id, merged, renamed

    def _upsert_customer(self, customer: Customer, mappings: IdMappingTable) -> Customer:
        _ = mappings
        if customer.email:
            for rem in self._target.customers.list(active_only=False, limit=1000):
                if rem.email and rem.email.lower() == customer.email.lower():
                    return self._target.customers.upsert(
                        replace(customer, id=rem.id, updated_at=_utcnow())
                    )
        return self._target.customers.upsert(replace(customer, id=_new_id()))

    def _upsert_employee(self, employee: Employee, mappings: IdMappingTable) -> Employee:
        _ = mappings
        if employee.email:
            for rem in self._target.employees.list(active_only=False, limit=1000):
                if rem.email and rem.email.lower() == employee.email.lower():
                    return self._target.employees.upsert(replace(employee, id=rem.id))
        return self._target.employees.upsert(replace(employee, id=_new_id()))

    def _remap_order(self, order: Order, mappings: IdMappingTable, st: LinkEn1State) -> Order:
        from nodeone.core.eposone_domain.models import OrderLine

        business_id = st.en1_business_id or order.business_id
        branch_id = mappings.get_en1(ENTITY_BRANCH, order.branch_id) or st.branch_id or order.branch_id
        register_id = (
            mappings.get_en1(ENTITY_REGISTER, order.register_id or '')
            or st.register_id
            or order.register_id
        )
        customer_id = (
            mappings.get_en1(ENTITY_CUSTOMER, order.customer_id)
            if order.customer_id
            else None
        )
        lines = tuple(
            OrderLine(
                id=_new_id(),
                description=ln.description,
                quantity=ln.quantity,
                unit_price=ln.unit_price,
                line_total=ln.line_total,
                line_status=ln.line_status,
                product_id=(
                    mappings.get_en1(ENTITY_PRODUCT, ln.product_id) if ln.product_id else None
                ),
                tax_rate_id=ln.tax_rate_id,
            )
            for ln in order.lines
        )
        return replace(
            order,
            id=_new_id(),
            business_id=business_id,
            branch_id=branch_id,
            register_id=register_id,
            customer_id=customer_id,
            lines=lines,
            payments=(),
            version=1,
            idempotency_key=f'link:{order.id}',
        )


def assistant_from_memory_bundles(
    local_bundle: Any,
    target_bundle: Any,
    *,
    first_start_state: FirstStartState | None = None,
) -> LinkEn1Assistant:
    """Factory para tests / sketch: dos Memory bundles + estado in-store."""
    from nodeone.core.eposone_domain.first_start import attach_first_start_state_store

    attach_first_start_state_store(local_bundle.store)
    if first_start_state is not None:
        local_bundle.store.first_start = first_start_state
    elif not hasattr(local_bundle.store, 'first_start') or local_bundle.store.first_start is None:
        local_bundle.store.first_start = FirstStartState.uninitialized()

    if not hasattr(local_bundle.store, 'link_en1'):
        local_bundle.store.link_en1 = LinkEn1State.idle_for_local()

    def get_fs() -> FirstStartState:
        return local_bundle.store.first_start

    def set_fs(state: FirstStartState) -> None:
        local_bundle.store.first_start = state

    def get_link() -> LinkEn1State:
        raw = getattr(local_bundle.store, 'link_en1', None)
        if isinstance(raw, LinkEn1State):
            return raw
        return LinkEn1State.from_dict(raw if isinstance(raw, dict) else None)

    def set_link(state: LinkEn1State) -> None:
        local_bundle.store.link_en1 = state

    return LinkEn1Assistant(
        local=local_bundle,
        target=target_bundle,
        get_first_start=get_fs,
        set_first_start=set_fs,
        get_link_state=get_link,
        set_link_state=set_link,
    )
