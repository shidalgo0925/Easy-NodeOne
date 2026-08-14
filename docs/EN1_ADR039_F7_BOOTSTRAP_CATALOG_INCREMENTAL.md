# EN1 ADR-039 F7 — Bootstrap catalog incremental (EN1-only)

| Campo | Valor |
|-------|--------|
| ADR | [ADR-039](ADR-039-EN1-PRODUCTS-INVENTORY-CONNECTED.md) |
| Fecha | 2026-08-13 |
| Alcance | Dev EN1 — delta catálogo en `GET /api/v1/devices/bootstrap` |
| Flutter / EP1 client | **NO TOCADO** (sigue full-pull si no envía `catalog_version`) |
| STG / PRD | **NO** |

---

## Contrato aditivo

Query (igual patrón que `cashiers_version`):

```http
GET /api/v1/devices/bootstrap?include=products,stock&catalog_version=<int>
```

Respuesta:

| Campo | Significado |
|-------|-------------|
| `catalog_version` | Siempre presente (timestamp `max(core_product.updated_at)` o fallback) |
| `products_changed` | `false` si `catalog_version` query == server |
| `products` | Omitido si no cambió; presente si cambió o no se envió known version |
| `products_count` | `0` si omitido; len(products) si se envía |

Stock **sigue full** en cada bootstrap con `include=stock` (cambia con más frecuencia).

Clientes viejos (sin query `catalog_version`): `products_changed=true` + array completo — compatible.

---

## Código

- `DeviceProvisioningService.build_bootstrap_for_terminal(..., known_catalog_version=)`
- `devices_v1_routes.devices_bootstrap` parsea `catalog_version`

---

## STOP

F7 EN1 DONE. Consumo en APK / Flutter requiere GO aparte. Push F3–F7 si se pide.
