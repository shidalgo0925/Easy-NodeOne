# EN1 ADR-039 F0 — Products / Inventory Discovery

| Campo | Valor |
|-------|--------|
| ADR | [ADR-039](ADR-039-EN1-PRODUCTS-INVENTORY-CONNECTED.md) |
| Fecha | 2026-08-13 |
| Entorno | Dev EN1 · `develop` |
| Decisión F1 | **FORMALIZE `CoreProduct` / `core_product`** — no tercer catálogo |

---

## Current → Target (candidatos)

| Componente | Tabla / path | Org | Clase ADR-039 |
|------------|--------------|-----|---------------|
| **CoreProduct** | `core_product` · `models/core_master.py` | Sí | **FORMALIZE** (canónico F1) |
| CoreProductService / ProductService | `nodeone/core/master/product.py` | Sí | **FORMALIZE** |
| EPosOne BO products | escribe `core_product` | Sí | **REUSE** |
| eposone_domain Product mapping | portable | — | **ADAPT** |
| CoreStockBalance / Movement | `core_stock_*` | Sí | **REUSE** (F2) |
| StockService | `nodeone/core/commerce/stock.py` | Sí | **FORMALIZE** (F2) |
| CoreOrgUnit warehouse | `core_org_unit` | Sí | **REUSE** (F2) |
| Service / ServiceCategory | `service` / categories | Service sí; category **global** | **LEGACY** (Sales/membresías) |
| Sales quotation/invoice product_id | → Service.id | vía doc | **LEGACY** |
| Contador templates | `contador_product_*` | Sí | **DO NOT TOUCH** F1 |
| ETS product_code / subscriptions | `ets_product_*` | Sí | **DO NOT TOUCH** (SaaS registry) |

---

## Mapeo P0 → CoreProduct

| P0 | Campo |
|----|--------|
| SKU | `product_ref` |
| nombre | `name` |
| descripción | `description` |
| categoría | `category` (string) |
| unidad | `uom` |
| barcode | `barcode` |
| tipo STOCKABLE / NON_STOCKABLE / SERVICE | **ADAPT** UI: STOCKABLE=`good`+`tracks_inventory`; NON_STOCKABLE=`good` sin track; SERVICE=`service` |
| costo / precio | `cost_price` / `unit_price` |
| impuesto | `fiscal_category` (ITBMS) — distinto de `taxes` Sales |
| inventariable | `tracks_inventory` |
| activo | `status` active/inactive |

---

## Impacto

- **EPosOne:** bajo — mismo SoR `core_product`.  
- **Sales:** aislado — sigue en `Service`. Unificación fuera de F1.  
- **Nav confusión:** área Contador label «Inventario» + EPosOne «Inventario» → corregir labels en F1; mover/retirar entrada EPosOne en **F3**.

---

## Gaps F2

1. Formalizar Inventory UI/API sobre `core_stock_*` + warehouse org units.  
2. Tipos movimiento ADR-039 vs adjust/deduct actuales.  
3. FK/integrity product_ref.  
4. Transferencias warehouse↔warehouse.  
5. Política ALLOW/WARN/BLOCK negative.  
6. Seed module `inventory` usable (deps ya preparadas en F1).

---

## STOP F0

Evidencia suficiente → F1 reutiliza `core_product`. **No** crear `ProductV2`.
