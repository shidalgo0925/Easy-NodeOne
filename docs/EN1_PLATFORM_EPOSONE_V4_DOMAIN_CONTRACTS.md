# EPosOne V4 — Contratos de dominio portables (Sprint 2)

| Campo | Valor |
|-------|--------|
| Sprint | **2 — Contrato de dominio** |
| Estado | **Documentado** — 9 jul 2026 · Sprint 3 providers: [`EN1_PLATFORM_EPOSONE_V4_PROVIDERS.md`](EN1_PLATFORM_EPOSONE_V4_PROVIDERS.md) |
| Roadmap | [`EN1_PLATFORM_EPOSONE_V4_ROADMAP.md`](EN1_PLATFORM_EPOSONE_V4_ROADMAP.md) |
| ADR | [ADR-002](ADR-002-EPOSONE-DOMAIN.md) |
| Dominio de negocio | [`EN1_PLATFORM_ETAPA6_DOMINIO_COMERCIAL.md`](EN1_PLATFORM_ETAPA6_DOMINIO_COMERCIAL.md) (estados/flujos; no reabre 6.1–6.8) |
| Alcance | **Solo contratos** — sin repositorios SQLite/API, sin sync, sin Android |

---

## 1. Objetivo

Definir el **contrato portable** que ambas implementaciones (Modo Local / Modo Plataforma) deben cumplir.

```text
Casos de uso EPosOne
        │
   Puertos (estos contratos)
        │
   ┌────┴────┐
SQLite     EN1 API     ← Sprint 3 (providers)
```

**Prohibido en este documento y en futuros tipos de dominio:**

- Nombres de tablas (`core_*`, `saas_*`).
- Referencias a SQLite, Room, Flask, SQLAlchemy, Gunicorn.
- Campos solo-EN1 (`source_app_id`, `organization_id` int de tenant) **como identidad primaria**.
- Campos solo-local (paths de archivo, rowid SQLite).

**Permitido:** IDs opacos (`id: string`), referencias cruzadas por id, enums de dominio, montos, fechas ISO-8601 UTC.

---

## 2. Convenciones

| Convención | Valor |
|------------|--------|
| Identificadores | `string` opaco (UUID v4 recomendado en Local; EN1 puede mapear a su id interno vía tabla de vínculo — ADR-004) |
| Dinero | `number` decimal (2 decimales en JSON; precisión en implementación) + `currency: string` (ISO 4217) |
| Fechas | ISO-8601 UTC (`2026-07-09T21:00:00Z`) |
| Nullabilidad | Campo omitido o `null` = ausente |
| Enums | string literals documentados |
| Serialización | JSON; mismos nombres de campo en Local y Plataforma |
| Versión de contrato | `schema_version: 1` en envelopes de export/vinculación |

### Envelope de export / vinculación (ADR-004)

```json
{
  "schema_version": 1,
  "exported_at": "2026-07-09T21:00:00Z",
  "mode_at_export": "local",
  "business": { "...BusinessConfig..." },
  "products": [],
  "customers": [],
  "employees": [],
  "inventory_balances": [],
  "orders": [],
  "cash_shifts": []
}
```

---

## 3. Contratos

### 3.1 BusinessConfig (Configuración / Empresa)

Contenedor del negocio en Modo Local; en Plataforma se mapea a organización/empresa EN1 **sin** exponer tablas.

| Campo | Tipo | Req. | Notas |
|-------|------|:----:|-------|
| `id` | string | sí | Id opaco del negocio |
| `name` | string | sí | Nombre comercial |
| `legal_name` | string | no | Razón social |
| `tax_id` | string | no | RUC / NIT / etc. |
| `currency` | string | sí | ISO 4217 default |
| `country_code` | string | no | ISO 3166-1 alpha-2 |
| `timezone` | string | no | IANA |
| `address` | object | no | `{ line1, city, region, postal_code }` |
| `tax_rates` | TaxRate[] | no | Impuestos del negocio |
| `created_at` | string | sí | ISO-8601 |
| `updated_at` | string | no | |

**TaxRate**

| Campo | Tipo | Req. |
|-------|------|:----:|
| `id` | string | sí |
| `name` | string | sí |
| `rate` | number | sí | 0.07 = 7% |
| `inclusive` | boolean | sí | Precio incluye impuesto |

**Branch** (sucursal — hija del negocio)

| Campo | Tipo | Req. |
|-------|------|:----:|
| `id` | string | sí |
| `business_id` | string | sí |
| `name` | string | sí |
| `address` | object | no |
| `is_default` | boolean | sí |

**Register** (caja lógica)

| Campo | Tipo | Req. |
|-------|------|:----:|
| `id` | string | sí |
| `branch_id` | string | sí |
| `name` | string | sí |
| `is_default` | boolean | sí |

