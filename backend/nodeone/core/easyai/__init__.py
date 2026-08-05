"""EasyAI Core — Connector SDK (interfaces only).

EN1 exposes business context to EasyAI through Domain Connectors.
This package defines contracts. No LLM, no prompts, no SQL, no ORM leakage.

Runtime adapters that call existing EN1 services are out of scope for this
module until a later GO (wiring phase).
"""

from __future__ import annotations

from nodeone.core.easyai.contracts import (
    ConnectorRequest,
    ContextSlice,
    DomainConnector,
    EventEnvelope,
    EventTypeDescriptor,
    ToolCallResult,
    ToolDescriptor,
    ToolInvocation,
)
from nodeone.core.easyai.registry import ConnectorRegistry
from nodeone.core.easyai.domains import DOMAIN_IDS, DomainId

__all__ = [
    'ConnectorRequest',
    'ContextSlice',
    'DomainConnector',
    'EventEnvelope',
    'EventTypeDescriptor',
    'ToolCallResult',
    'ToolDescriptor',
    'ToolInvocation',
    'ConnectorRegistry',
    'DOMAIN_IDS',
    'DomainId',
]
