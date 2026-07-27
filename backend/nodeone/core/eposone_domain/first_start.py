"""Sprint 4 — Primer inicio EPosOne (Crear negocio | Conectar EasyNodeOne).

Capa de casos de uso sobre Config/Employee repositories.
No conoce Flask, Android ni el motor sync. Copy: nunca «migración».
"""

from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Literal

from nodeone.core.eposone_domain.models import Branch, BusinessConfig, Employee, Register

OperatingMode = Literal['uninitialized', 'local', 'platform']
FirstStartPath = Literal['create_business', 'connect_en1']

PATH_CREATE_BUSINESS: FirstStartPath = 'create_business'
PATH_CONNECT_EN1: FirstStartPath = 'connect_en1'

MODE_UNINITIALIZED: OperatingMode = 'uninitialized'
MODE_LOCAL: OperatingMode = 'local'
MODE_PLATFORM: OperatingMode = 'platform'

# Copy congelado ADR-003 (UI strings)
LABEL_CREATE_BUSINESS = 'Crear un nuevo negocio'
LABEL_CONNECT_EN1 = 'Conectar con EasyNodeOne'


def _utcnow() -> str:
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def _new_id() -> str:
    return str(uuid.uuid4())


@dataclass(frozen=True)
class FirstStartChoice:
    """Opción del wizard de primer inicio."""

    path: FirstStartPath
    label: str
    description: str


FIRST_START_CHOICES: tuple[FirstStartChoice, ...] = (
    FirstStartChoice(
        path=PATH_CREATE_BUSINESS,
        label=LABEL_CREATE_BUSINESS,
        description='Operá en Modo Local: empresa, sucursal, caja y admin en este dispositivo.',
    ),
    FirstStartChoice(
        path=PATH_CONNECT_EN1,
        label=LABEL_CONNECT_EN1,
        description='Modo Plataforma: iniciá sesión en EasyNodeOne y descargá la configuración.',
    ),
)


@dataclass(frozen=True)
class FirstStartState:
    """Estado persistido del bootstrap POS (Local o Plataforma)."""

    completed: bool
    operating_mode: OperatingMode
    path: FirstStartPath | None = None
    business_id: str | None = None
    branch_id: str | None = None
    register_id: str | None = None
    admin_employee_id: str | None = None
    en1_organization_id: str | None = None
    has_en1_credentials: bool = False
    completed_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def uninitialized(cls) -> FirstStartState:
        return cls(completed=False, operating_mode=MODE_UNINITIALIZED)

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> FirstStartState:
        if not data:
            return cls.uninitialized()
        return cls(
            completed=bool(data.get('completed')),
            operating_mode=str(data.get('operating_mode') or MODE_UNINITIALIZED),  # type: ignore[arg-type]
            path=data.get('path'),  # type: ignore[arg-type]
            business_id=data.get('business_id'),
            branch_id=data.get('branch_id'),
            register_id=data.get('register_id'),
            admin_employee_id=data.get('admin_employee_id'),
            en1_organization_id=data.get('en1_organization_id'),
            has_en1_credentials=bool(data.get('has_en1_credentials')),
            completed_at=data.get('completed_at'),
        )


@dataclass(frozen=True)
class CreateBusinessInput:
    business_name: str
    currency: str = 'USD'
    legal_name: str | None = None
    tax_id: str | None = None
    country_code: str | None = None
    timezone: str | None = None
    branch_name: str = 'Sucursal principal'
    register_name: str = 'Caja 1'
    admin_display_name: str = 'Administrador'
    admin_email: str | None = None
    admin_has_pin: bool = True


@dataclass(frozen=True)
class ConnectEn1Input:
    """Conectar con EasyNodeOne — tokens reales van fuera; aquí solo flags + ids."""

    organization_id: str
    access_granted: bool
    business_name: str | None = None
    currency: str = 'USD'
    branch_id: str | None = None
    branch_name: str = 'Sucursal'
    register_id: str | None = None
    register_name: str = 'Caja 1'
    admin_display_name: str = 'Admin EN1'
    admin_email: str | None = None


@dataclass(frozen=True)
class FirstStartResult:
    state: FirstStartState
    business: BusinessConfig
    branch: Branch
    register: Register
    admin: Employee


class FirstStartError(ValueError):
    """Error de validación / flujo del wizard."""


