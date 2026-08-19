"""ADR-EN1-EP1 — ciclo operativo org: PROVISIONING → TEST → OPERATIONAL."""

from __future__ import annotations

OPS_PROVISIONING = 'PROVISIONING'
OPS_TEST = 'TEST'
OPS_OPERATIONAL = 'OPERATIONAL'
OPS_LIFECYCLES = frozenset({OPS_PROVISIONING, OPS_TEST, OPS_OPERATIONAL})

MONEY_HANDOFF_SIMPLE = 'SIMPLE'
MONEY_HANDOFF_CHAIN = 'CHAIN_OF_CUSTODY'
MONEY_HANDOFF_MODES = frozenset({MONEY_HANDOFF_SIMPLE, MONEY_HANDOFF_CHAIN})

HANDOFF_PENDING = 'PENDING_HANDOFF'
HANDOFF_CONFIRMED = 'CONFIRMED_IN_CASH_REGISTER'
HANDOFF_REVERSED = 'REVERSED'
HANDOFF_STATUSES = frozenset({HANDOFF_PENDING, HANDOFF_CONFIRMED, HANDOFF_REVERSED})

CLOSE_TEST_PHRASE = 'PREPARAR OPERACION REAL'
EVENT_TEST_PERIOD_CLOSED = 'TEST_PERIOD_CLOSED'


def normalize_ops_lifecycle(raw: str | None) -> str:
    val = str(raw or OPS_TEST).strip().upper() or OPS_TEST
    return val if val in OPS_LIFECYCLES else OPS_TEST


def normalize_money_handoff_mode(raw: str | None) -> str:
    val = str(raw or MONEY_HANDOFF_SIMPLE).strip().upper() or MONEY_HANDOFF_SIMPLE
    return val if val in MONEY_HANDOFF_MODES else MONEY_HANDOFF_SIMPLE


def is_test_lifecycle(organization_id: int) -> bool:
    return resolve_ops_lifecycle(organization_id) == OPS_TEST


def resolve_ops_lifecycle(organization_id: int) -> str:
    try:
        from nodeone.modules.eposone.settings_service import EposoneSettingsService

        dto = EposoneSettingsService.get_settings(int(organization_id))
        return normalize_ops_lifecycle(getattr(dto, 'operational_lifecycle', None))
    except Exception:
        return OPS_TEST


def resolve_money_handoff_mode(organization_id: int) -> str:
    try:
        from nodeone.modules.eposone.settings_service import EposoneSettingsService

        dto = EposoneSettingsService.get_settings(int(organization_id))
        return normalize_money_handoff_mode(getattr(dto, 'money_handoff_mode', None))
    except Exception:
        return MONEY_HANDOFF_SIMPLE


def resolve_test_session_id(organization_id: int) -> str | None:
    try:
        from nodeone.modules.eposone.settings_service import EposoneSettingsService

        dto = EposoneSettingsService.get_settings(int(organization_id))
        raw = (getattr(dto, 'test_session_id', None) or '').strip()
        return raw or None
    except Exception:
        return None


def is_pre_operational(organization_id: int) -> bool:
    return resolve_ops_lifecycle(organization_id) != OPS_OPERATIONAL


def ensure_test_session_id(organization_id: int) -> str | None:
    """Mint persistente si el ciclo no es OPERATIONAL y aún no hay sesión."""
    if not is_pre_operational(int(organization_id)):
        return None
    existing = resolve_test_session_id(int(organization_id))
    if existing:
        return existing
    import uuid

    minted = f'TEST-{uuid.uuid4().hex[:16]}'
    from nodeone.modules.eposone.settings_service import EposoneSettingsService

    EposoneSettingsService.update_settings(int(organization_id), test_session_id=minted)
    return minted


def stamp_test_fields(row, organization_id: int) -> None:
    """Marca entidades transaccionales mientras PROVISIONING/TEST."""
    if not hasattr(row, 'is_test'):
        return
    if not is_pre_operational(int(organization_id)):
        return
    row.is_test = True
    if hasattr(row, 'test_session_id'):
        row.test_session_id = ensure_test_session_id(int(organization_id))


def catalog_sync_status(status: str | None) -> str:
    """Contrato EP1: ACTIVE | INACTIVE (baja comercial, no DELETE)."""
    st = (status or 'active').strip().lower()
    return 'ACTIVE' if st == 'active' else 'INACTIVE'
