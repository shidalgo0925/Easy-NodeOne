# API Contracts — EasyAI Connector Layer (EN1)

| Campo | Valor |
|-------|--------|
| Versión | **1.0** (contrato de diseño) |
| Transporte V1 | **In-process** (Python `DomainConnector`) |
| Transporte V2 (opcional) | HTTP JSON bajo `/api/easyai/v1` — **no implementado** |

---

## 1. In-process API (normativo V1)

### 1.1 Registry

```text
ConnectorRegistry.register(connector)
ConnectorRegistry.get(domain_id) → DomainConnector | None
ConnectorRegistry.all() → DomainConnector[]
ConnectorRegistry.list_all_tools() → ToolDescriptor[]
ConnectorRegistry.missing_domain_ids() → string[]
```

### 1.2 DomainConnector

```text
get_contexts(ConnectorRequest) → ContextSlice[]
list_tools() → ToolDescriptor[]
invoke_tool(ToolInvocation) → ToolCallResult
list_event_types() → EventTypeDescriptor[]
```

### 1.3 ConnectorRequest (campos)

| Campo | Tipo | Notas |
|-------|------|-------|
| `organization_id` | int \| null | Tenant activo |
| `user_id` | int \| null | Actor |
| `product_code` | string \| null | de ContextResolver |
| `surface` | string \| null | platform \| portal \| product |
| `active_app_id` | string \| null | launcher |
| `locale` | string | default `es` |
| `timezone` | string \| null | IANA |
| `request_id` | string \| null | correlación |
| `capability_flags` | map[string,bool] | saas/entitlement soft |

### 1.4 ToolCallResult

```json
{
  "ok": true,
  "tool_id": "dashboard.get_kpis",
  "data": { },
  "error_code": null,
  "error_message": null
}
```

---

## 2. HTTP façade (contrato futuro — no implementar ahora)

Prefijo propuesto: `/api/easyai/v1`

Auth: sesión BO o service token (TBD con EasyAI). **No** API-Key de membership reuse sin diseño.

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/connectors` | Dominios registrados + missing |
| GET | `/connectors/{domain_id}/contexts` | Contextos (query: usa request server-side) |
| GET | `/connectors/{domain_id}/tools` | Catálogo tools del dominio |
| POST | `/tools/{tool_id}/invoke` | Body: `{ "arguments": { } }` |
| GET | `/connectors/{domain_id}/events/types` | Tipos declarados |
| GET | `/events` | Proxy de lectura a sync events (cursor) |

Errores HTTP: `400` validation · `401` auth · `403` forbidden · `404` tool/domain · `501` not_implemented.

---

## 3. Mapeo a APIs EN1 existentes (wiring hints)

Los adapters **no** reimplementan lógica; delegan:

| Connector tool (ej.) | Servicio / ruta EN1 actual |
|----------------------|----------------------------|
| `dashboard.get_kpis` | `CommerceDashboardService.build_operational_dashboard` |
| `commerce.list_open_shifts` | `CashRegisterService` / OCC today |
| `commerce.get_shift_exceptions` | `build_operations_control_excepciones` |
| `commerce.get_payment_mix` | `build_operations_control_pagos` |
| `products.search` | ProductService / `/api/eposone/products` |
| `contacts.search` | Contact APIs |
| `membership.verify` | `POST /api/v1/membership/verification` |
| `subscriptions.list_active` | `SubscriptionRegistry` |
| `entitlements.get_effective` | `EntitlementService` |
| `licenses.list_register` | register license service |
| `history.list` | `GET /api/admin/history` |
| `event_bus.list_since` | `GET /api/platform/sync/events` |
| `context_resolver.get_app_context` | `ContextResolver.current_app_context` |
| `resolver.get_organization` | `runtime.resolve_organization_id` + OrganizationService |

---

## 4. Versionado

- `tool_id` y `context_id` son **estables**; breaking change = nuevo id (`*.v2`) o bump de este documento.
- JSON Schema en descriptors puede ampliarse de forma aditiva (nuevas properties optional).