class FirstStartWizard:
    """Orquesta el primer inicio sobre un bundle de providers (Memory / SQLite / API).

    El bundle debe exponer ``config``, ``employees`` y opcionalmente
    ``get_first_start_state`` / ``set_first_start_state`` (inyectados o vía mixin).
    """

    def __init__(
        self,
        *,
        config,
        employees,
        get_state: Any,
        set_state: Any,
    ) -> None:
        self._config = config
        self._employees = employees
        self._get_state = get_state
        self._set_state = set_state

    @staticmethod
    def choices() -> tuple[FirstStartChoice, ...]:
        return FIRST_START_CHOICES

    def current_state(self) -> FirstStartState:
        return self._get_state()

    def needs_first_start(self) -> bool:
        """True hasta que el wizard complete (estado ``completed``)."""
        return not self.current_state().completed

    def create_local_business(self, data: CreateBusinessInput) -> FirstStartResult:
        """Camino: Crear un nuevo negocio → Modo Local."""
        if not self.needs_first_start():
            raise FirstStartError('first_start_already_completed')
        name = (data.business_name or '').strip()
        if not name:
            raise FirstStartError('business_name_required')
        currency = (data.currency or 'USD').strip().upper() or 'USD'
        if len(currency) != 3:
            raise FirstStartError('invalid_currency')

        now = _utcnow()
        business_id = _new_id()
        branch_id = _new_id()
        register_id = _new_id()

        business = BusinessConfig(
            id=business_id,
            name=name,
            currency=currency,
            created_at=now,
            legal_name=(data.legal_name or '').strip() or None,
            tax_id=(data.tax_id or '').strip() or None,
            country_code=(data.country_code or '').strip().upper() or None,
            timezone=(data.timezone or '').strip() or None,
        )
        branch = Branch(
            id=branch_id,
            business_id=business_id,
            name=(data.branch_name or 'Sucursal principal').strip() or 'Sucursal principal',
            is_default=True,
        )
        register = Register(
            id=register_id,
            branch_id=branch_id,
            name=(data.register_name or 'Caja 1').strip() or 'Caja 1',
            is_default=True,
        )
        self._config.upsert_config(business, branches=[branch], registers=[register])

        admin = self._employees.upsert(
            Employee(
                id=_new_id(),
                display_name=(data.admin_display_name or 'Administrador').strip() or 'Administrador',
                has_pin=bool(data.admin_has_pin),
                operational_roles=('manager', 'cashier'),
                active=True,
                created_at=now,
                email=(data.admin_email or '').strip() or None,
            )
        )

        state = FirstStartState(
            completed=True,
            operating_mode=MODE_LOCAL,
            path=PATH_CREATE_BUSINESS,
            business_id=business.id,
            branch_id=branch.id,
            register_id=register.id,
            admin_employee_id=admin.id,
            en1_organization_id=None,
            has_en1_credentials=False,
            completed_at=now,
        )
        self._set_state(state)
        return FirstStartResult(
            state=state, business=business, branch=branch, register=register, admin=admin
        )

    def connect_en1(self, data: ConnectEn1Input) -> FirstStartResult:
        """Camino: Conectar con EasyNodeOne → Modo Plataforma (bootstrap config).

        No implementa OAuth: el cliente entrega ``access_granted`` tras login externo.
        Persiste BusinessConfig / sucursal / caja seleccionados vía ConfigRepository.
        """
        if not self.needs_first_start():
            raise FirstStartError('first_start_already_completed')
        org_id = (data.organization_id or '').strip()
        if not org_id:
            raise FirstStartError('organization_id_required')
        if not data.access_granted:
            raise FirstStartError('en1_access_required')

        now = _utcnow()
        currency = (data.currency or 'USD').strip().upper() or 'USD'
        prefer_branch = (data.branch_id or '').strip() or None
        prefer_register = (data.register_id or '').strip() or None

        remote = self._config.get_business()
        if remote is not None:
            business = remote
            branches = list(self._config.get_branches())
            registers = list(self._config.get_registers())
        else:
            business = None
            branches = []
            registers = []

        if business is None:
            business = BusinessConfig(
                id=org_id,
                name=(data.business_name or '').strip() or f'Organización {org_id}',
                currency=currency,
                created_at=now,
            )

        if prefer_branch and any(b.id == prefer_branch for b in branches):
            branch = next(b for b in branches if b.id == prefer_branch)
        elif branches:
            branch = branches[0]
        else:
            branch = Branch(
                id=prefer_branch or _new_id(),
                business_id=business.id,
                name=(data.branch_name or 'Sucursal').strip() or 'Sucursal',
                is_default=True,
            )
            branches = [branch]

        branch_registers = [r for r in registers if r.branch_id == branch.id] or list(registers)
        if prefer_register and any(r.id == prefer_register for r in branch_registers):
            register = next(r for r in branch_registers if r.id == prefer_register)
        elif branch_registers:
            register = branch_registers[0]
        else:
            register = Register(
                id=prefer_register or _new_id(),
                branch_id=branch.id,
                name=(data.register_name or 'Caja 1').strip() or 'Caja 1',
                is_default=True,
            )
            registers = [register]

        self._config.upsert_config(business, branches=branches, registers=registers)

        business = self._config.get_business() or business
        branches = self._config.get_branches() or branches
        registers = self._config.get_registers() or registers
        branch = next((b for b in branches if b.id == branch.id), branches[0])
        register = next((r for r in registers if r.id == register.id), registers[0])

        admin = self._employees.upsert(
            Employee(
                id=_new_id(),
                display_name=(data.admin_display_name or 'Admin EN1').strip() or 'Admin EN1',
                has_pin=False,
                operational_roles=('manager',),
                active=True,
                created_at=now,
                email=(data.admin_email or '').strip() or None,
            )
        )

        state = FirstStartState(
            completed=True,
            operating_mode=MODE_PLATFORM,
            path=PATH_CONNECT_EN1,
            business_id=business.id,
            branch_id=branch.id,
            register_id=register.id,
            admin_employee_id=admin.id,
            en1_organization_id=org_id,
            has_en1_credentials=True,
            completed_at=now,
        )
        self._set_state(state)
        return FirstStartResult(
            state=state, business=business, branch=branch, register=register, admin=admin
        )


