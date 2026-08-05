"""Connector SDK — typed contracts (no I/O)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Mapping, Protocol, Sequence, runtime_checkable


@dataclass(frozen=True, slots=True)
class ConnectorRequest:
    """Resolved call context passed into every connector method.

    Built by EN1 from ContextResolver + org/user session — never by EasyAI guessing.
    """

    organization_id: int | None
    user_id: int | None
    product_code: str | None = None
    surface: str | None = None  # platform | portal | product
    active_app_id: str | None = None
    locale: str = 'es'
    timezone: str | None = None
    request_id: str | None = None
    # Soft capabilities (entitlement/saas flags), not a SQL dump
    capability_flags: Mapping[str, bool] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ContextSlice:
    """One named context packet for prompt/tool grounding.

    `payload` must be JSON-serializable DTOs only (dicts/lists/scalars).
    Forbidden: ORM instances, SQLAlchemy sessions, raw table rows as models.
    """

    context_id: str
    domain_id: str
    title: str
    payload: Mapping[str, Any]
    freshness: str = 'request'  # request | short_cache | snapshot
    as_of: datetime | None = None


@dataclass(frozen=True, slots=True)
class ToolDescriptor:
    """Machine-callable capability exposed by a domain connector."""

    tool_id: str
    domain_id: str
    name: str
    description: str
    input_schema: Mapping[str, Any]  # JSON Schema draft-07 subset
    output_schema: Mapping[str, Any]
    requires_organization: bool = True
    requires_auth: bool = True
    side_effect: str = 'read'  # read | write | admin
    # Stable pointer to existing EN1 service (documentation / wiring hint)
    en1_service_hint: str | None = None


@dataclass(frozen=True, slots=True)
class ToolInvocation:
    tool_id: str
    arguments: Mapping[str, Any]
    request: ConnectorRequest


@dataclass(frozen=True, slots=True)
class ToolCallResult:
    ok: bool
    tool_id: str
    data: Mapping[str, Any] | None = None
    error_code: str | None = None
    error_message: str | None = None


@dataclass(frozen=True, slots=True)
class EventTypeDescriptor:
    """Declarative event type a domain may emit into the catalog / bus."""

    event_type: str
    domain_id: str
    description: str
    payload_schema: Mapping[str, Any]
    # Where it already lives in EN1 (if any)
    en1_source_hint: str | None = None


@dataclass(frozen=True, slots=True)
class EventEnvelope:
    """Normalized event for EasyAI consumers (mirrors platform outbox shape)."""

    event_id: str
    event_type: str
    domain_id: str
    organization_id: int | None
    occurred_at: datetime
    payload: Mapping[str, Any]
    source_app_id: str | None = None


@runtime_checkable
class DomainConnector(Protocol):
    """Contract every EN1 domain connector must satisfy.

    Implementations call existing EN1 *services* only — never SQL/tables.
    """

    @property
    def domain_id(self) -> str:
        ...

    @property
    def display_name(self) -> str:
        ...

    def get_contexts(self, request: ConnectorRequest) -> Sequence[ContextSlice]:
        """Return context slices relevant for this domain + request."""
        ...

    def list_tools(self) -> Sequence[ToolDescriptor]:
        """Advertise tools (may be static; auth checked at invoke)."""
        ...

    def invoke_tool(self, invocation: ToolInvocation) -> ToolCallResult:
        """Execute a tool by id. Must validate args and org scope."""
        ...

    def list_event_types(self) -> Sequence[EventTypeDescriptor]:
        """Advertise event types this domain owns or mirrors."""
        ...
