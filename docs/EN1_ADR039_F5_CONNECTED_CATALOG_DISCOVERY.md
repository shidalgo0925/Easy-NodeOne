# EN1 ADR-039 F5 — Connected Catalog / Inventory Contract Discovery

| Campo | Valor |
|-------|--------|
| ADR | [ADR-039](ADR-039-EN1-PRODUCTS-INVENTORY-CONNECTED.md) |
| Tipo | **Discovery** (contrato) — **sin código EP1** · sin STG/PRD |
| Fecha | 2026-08-13 |
| Entorno inspeccionado | Dev EN1 `/opt/easynodeone/dev/app` · `develop` |
| Estado | **DONE (docs)** · **F6 OFF** hasta GO/ADR aparte |
| Relacionados | [Handoff productos/inventario](EN1_EPOSONE_HANDOFF_PRODUCTOS_INVENTARIO.md) · [ADR-034 Connected provisioning](ADR-034-CONNECTED-PROVISIONING-FLOW.md) · [ADR-037 M2M inventory](EN1_ADR037_M2M_INVENTORY.md) |

---

## 1. Objetivo F5

Definir el **contrato Connected** de catálogo + stock entre EN1 (SoR) y EP1 (device), sin implementar F6 ni tocar Flutter/EP1.

Pregunta rectora: **¿Qué ya existe en EN1 para sync down/up, y qué falta para que Connected use el Inventario nativo ADR-039 sin segundo ledger?**

---

## 2. Resumen ejecutivo

| Dirección | Hoy (Dev EN1) | Hueco vs ADR-039 Connected |
|-----------|---------------|----------------------------|
| **EN1 → device (sync down)** | `GET /api/v1/devices/bootstrap` (Bearer device) | Snapshot full; versión catálogo gruesa; no habla `inventory_service` kinds |
| **EN1 UI sesión (BO)** | `/api/eposone/products*`, stock-* + secciones EPosOne | Duplica superficie vs `/admin/products` + `/admin/inventory` nativos |
| **Device → EN1 (sync up)** | Sync queue: orders/cash + `stock_adjust` | No hay evento tipado ADR-039 (`SALE`/`RECEIPT`/…) con `source_system=EP1` + idempotency estable |
| **Standalone EP1** | Catálogo local | **No debe depender** de EN1 (invariante ADR-039) |
| **M2M Integration Center** | Familia distinta (ADR-037) | Connected POS **no** usa `X-API-Key` para catálogo |

**Conclusión:** SoR de producto/stock Connected ya es `core_product` + `core_stock_*`. F6 no crea tablas nuevas de catálogo; debe **formalizar contrato** sobre bootstrap + movimientos vía `inventory_service` (o bridge explícito a `StockService`) con `source_system` / `source_event_id`.

---

## 3. Superficies existentes (solo EN1)

### 3.1 Device Bootstrap — Sync Down (oficial Hito 2)

| Item | Valor |
|------|--------|
| Endpoint | `GET /api/v1/devices/bootstrap` |
| Auth | Device Bearer (`Authorization`) |
| Código | `DeviceProvisioningService.build_bootstrap_for_terminal` · `devices_v1_routes.py` |
| `include` | `config`, `products`, `stock` (alias `stock_balances`), `cashiers`, `policies` |
| Versión catálogo | `catalog_version` ≈ `max(core_product.updated_at).timestamp()` o `len(products)` |
| Política | `installation.sync_policy.mode = bootstrap_then_incremental` · `catalog_full_on_mismatch: true` (declarado; incremental **no** implementado como delta API) |

**Payload producto (extracto):** `product_ref`, name, description, type, status, category, fiscal_category, barcode, prices, `tracks_inventory`, uom/pack, min/max_stock, image_url.

**Payload stock:** por balance — `product_ref`, `warehouse_ref`, `warehouse_org_unit_id`, on_hand / reserved / available. Bodega resuelta por sucursal del terminal (`StockService.resolve_warehouse_id`); fallback = todos los saldos org.

### 3.2 API sesión EPosOne (login humano / BO)

Prefijo `/api/eposone/` · `@login_required` · `api_routes.py`:

| Método | Path | Uso |
|--------|------|-----|
| CRUD | `/products`, `/products/<ref>`, image | BO / herramientas |
| GET | `/stock-balances`, `/stock-movements` | Lectura |
| POST | `/stock-adjust` | Ajuste manual |

**No** es el canal Connected de tablet (canal = device Bearer).

### 3.3 Sync up (cola EP1)

`eposone/sync_handlers.py` — operaciones incluyen `stock_adjust` → `StockService.record_manual_adjust` (`source_app_id='eposone'`).

Pedidos: deducción vía dominio comercial / `StockService.apply_order_movement` (eventos commerce), **no** vía `inventory_service.record_movement(kind='SALE', source_system='EP1')`.

### 3.4 Inventario nativo ADR-039 (F1–F4)

| Pieza | Path |
|-------|------|
| Products UI | `/admin/products` · módulo `products` |
| Inventory UI | `/admin/inventory` · módulo `inventory` |
| Core | `inventory_service` — kinds ADR-039, policy ALLOW/WARN/BLOCK, transfer, mínimos, idempotency `source_system`+`source_event_id` |
| Ledger | **mismo** `core_stock_*` (sin tercer ledger) |

