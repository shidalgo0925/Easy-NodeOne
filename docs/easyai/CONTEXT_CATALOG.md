# Context Catalog — EasyAI / EN1

| Campo | Valor |
|-------|--------|
| Versión | **1.0** |
| Forma | `ContextSlice` (`context_id`, `domain_id`, `title`, `payload`, …) |

Cada entrada: id · dominio · contenido del payload · fuente EN1 · notas.

---

## Plataforma / resolución

### `ctx.product_brand`
- **domain:** `context_resolver`
- **payload:** `{ product_code, surface, brand_name, tagline, theme_tokens?, allowed_apps? }`
- **fuente:** `ContextResolver.current_app_context()` / ProductRegistry / BrandContext
- **nota:** `allowed_apps` es hint suave; no sustituye entitlements

### `ctx.organization`
- **domain:** `organizations` (+ `resolver`)
- **payload:** `{ organization_id, name, subdomain, timezone, status? }`
- **fuente:** `OrganizationService` / `SaasOrganization`

### `ctx.session_scope`
- **domain:** `resolver`
- **payload:** `{ organization_id, user_id, active_app_id, product_code, surface }`
- **fuente:** runtime + launcher + ContextResolver

### `ctx.user`
- **domain:** `users`
- **payload:** `{ user_id, display_name, email?, is_admin?, organization_ids[] }`
- **fuente:** `current_user` + `user_organization` (sin secretos/password)

### `ctx.entitlements`
- **domain:** `entitlements`
- **payload:** `{ product_code, plan_code?, state, features{}, limits{}, overrides? }`
- **fuente:** `EntitlementService`

### `ctx.subscriptions`
- **domain:** `subscriptions`
- **payload:** `{ items: [{ product_code, status, started_at?, ends_at? }] }`
- **fuente:** `SubscriptionRegistry`

---

## Operación comercial / POS

### `ctx.commerce.day_summary`
- **domain:** `commerce` / `dashboard`
- **payload:** `{ day_local, timezone, sales, orders_count, shifts_open, shifts_closed, differences, alerts }`
- **fuente:** OCC `build_operations_control_today` / dashboard KPIs

### `ctx.commerce.health`
- **domain:** `analytics` / `dashboard`
- **payload:** `{ score, devices_ok, devices_stale, open_orders, stale_orders, exceptions }`
- **fuente:** OCC `build_operations_control_operacion`

### `ctx.commerce.payment_mix`
- **domain:** `payments` / `commerce`
- **payload:** `{ day_local, methods: [{ method, label, amount, share_pct }], total }`
- **fuente:** OCC pagos

---

## Catálogo / personas

### `ctx.products.snapshot`
- **domain:** `products`
- **payload:** `{ count_active?, currency?, note }` — resumen corto; detalle vía tools
- **fuente:** ProductService counts

### `ctx.contacts.scope`
- **domain:** `contacts`
- **payload:** `{ organization_id, searchable: true }`
- **fuente:** contact APIs (declarativo)

### `ctx.membership.scope`
- **domain:** `membership`
- **payload:** `{ verification_api: true, plans_available? }`
- **fuente:** membership module / API Center (según silo)

### `ctx.crm.limited`
- **domain:** `crm`
- **payload:** `{ status: "limited", reason: "ecrm_stub", fallback_domain: "contacts" }`
- **fuente:** App Registry / inventário — **no inventar CRM**

---

## Licencias / auditoría

### `ctx.licenses.register_summary`
- **domain:** `licenses`
- **payload:** `{ active, grace, expired, unknown }` (conteos org)
- **fuente:** register license service

### `ctx.audit.capabilities`
- **domain:** `audit` / `history`
- **payload:** `{ history_api: true, admin_history: true }`
- **fuente:** history module

### `ctx.event_bus.capabilities`
- **domain:** `event_bus`
- **payload:** `{ outbox: true, pull_path: "/api/platform/sync/events" }`
- **fuente:** platform events

---

## Reglas de ensamblado (diseño)

Para un Business Assistant en request autenticado, el **mínimo** recomendado:

1. `ctx.session_scope`
2. `ctx.organization`
3. `ctx.product_brand`
4. `ctx.entitlements`
5. Dominio activo (`ctx.commerce.day_summary` si app = eposone)

EasyAI ensambla; EN1 solo publica slices.
