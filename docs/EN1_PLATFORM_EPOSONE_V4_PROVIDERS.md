# EPosOne V4 — Data providers (Sprint 3)

| Campo | Valor |
|-------|--------|
| Sprint | **3 — Data providers** |
| Estado | **Implementado** — 9 jul 2026 (Dev EN1) |
| Roadmap | [`EN1_PLATFORM_EPOSONE_V4_ROADMAP.md`](EN1_PLATFORM_EPOSONE_V4_ROADMAP.md) |
| Contratos | [`EN1_PLATFORM_EPOSONE_V4_DOMAIN_CONTRACTS.md`](EN1_PLATFORM_EPOSONE_V4_DOMAIN_CONTRACTS.md) |
| ADR | [ADR-002](ADR-002-EPOSONE-DOMAIN.md) |
| Código | `backend/nodeone/core/eposone_domain/` |

---

## 1. Objetivo

Implementar los **puertos** nombrados en Sprint 2 y tres **providers** sin que el dominio conozca SQLite ni EN1.

```text
Casos de uso EPosOne
        │
   Puertos (ports.py)
        │
   ┌────┼────────────┐
Memory  SQLite     API EN1
(Local) (Local)   (Plataforma)
```

---

## 2. Paquete

| Módulo | Rol |
|--------|-----|
| `eposone_domain/models.py` | Dataclasses del contrato portable (IDs `str`) |
| `eposone_domain/ports.py` | `Protocol` runtime-checkable |
| `eposone_domain/memory/` | Provider in-process (tests / sketch Local) |
| `eposone_domain/sqlite/` | Provider disco vía `sqlite3` stdlib (Local) |
| `eposone_domain/api/` | Adapter sobre `OrderService`, `CoreProductService`, etc. |

**No toca:** `commerce/dtos.py`, `core/sync/`, rutas Flask, Android.

---

## 3. Bundles

```python
from nodeone.core.eposone_domain.memory import MemoryProviderBundle
from nodeone.core.eposone_domain.sqlite import SqliteProviderBundle
from nodeone.core.eposone_domain.api import ApiProviderBundle

local = MemoryProviderBundle()          # o SqliteProviderBundle('/path/db')
plat = ApiProviderBundle(organization_id=1)
```

Cada bundle expone: `products`, `customers`, `employees`, `orders`, `cash_shifts`, `inventory`, `config`, `promotions`.

---

## 4. Mapeo Plataforma (API)

| Portable | EN1 |
|----------|-----|
| `Product.id` | `str(CoreProduct.id)` ; `sku` ← `product_ref` |
| `product_type` | `good` ↔ `simple`; `kit` / `service` iguales |
| `Customer` | `ContactService` (`is_customer`) |
| `Employee` | `ContactService` (`is_employee`) — aproximación v1 |
| `Order` | `OrderService` + pagos `PaymentService` |
| `CashShift` | `CashRegisterService` (`register_ref` = `register_id`) |
| `InventoryBalance` | `StockService` (bodega ≈ `branch_id` org_unit) |
| `BusinessConfig` | `SaasOrganization` + branches vía `OrgUnitService` |
| `Register` list | Org units tipo `register` (Sprint 6) |

Cierre de caja API: `begin_reconcile` → `close_shift` (contrato EN1).

---

## 5. Criterio de hecho

- [x] Protocols named in Sprint 2 implemented as Python `Protocol`
- [x] Memory provider (Local sketch)
- [x] SQLite provider (Local on disk, stdlib)
- [x] API provider (Plataforma adapters + id `str` ↔ `int`)
- [x] Unit tests Memory / SQLite / mapping
- [x] Sin cambios a sync ni reescritura de dominio comercial EN1
- [ ] Revisión humana; GO Sprint 7 (sync) / APK

---

## 6. Fuera de alcance (siguientes sprints)

- Wizard Crear negocio / Conectar EN1 — ver [`EN1_PLATFORM_EPOSONE_V4_FIRST_START.md`](EN1_PLATFORM_EPOSONE_V4_FIRST_START.md) (Sprint 4)
- Asistente Vincular — ver [`EN1_PLATFORM_EPOSONE_V4_LINK_EN1.md`](EN1_PLATFORM_EPOSONE_V4_LINK_EN1.md) (Sprint 5)
- Dispositivos POS — ver [`EN1_PLATFORM_EPOSONE_V4_DEVICES.md`](EN1_PLATFORM_EPOSONE_V4_DEVICES.md) (Sprint 6)
- Cablear `core/sync/` al Modo Plataforma (Sprint 7)
- Provider Android Room / APK