EPosOne BO «Stock POS» (`/admin/eposone/section/inventory`) sigue siendo UI operativa POS sobre el mismo ledger.

---

## 4. Mapa de ownership (Connected)

```text
                    ┌─────────────────────────────┐
                    │  EN1 SoR                      │
                    │  core_product                 │
                    │  core_stock_balance/movement  │
                    │  core_org_unit (warehouse)    │
                    └──────────────┬────────────────┘
           write BO EN1 / EPosOne  │  read bootstrap
           inventory_service       │  (device Bearer)
           StockService            ▼
                    ┌─────────────────────────────┐
                    │  EP1 Connected device         │
                    │  cache local + offline up orders │
                    └─────────────────────────────┘

Standalone EP1: SoR local — sin dependencia EN1 (F6 no la introduce).
```

---

## 5. Gaps → input F6 (propuesta; sin implementar)

| # | Gap | Propuesta F6 (EN1-only salvo GO EP1) |
|---|-----|--------------------------------------|
| G1 | Bootstrap no usa `inventory_service` / kinds ADR-039 | Mantener snapshot balances; documentar mapping engine `adjust/deduct` ↔ kinds |
| G2 | Incremental catalog no existe | Opción A: `If-None-Match` / `catalog_version` → 304; B: `changed_since`; P0 = full on mismatch (ya declarado) |
| G3 | Sync up venta no marca `source_system=EP1` + event id estable | Al cerrar/capturar: `record_movement(SALE, …)` **o** bridge order→inventory con idempotency `EP1:{device}:{local_event_id}` |
| G4 | `stock_adjust` sync bypassea reasons ADR-039 | Mapear a `ADJUSTMENT_IN/OUT` + reason allow-list |
| G5 | Dos UIs BO (EN1 Inventario vs Stock POS) | Política: Connected ops stock en EN1 Inventario; Stock POS = atajo POS (label ya F3); unificar APIs en F6+ si GO |
| G6 | Transferencias F4 no en bootstrap/device | Device no crea transferencias EN1 en P0; BO EN1 sí |
| G7 | Mínimos | Ya en producto + UI alertas; bootstrap ya envía `min_stock`/`max_stock` — EP1 decide UX |
| G8 | Auth Connected ≠ Integration API Key | No mezclar con ADR-037 F1 |

**Fuera de F6 sin GO explícito:** cambios schema Flutter, STG/PRD, M2M commercial keys para POS.

---

## 6. Contrato borrador (normativo para F6)

### 6.1 Sync Down (device)

1. Auth: Device Bearer únicamente.  
2. Endpoint canónico: `GET /api/v1/devices/bootstrap?include=products,stock,…`.  
3. SoR: `core_product` + `core_stock_*`.  
4. Si `catalog_version` local ≠ server → full products (política actual).  
5. Stock scoped a warehouse de sucursal del register cuando exista.  
6. Standalone: **no** llama este endpoint como SoR.

### 6.2 Sync Up stock (device → EN1)

1. Toda mutación de stock Connected debe ser **idempotente** (`source_system` + `source_event_id`).  
2. Preferir kinds ADR-039 vía `inventory_service` (o adaptador 1:1 a `StockService` documentado).  
3. Prohibido DELETE de movimientos confirmados.  
4. Tenant = org del device; no cross-org.

### 6.3 Campos catálogo P0 (alineados bootstrap actual)

`product_ref` (SKU), name, status, product_type, tracks_inventory, unit_price, currency, barcode, category, fiscal_category, uom, purchase_uom, pack_factor, min_stock, max_stock, image_url.

Tipos UI EN1: STOCKABLE / NON_STOCKABLE / SERVICE ↔ `good`+tracks / `good` / `service` (F0).

---

## 7. Decisiones F5 (cerradas en discovery)

| Tema | Decisión |
|------|----------|
| ¿Tercer catálogo Connected? | **No** — reutilizar `core_product` |
| ¿Segundo ledger? | **No** — `core_stock_*` + `inventory_service` |
| ¿Canal device? | **Bootstrap Bearer** (no session cookie; no Integration API Key) |
| ¿F6 toca EP1? | **Solo con GO/ADR aparte**; F5 no toca EP1 |
| ¿F6 mínimo EN1? | Adaptador sync/order → `inventory_service` + doc contrato + tests Dev; bootstrap sigue |

---

## 8. Evidencia código (rutas)

| Área | Path |
|------|------|
| Bootstrap | `backend/nodeone/modules/eposone/device_provisioning.py` (`build_bootstrap_for_terminal`) |
| Device routes | `backend/nodeone/modules/eposone/devices_v1_routes.py` |
| Session API | `backend/nodeone/modules/eposone/api_routes.py` |
| Sync up | `backend/nodeone/modules/eposone/sync_handlers.py` |
| Inventory nativo | `backend/nodeone/core/platform/inventory_service.py` |
| UI nativa | `backend/nodeone/modules/en1_inventory/`, `en1_products/` |

---

## 9. STOP F5

Discovery suficiente para abrir **F6** con GO explícito.  
**No** implementado: código EP1, cambios bootstrap, adaptador sync→inventory, STG/PRD.

**Siguiente:** `GO ADR-039 F6` (o ADR hijo Connected catalog) acotando solo EN1 o EN1+EP1.