---

### 3.2 Product (Producto)

| Campo | Tipo | Req. | Notas |
|-------|------|:----:|-------|
| `id` | string | sí | |
| `sku` | string | no | Código interno / barra |
| `name` | string | sí | |
| `description` | string | no | |
| `unit_price` | number | sí | Precio base lista |
| `currency` | string | sí | |
| `tax_rate_id` | string | no | Ref TaxRate |
| `product_type` | string | sí | `simple` \| `kit` \| `service` (alineado Etapa 6.5) |
| `active` | boolean | sí | |
| `track_stock` | boolean | sí | |
| `created_at` | string | sí | |
| `updated_at` | string | no | |

**KitLine** (si `product_type=kit`)

| Campo | Tipo | Req. |
|-------|------|:----:|
| `component_product_id` | string | sí |
| `quantity` | number | sí |

---

### 3.3 Customer (Cliente)

| Campo | Tipo | Req. | Notas |
|-------|------|:----:|-------|
| `id` | string | sí | |
| `display_name` | string | sí | |
| `email` | string | no | Clave preferida de vínculo usuario/cliente (ADR-004) |
| `phone` | string | no | |
| `document_id` | string | no | Cédula / pasaporte / RUC |
| `tax_id` | string | no | |
| `notes` | string | no | |
| `active` | boolean | sí | |
| `created_at` | string | sí | |
| `updated_at` | string | no | |

---

### 3.4 Employee (Empleado / cajero)

| Campo | Tipo | Req. | Notas |
|-------|------|:----:|-------|
| `id` | string | sí | |
| `display_name` | string | sí | |
| `email` | string | no | |
| `pin_hint` | string | no | Nunca guardar PIN en claro en export; solo flag `has_pin` |
| `has_pin` | boolean | sí | |
| `operational_roles` | string[] | sí | `waiter` \| `seller` \| `cashier` \| `supervisor` \| `manager` (Etapa 6.2) |
| `active` | boolean | sí | |
| `created_at` | string | sí | |

---

### 3.5 Order (Venta / Pedido) — agregado raíz

Centro del sistema (Etapa 6.3). **No** es la factura.

| Campo | Tipo | Req. | Notas |
|-------|------|:----:|-------|
| `id` | string | sí | |
| `order_ref` | string | sí | Referencia humana visible |
| `business_id` | string | sí | |
| `branch_id` | string | sí | Obligatorio POS |
| `register_id` | string | no | Caja lógica |
| `terminal_id` | string | no | Dispositivo |
| `customer_id` | string | no | Obligatorio crédito/delivery/FE nominativa |
| `created_by_employee_id` | string | no | |
| `cashier_employee_id` | string | no | Quien cobró |
| `operational_status` | string | sí | Ver enum abajo |
| `payment_status` | string | sí | `unpaid` \| `partial` \| `paid` \| `overpaid` |
| `fiscal_status` | string | sí | `not_required` \| `pending` \| `invoiced` \| `cancelled` |
| `currency` | string | sí | |
| `subtotal` | number | sí | |
| `tax_total` | number | sí | |
| `discount_total` | number | sí | |
| `grand_total` | number | sí | |
| `amount_paid` | number | sí | |
| `promotion_id` | string | no | |
| `parent_order_id` | string | no | Mesa / cuenta padre |
| `version` | integer | sí | Optimistic locking (Plataforma / sync) |
| `lines` | OrderLine[] | sí | |
| `payments` | Payment[] | no | Embebidos o por ref según provider |
| `created_at` | string | sí | |
| `updated_at` | string | no | |
| `idempotency_key` | string | no | Escrituras offline / duplicados |

**operational_status:** `draft` \| `confirmed` \| `in_progress` \| `ready` \| `delivered` \| `cancelled` \| `refunded`

**OrderLine**

| Campo | Tipo | Req. |
|-------|------|:----:|
| `id` | string | sí |
| `product_id` | string | no |
| `description` | string | sí |
| `quantity` | number | sí |
| `unit_price` | number | sí |
| `line_total` | number | sí |
| `tax_rate_id` | string | no |
| `line_status` | string | sí | Etapa 6.3 líneas |

**Payment**

| Campo | Tipo | Req. |
|-------|------|:----:|
| `id` | string | sí |
| `order_id` | string | sí |
| `payment_ref` | string | sí |
| `status` | string | sí | p.ej. `captured` \| `refunded` \| `failed` |
| `payment_type` | string | sí | `cash` \| `card` \| `transfer` \| `other` |
| `amount` | number | sí |
| `currency` | string | sí |
| `refunded_amount` | number | sí |
| `captured_at` | string | no |
| `idempotency_key` | string | no |

---

