# ADR-039 — EN1 Products & Inventory Native + EP1 Connected Catalog

| Campo | Valor |
|-------|--------|
| ID | **ADR-039** |
| Estado | **ACCEPTED** — 13 ago 2026 |
| GO actual | **F0–F3 DONE (Dev)** · F4+ OFF hasta GO |
| Baseline | F3 tip `develop` |
| Base | [ADR-038](ADR-038-EN1-MODULAR-DOMAIN-ARCHITECTURE.md) Module Registry F1 |
| F0 inventario | [EN1_ADR039_F0_PRODUCTS_INVENTORY_DISCOVERY.md](EN1_ADR039_F0_PRODUCTS_INVENTORY_DISCOVERY.md) |
| EP1 / STG / PRD | **NO TOCAR** (F0–F5) |
| Connected (F6) | OFF hasta GO específico |

---

## Decisión

EN1 formaliza módulos nativos **Productos** e **Inventario**. EPosOne **no** es el módulo Inventario de EN1.

ADR-039 **supersede** únicamente el slice Products/Inventory previsto como F3/F4 en ADR-038. No supersede Module Registry, Memberships, Sales, Promotions, ni el resto de ADR-038.

Dependencia Module Registry: `inventory → products`.

Regla crítica: **no crear un tercer catálogo**. F0 eligió **FORMALIZE `core_product`**.

---

## Fases

| Fase | Contenido | Gate |
|------|-----------|------|
| **F0** | Discovery | DONE con este GO |
| **F1** | Products formalization (nav + CRUD + registry) | DONE |
| **F2** | Inventory Core | DONE |
| **F3** | Inventory UI + nav Inventario nativo (EPosOne = Stock POS) | DONE → STOP |
| **F4** | Transfers / mínimos | GO |
| **F5** | Connected contract discovery (sin código EP1) | GO → STOP |
| **F6** | Connected implementation | GO/ADR aparte |

---

## Invariantes (extracto)

1. EN1 Inventory ≠ EPosOne  
2. Products ≠ Inventory · stock = movimientos  
3. No DELETE de movimientos confirmados  
4. Tenant isolation  
5. No tocar EP1 en F0–F5  
6. Standalone EP1 no depende de EN1  

---

## Changelog

| Fecha | Nota |
|-------|------|
| 2026-08-13 | ACCEPTED. GO F0+F1 Dev. Canonical product = `core_product`. |
| 2026-08-13 | F1 DONE Dev: módulo `products`/`inventory` en registry; UI `/admin/products`; nav Productos; labels Stock POS / Conteo físico; tests. **STOP** — F2 requiere GO. |
| 2026-08-13 | F2 DONE Dev: `inventory_service` sobre core_stock_* + warehouse default; kinds ADR-039; policy ALLOW/WARN/BLOCK; kardex; tests Coca-Cola + idempotency. **STOP** — F3 UI requiere GO. |
| 2026-08-13 | F3 DONE Dev: UI `/admin/inventory` (Existencias, Movimientos, Entrada, Ajuste, Kardex, Almacenes); nav v2 área Inventario; EPosOne sigue como Stock POS; tests. **STOP** — F4 requiere GO. |
