# Connector Specification — EasyAI ↔ EN1

| Campo | Valor |
|-------|--------|
| Versión | **1.0** (diseño) |
| SDK | `nodeone.core.easyai` |
| Estado | Aprobado para documentación; wiring pendiente GO |

---

## 1. Propósito

Definir cómo cada dominio EN1 se publica hacia EasyAI Core como un **Domain Connector**:

```text
EasyAI Core
    │
    ▼
ConnectorRegistry  (EN1)
    │
    ├── organizations
    ├── commerce
    ├── entitlements
    └── …
         │
         ├── get_contexts(request) → ContextSlice[]
         ├── list_tools() / invoke_tool()
         └── list_event_types() (+ bus existente)
```

---

## 2. Tipos núcleo

Definidos en `backend/nodeone/core/easyai/contracts.py`:

| Tipo | Rol |
|------|-----|
| `ConnectorRequest` | Identidad de llamada (org, user, product, surface, flags) |
| `ContextSlice` | Paquete de contexto nombrado (DTO) |
| `ToolDescriptor` | Metadato de herramienta (JSON Schema in/out) |
| `ToolInvocation` / `ToolCallResult` | Ejecución |
| `EventTypeDescriptor` | Tipo de evento declarativo |
| `EventEnvelope` | Evento normalizado (lectura) |
| `DomainConnector` | Protocol obligatorio |

---

## 3. Reglas del connector

### 3.1 Obligatorio

1. Implementar `DomainConnector`.
2. `domain_id` ∈ `DOMAIN_IDS`.
3. Contextos y resultados = **dict JSON-safe**.
4. Tools `read` por defecto; `write`/`admin` requieren justificación y permiso.
5. Si `requires_organization` y `request.organization_id is None` → `error_code=organization_required`.
6. Mapear a **servicio EN1 existente** (`en1_service_hint`); no abrir SQL.

### 3.2 Prohibido

- Importar/retornar modelos SQLAlchemy.
- Exponer nombres de tabla o queries.
- Llamar LLMs / prompts.
- Inventar org/user distintos de `ConnectorRequest` (salvo tools platform explícitos multi-org, fuera de V1).

### 3.3 Idempotencia y errores

Códigos estables sugeridos:

| `error_code` | Uso |
|--------------|-----|
| `organization_required` | Falta org |
| `auth_required` | Usuario no autenticado |
| `forbidden` | RBAC / entitlement |
| `tool_not_found` | tool_id desconocido |
| `validation_error` | args inválidos |
| `not_implemented` | Connector declarado, adapter pendiente |
| `upstream_error` | Fallo servicio EN1 |

---

## 4. Madurez por dominio (diseño)

| domain_id | Madurez EN1 hoy | Connector V1 |
|-----------|-----------------|--------------|
| `context_resolver` | Alta | Contextos product/brand |
| `resolver` | Alta | Org + active app resolve |
| `organizations` | Alta | Contexto org + get org |
| `users` | Alta | User snapshot + orgs |
| `entitlements` | Alta | Effective entitlement |
| `subscriptions` | Alta | List/active products |
| `contacts` | Alta | Search/get |
| `membership` | Alta | Verify + plans (según silo) |
| `commerce` | Alta | Orders/shifts summary tools |
| `products` | Alta | Catalog search |
| `dashboard` | Alta | KPI snapshot |
| `analytics` | Media (≈ dashboard) | Alias operativo V1 |
| `licenses` | Alta | Register license status |
| `payments` | Media–Alta | Pending / mix (POS + membership) |
| `history` / `audit` | Alta | Timeline tools |
| `event_bus` | Alta | List/pull event types |
| `crm` | Baja (stub app) | Context “limited”; tools `not_implemented` o contacts-only |

---

## 5. Relación con inventarios previos

- **Contextos** se alimentan de ContextResolver, runtime org, entitlements (inventario §1).
- **Tools** delegan en servicios dashboard/OCC/order/cash/history (inventario §3–4, §7).
- **Eventos** reflejan `platform_domain_event` + order events + history (inventario §5).

---

## 6. Criterio de hecho (esta fase diseño)

- [x] Protocol `DomainConnector` en código.
- [x] Registry + `DOMAIN_IDS`.
- [x] Spec + API Contracts + 3 catálogos.
- [ ] Ningún adapter runtime (fase siguiente).
- [ ] Ningún endpoint HTTP EasyAI (fase siguiente).
