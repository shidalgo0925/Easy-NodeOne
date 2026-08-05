# Tool Catalog — EasyAI / EN1

| Campo | Valor |
|-------|--------|
| Versión | **1.0** |
| Forma | `ToolDescriptor.tool_id` = `{domain}.{action}` |
| side_effect | `read` salvo indicación |

Schema detallado vive en el descriptor en wiring; aquí: contrato semántico + hint EN1.

---

## `context_resolver`

| tool_id | Descripción | EN1 hint |
|---------|-------------|----------|
| `context_resolver.get_app_context` | Product + brand + surface del host | `ContextResolver.current_app_context` |

## `resolver`

| tool_id | Descripción | EN1 hint |
|---------|-------------|----------|
| `resolver.get_organization_id` | Org activa del request | `runtime.resolve_organization_id` |
| `resolver.get_active_app` | App launcher activa | `launcher` / `app_shell` |

## `organizations`

| tool_id | Descripción | EN1 hint |
|---------|-------------|----------|
| `organizations.get` | Detalle org por id (scoped) | `OrganizationService` |
| `organizations.list_accessible` | Orgs del usuario | `user_organization` |

## `users`

| tool_id | Descripción | EN1 hint |
|---------|-------------|----------|
| `users.get_me` | Snapshot actor | `current_user` |
| `users.list_org_memberships` | Membresías user↔org | `user_organization` |

## `entitlements`

| tool_id | Descripción | EN1 hint |
|---------|-------------|----------|
| `entitlements.get_effective` | Entitlement efectivo org×product | `EntitlementService` |
| `entitlements.has_feature` | Check feature flag de plan | `EntitlementService.has_feature` |

## `subscriptions`

| tool_id | Descripción | EN1 hint |
|---------|-------------|----------|
| `subscriptions.list` | Suscripciones org | `SubscriptionRegistry` |
| `subscriptions.list_active_products` | Productos activos | `SubscriptionRegistry` |

## `licenses`

| tool_id | Descripción | EN1 hint |
|---------|-------------|----------|
| `licenses.list_registers` | Licencias por caja | register license service |
| `licenses.expiring` | Licencias por vencer (días) | mismas tablas vía servicio |
| `licenses.get_policy` | Cupos LicensePolicy | `GET /api/eposone/license-policy` |

## `contacts`

| tool_id | Descripción | EN1 hint |
|---------|-------------|----------|
| `contacts.search` | Buscar contactos org | `/api/admin/contacts`, eposone contacts |
| `contacts.get` | Detalle contacto | Contact service |

## `crm`

| tool_id | Descripción | EN1 hint |
|---------|-------------|----------|
| `crm.status` | Declara limited / stub | App Registry |
| *(resto)* | `not_implemented` V1 | — |

## `membership`

| tool_id | Descripción | EN1 hint |
|---------|-------------|----------|
| `membership.verify` | Verificar miembro (email/…) | `/api/v1/membership/verification` |
| `membership.list_plans` | Planes (si módulo on) | membership services |

## `payments`

| tool_id | Descripción | EN1 hint |
|---------|-------------|----------|
| `payments.pos_mix_today` | Mix medios día negocio | OCC pagos |
| `payments.pos_open_balances` | Pedidos unpaid/partial (resumen) | Order Domain query vía servicio |
| `payments.membership_pending` | Pagos membership pendientes (si aplica) | `models/payments` vía servicio pagos |

## `products`

| tool_id | Descripción | EN1 hint |
|---------|-------------|----------|
| `products.search` | Buscar catálogo | ProductService / eposone products |
| `products.get` | Detalle product_ref | CoreProduct service |
| `products.stock_alerts` | Críticos / sin stock | dashboard stock signals |

## `commerce`

| tool_id | Descripción | EN1 hint |
|---------|-------------|----------|
| `commerce.get_day_board` | Board OCC Hoy | `build_operations_control_today` |
| `commerce.list_exceptions` | Excepciones caja | `build_operations_control_excepciones` |
| `commerce.get_shift` | Arqueo/resumen turno | `build_shift_close_report` |
| `commerce.get_shift_timeline` | Bitácora turno | `build_shift_bitacora` |
| `commerce.list_open_orders` | Pedidos abiertos (filtros) | Order Domain / eposone orders API |
| `commerce.get_order` | Pedido + pagos (DTO) | Order Domain |

## `dashboard`

| tool_id | Descripción | EN1 hint |
|---------|-------------|----------|
| `dashboard.get_kpis` | KPIs operativos rango | `CommerceDashboardService` |
| `dashboard.top_products` | Top productos | mismo servicio |
| `dashboard.sales_by_hour` | Serie horaria | mismo servicio |

## `analytics`

V1: **alias** de `dashboard.*` + `commerce.get_day_board` / health.  
tool_ids espejo opcionales: `analytics.get_kpis` → mismo backend.

## `history`

| tool_id | Descripción | EN1 hint |
|---------|-------------|----------|
| `history.list` | Timeline historial org | `/api/admin/history` |

## `audit`

| tool_id | Descripción | EN1 hint |
|---------|-------------|----------|
| `audit.list_system_actions` | Subset system del historial | HistoryLogger / admin history filters |

## `event_bus`

| tool_id | Descripción | EN1 hint |
|---------|-------------|----------|
| `event_bus.list_types` | Catálogo tipos conocidos | Event Catalog + commerce.events |
| `event_bus.pull` | Pull desde cursor | `/api/platform/sync/events` |

---

## Política V1

- Solo **read** salvo GO explícito para writes.
- Tools multi-org plataforma: **fuera de V1**.
- Todo tool debe poder responder `not_implemented` hasta existir adapter.
