# EIS-009 — Sessions

| Campo | Valor |
|-------|--------|
| ID | **EIS-009** |
| Versión | **1.0.0** |
| Estado | **Frozen / Approved** |
| Padre | EIS-000 |

---

## 1. Propósito

Definir la **Session** de interoperabilidad entre un usuario/servicio, EasyAI Core y uno o más Connectors — sin implementar runtime.

---

## 2. Separación de sesiones

| Sesión | Owner | Rol |
|--------|-------|-----|
| **EasyAI Session** | ARP / EasyAI Core | Conversación, memoria de diálogo, tool loop |
| **Product Session** | Producto (EN1, EPosOne, …) | Auth de negocio del usuario en el producto (opcional) |
| **Connector Call Context** | Por request | Claims tenant/user/scopes en cada invoke |

El Connector **no** posee la conversación LLM. Solo responde Contexts/Tools/Events bajo un **Call Context** derivado de la EasyAI Session.

---

## 3. Session descriptor (lógico)

```json
{
  "session_id": "eas_…",
  "created_at": "2026-08-05T12:00:00Z",
  "tenant_id": "org_123",
  "organization_id": "org_123",
  "actor": {
    "type": "user",
    "subject_id": "user_9",
    "display_name": null
  },
  "product_code": "eposone",
  "connector_ids": ["eposone"],
  "capabilities_granted": ["commerce.read", "dashboard.read"],
  "locale": "es",
  "timezone": "America/Panama",
  "correlation_id": "req_…"
}
```

| Campo | Requerido | Notas |
|-------|-----------|-------|
| `session_id` | sí | Opaco, único en EasyAI |
| `tenant_id` / `organization_id` | sí | Alias según Manifest `tenant_claim` |
| `actor` | sí | `user` \| `service` |
| `connector_ids` | sí | Connectors habilitados en la sesión |
| `capabilities_granted` | sí | Intersección plan/RBAC/scopes |

---

## 4. Ciclo de vida (lógico)

```text
create → active → (refresh scopes) → close | expire
```

- **create:** EasyAI autentica actor + resuelve tenant + Discovery de Connectors.
- **active:** Context Builder pide Contexts; Tool Dispatcher invoca Tools con Call Context.
- **close/expire:** no más invokes; Memory de conversación queda en ARP (fuera EIS).

---

## 5. Call Context (por invoke)

Cada `tools/invoke` lleva (headers o envelope):

- Identidad (EIS-005)
- `session_id`
- `organization_id` / tenant
- `request_id`
- Scopes efectivos ⊆ `capabilities_granted`

El Connector valida; no confía en args del modelo para elegir otro tenant.

---

## 6. Reglas

1. Una Session EasyAI **no** implica sesión HTTP de producto, salvo que el Connector lo requiera (documentar en Manifest).
2. Service principals pueden abrir Session sin usuario (`actor.type=service`) para digests.
3. Cross-tenant en una Session: **prohibido** en v1.0 salvo capability `platform.admin` (futuro).
4. El producto no inventa `session_id` de EasyAI.
