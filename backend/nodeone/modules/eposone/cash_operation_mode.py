"""ADR-036 — modos de operación de caja (SIMPLE | CHAIN_OF_CUSTODY)."""

from __future__ import annotations

CASH_MODE_SIMPLE = 'SIMPLE'
CASH_MODE_CHAIN_OF_CUSTODY = 'CHAIN_OF_CUSTODY'
_ALLOWED = frozenset({CASH_MODE_SIMPLE, CASH_MODE_CHAIN_OF_CUSTODY})


def normalize_cash_operation_mode(raw: str | None) -> str:
    mode = str(raw or CASH_MODE_SIMPLE).strip().upper() or CASH_MODE_SIMPLE
    if mode not in _ALLOWED:
        return CASH_MODE_SIMPLE
    return mode


def resolve_cash_operation_mode(organization_id: int) -> str:
    """Modo efectivo de la org (default SIMPLE). Override por caja = fase posterior."""
    try:
        from nodeone.modules.eposone.settings_service import EposoneSettingsService

        dto = EposoneSettingsService.get_settings(int(organization_id))
        return normalize_cash_operation_mode(getattr(dto, 'cash_operation_mode', None))
    except Exception:
        return CASH_MODE_SIMPLE


def is_chain_of_custody(organization_id: int) -> bool:
    return resolve_cash_operation_mode(organization_id) == CASH_MODE_CHAIN_OF_CUSTODY
