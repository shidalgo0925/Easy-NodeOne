# EN1 ADR-039 F6 — Connected Inventory Bridge (EN1-only)

| Campo | Valor |
|-------|--------|
| ADR | [ADR-039](ADR-039-EN1-PRODUCTS-INVENTORY-CONNECTED.md) |
| Discovery | [F5](EN1_ADR039_F5_CONNECTED_CATALOG_DISCOVERY.md) |
| Fecha | 2026-08-13 |
| Alcance | **Solo Dev EN1** — adaptador sync/API/BO → `inventory_service` |
| EP1 / Flutter / STG / PRD | **NO TOCADO** |
| Bootstrap device | Sin cambios (sigue snapshot `core_*`) |

---

## Entrega

Módulo `nodeone/core/platform/connected_inventory.py`:

| Función | Comportamiento |
|---------|----------------|
| `record_connected_adjust` | Si `products`+`inventory` ON → `ADJUSTMENT_IN/OUT` + `source_system`/`source_event_id` (idempotency). Si OFF → `StockService.record_manual_adjust` |
| `apply_connected_order_movement` | `deduct`/`return` → `SALE`/`RETURN` vía inventory_service; `reserve`/`release` y módulo OFF → `StockService.apply_order_movement` |

Cableado:

- `eposone/stock_api.py` · `eposone/sync_handlers.py` (`stock_adjust`) · `eposone/routes.py` (BO adjust)
- `commerce/stock_handlers.py` (eventos deduct/return)

Supervisor approval se mantiene (misma gate que antes).

---

## Fuera de este GO

- Cambios Flutter / schema APK  
- Incremental catalog / bootstrap rewrite  
- STG / PRD / relatic  
- Integration API Key (ADR-037)

---

## STOP

F6 slice EN1 **DONE**. Más Connected (delta bootstrap, EP1 client) requiere GO nuevo.
