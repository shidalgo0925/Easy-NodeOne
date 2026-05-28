"""Configuración PAC por organización."""

from __future__ import annotations

import os
from typing import Optional

from nodeone.core.db import db
from models.efactura import ElectronicInvoiceProviderConfig

PROVIDER_EFACTURAPTY = 'efacturapty'


def get_or_create_provider_config(organization_id: int) -> ElectronicInvoiceProviderConfig:
    row = ElectronicInvoiceProviderConfig.query.filter_by(
        organization_id=int(organization_id),
        provider=PROVIDER_EFACTURAPTY,
    ).first()
    if row is None:
        row = ElectronicInvoiceProviderConfig(
            organization_id=int(organization_id),
            provider=PROVIDER_EFACTURAPTY,
            api_base_url='https://api.efacturapty.com',
            environment='sandbox',
            default_pos='001',
            enabled=False,
        )
        db.session.add(row)
        db.session.flush()
    return row


def token_tail_display(stored: str | None) -> str:
    if not stored:
        return ''
    s = stored.strip()
    if len(s) <= 4:
        return '****'
    return '*' * 12 + s[-4:]


def resolve_api_token(config: ElectronicInvoiceProviderConfig) -> str:
    """Token de org; en dev puede venir de EFACTURA_API_TOKEN si la fila está vacía."""
    raw = (config.api_token_encrypted or '').strip()
    if raw:
        return raw
    return (os.environ.get('EFACTURA_API_TOKEN') or '').strip()


def config_ready(config: ElectronicInvoiceProviderConfig) -> bool:
    return bool(config.enabled and resolve_api_token(config))