### 3.6 CashShift (Caja / turno)

| Campo | Tipo | Req. |
|-------|------|:----:|
| `id` | string | sí |
| `register_id` | string | sí |
| `branch_id` | string | sí |
| `opened_by_employee_id` | string | sí |
| `closed_by_employee_id` | string | no |
| `status` | string | sí | `open` \| `closed` |
| `opening_float` | number | sí |
| `closing_counted` | number | no |
| `expected_cash` | number | no |
| `currency` | string | sí |
| `opened_at` | string | sí |
| `closed_at` | string | no |

Regla de negocio (Etapa 6.1): máximo un turno `open` por `register_id`.

---

### 3.7 InventoryBalance (Inventario)

| Campo | Tipo | Req. |
|-------|------|:----:|
| `id` | string | sí |
| `product_id` | string | sí |
| `branch_id` | string | sí | O warehouse_id en evolución 6.5 |
| `quantity_on_hand` | number | sí |
| `quantity_reserved` | number | sí |
| `updated_at` | string | sí |

Movimientos detallados (`waste`, transferencias) se formalizan en Etapa 6.5 / Sprint 3 providers; v1 del contrato portable es el **saldo**.

---

### 3.8 Promotion (Promoción) — opcional v1

| Campo | Tipo | Req. |
|-------|------|:----:|
| `id` | string | sí |
| `name` | string | sí |
| `active` | boolean | sí |
| `rules` | object | sí | Opaco v1 — detalle en Sprint 3 |
| `valid_from` | string | no |
| `valid_to` | string | no |

---

### 3.9 Device (Terminal) — registro lógico

Usado en pedido y en Sprint 6 (Dispositivos POS EN1). En contrato portable:

| Campo | Tipo | Req. |
|-------|------|:----:|
| `id` | string | sí | UUID estable del dispositivo |
| `name` | string | no | |
| `profile` | string | sí | `fixed` \| `handheld` |
| `branch_id` | string | no | |
| `register_id` | string | no | |
| `app_version` | string | no | |
| `platform` | string | no | p.ej. `android` |
| `last_seen_at` | string | no | |

---

## 4. Puertos (interfaces) — definición conceptual

Sprint 3 implementará estas interfaces; Sprint 2 solo las nombra.

| Puerto | Operaciones típicas |
|--------|---------------------|
| `ProductRepository` | get, list, upsert, deactivate |
| `CustomerRepository` | get, list, upsert |
| `EmployeeRepository` | get, list, upsert |
| `OrderRepository` | get, list, create, update_status, add_payment |
| `CashShiftRepository` | get_open, open, close |
| `InventoryRepository` | get_balance, list_alerts, adjust (supervisor) |
| `ConfigRepository` | get_business, get_branches, get_registers, upsert_config |
| `PromotionRepository` | list_active, get |

Firma conceptual (no código):

```text
ProductRepository.list(query) → Product[]
ProductRepository.upsert(product) → Product
OrderRepository.create(order, idempotency_key?) → Order
```

Implementaciones futuras:

- `SqliteProductRepository`
- `ApiProductRepository`

---

## 5. Mapeo a scaffold EN1 (solo referencia Modo Plataforma)

| Contrato portable | Scaffold / nota EN1 (no es el contrato) |
|-------------------|----------------------------------------|
| Order | `OrderDTO` / `CommercialOrder` — hoy usa `id: int` + `organization_id`; el adapter API traducirá |
| Payment | `PaymentDTO` |
| Customer | Contact / cliente comercial |
| Product | Catálogo / services |
| CashShift | `CashRegisterService` / `core_cash_shift` |
| InventoryBalance | `CoreStockBalance` |
| BusinessConfig | `SaasOrganization` + org_units |
| Device | `PosTerminal` / Sprint 6 |

**Regla:** el adapter Plataforma convierte `string id` ↔ ids internos EN1. El dominio de app **nunca** importa modelos ORM.

---

## 6. Criterio de hecho Sprint 2

- [x] Contratos Producto, Cliente, Pedido/Venta, Caja, Inventario, Empleado, Config documentados.
- [x] Sin referencias a SQLite/EN1 como modelo.
- [x] Enums alineados a Etapa 6 (pedido, pago, fiscal, roles).
- [x] Envelope de export para vinculación (ADR-004).
- [x] Puertos nombrados para Sprint 3.
- [ ] Revisión / firma responsable.
- [ ] **No** implementar providers (Sprint 3) ni wizard (Sprint 4) en este entregable.

---

## 7. Fuera de alcance

- Código Android / Room / SQLite.
- Cambios a `nodeone/core/sync/` o `commerce/dtos.py` EN1.
- Asistente Vincular (Sprint 5).
- Módulo Dispositivos POS UI (Sprint 6).