def attach_first_start_state_store(store: Any) -> None:
    """Asegura atributos de bootstrap en MemoryStore (idempotente)."""
    if not hasattr(store, 'first_start'):
        store.first_start = FirstStartState.uninitialized()


def wizard_from_memory_bundle(bundle: Any) -> FirstStartWizard:
    attach_first_start_state_store(bundle.store)

    def get_state() -> FirstStartState:
        raw = getattr(bundle.store, 'first_start', None)
        if isinstance(raw, FirstStartState):
            return raw
        return FirstStartState.uninitialized()

    def set_state(state: FirstStartState) -> None:
        bundle.store.first_start = state

    return FirstStartWizard(
        config=bundle.config,
        employees=bundle.employees,
        get_state=get_state,
        set_state=set_state,
    )


def wizard_from_sqlite_bundle(bundle: Any) -> FirstStartWizard:
    import json

    db = bundle.db

    def _ensure_table(conn) -> None:
        conn.execute(
            'CREATE TABLE IF NOT EXISTS app_bootstrap ('
            'id INTEGER PRIMARY KEY CHECK (id = 1), '
            'payload TEXT NOT NULL)'
        )

    def get_state() -> FirstStartState:
        with db.connect() as conn:
            _ensure_table(conn)
            row = conn.execute('SELECT payload FROM app_bootstrap WHERE id = 1').fetchone()
            conn.commit()
        if row is None:
            return FirstStartState.uninitialized()
        return FirstStartState.from_dict(json.loads(row['payload']))

    def set_state(state: FirstStartState) -> None:
        payload = json.dumps(state.to_dict(), ensure_ascii=False)
        with db.connect() as conn:
            _ensure_table(conn)
            conn.execute(
                'INSERT INTO app_bootstrap(id, payload) VALUES(1, ?) '
                'ON CONFLICT(id) DO UPDATE SET payload = excluded.payload',
                (payload,),
            )
            conn.commit()

    return FirstStartWizard(
        config=bundle.config,
        employees=bundle.employees,
        get_state=get_state,
        set_state=set_state,
    )


def wizard_from_api_bundle(bundle: Any, *, state_holder: dict[str, Any] | None = None) -> FirstStartWizard:
    """Plataforma: el estado de bootstrap vive en holder in-process (cliente) o SQLite paralelo.

    ``ApiConfigRepository.upsert_config`` es lectura-dominante; el camino connect_en1
    usa get_business remoto y guarda selección en ``state_holder``.
    """
    holder = state_holder if state_holder is not None else {}

    def get_state() -> FirstStartState:
        return FirstStartState.from_dict(holder.get('first_start'))

    def set_state(state: FirstStartState) -> None:
        holder['first_start'] = state.to_dict()

    return FirstStartWizard(
        config=bundle.config,
        employees=bundle.employees,
        get_state=get_state,
        set_state=set_state,
    )
