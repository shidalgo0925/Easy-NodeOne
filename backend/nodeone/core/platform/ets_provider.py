"""Compañía productiva ETS en EN1 (proveedor comercial ADR-031 §4.1)."""

from __future__ import annotations

import os


def ets_provider_organization_id() -> int:
    """Org EN1 donde viven los clientes comerciales (default id=1)."""
    raw = (os.environ.get('NODEONE_ETS_PROVIDER_ORG_ID') or '1').strip()
    try:
        oid = int(raw)
    except (TypeError, ValueError):
        oid = 1
    return oid if oid > 0 else 1


def is_legacy_standalone_commercial_shell(org) -> bool:
    """Cascarones P0 (Cliente EPosOne — … / ets-cli-*) a ocultar del admin de Orgs."""
    if org is None:
        return False
    name = (getattr(org, 'name', None) or '').strip()
    sub = (getattr(org, 'subdomain', None) or '').strip().lower()
    if name.startswith('Cliente EPosOne'):
        return True
    if sub.startswith('ets-cli-'):
        return True
    return False
