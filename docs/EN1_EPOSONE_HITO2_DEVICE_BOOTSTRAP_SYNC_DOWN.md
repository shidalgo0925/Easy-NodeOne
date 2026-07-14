# EPosOne ↔ EN1 — Hito 2: Device Bootstrap (Sync Down) — CONTRATO

| Campo | Valor |
|-------|--------|
| Hito | **Hito 2 — Device Bootstrap (Sync Down) v1** |
| Estado | **Implementado en Dev** (13 jul 2026) — `GET /api/v1/devices/bootstrap` · pendiente E2E APK |
| Fecha | **13 jul 2026** |
| Precondición | Hito 1 Provisioning EN1-02 **cerrado / congelado** |
| Auth | `Authorization: Bearer <access_token>` del register |
| Destino | El de la Caja provisionada (**no** reenviar org/branch/pos/caja en el Wizard) |
| Ambiente Dev | `https://appdev.easynodeone.com` |
| Handoff productos BO | [`EN1_EPOSONE_HANDOFF_PRODUCTOS_INVENTARIO.md`](EN1_EPOSONE_HANDOFF_PRODUCTOS_INVENTARIO.md) |
| Hito 1 | [`EPOSONE_EN1_HITO1_PROVISIONING_CONTRACT.md`](EPOSONE_EN1_HITO1_PROVISIONING_CONTRACT.md) · [`EN1_EPOSONE_HANDOFF_STATUS.md`](EN1_EPOSONE_HANDOFF_STATUS.md) |

---

## Objetivo (criterio de hecho)

Tablet **nueva**:

```text
Instalar APK → Provisionar (Hito 1) → Descargar bootstrap EN1
→ Guardar catálogo/imágenes/local → Mostrar productos EN1 → Lista para vender
```

Tras E2E Hito 2: se puede **eliminar dependencia del catálogo local Istmo**; EN1 es fuente de verdad del catálogo en modo Plataforma.

**No** es objetivo de este hito: sync de ventas, transferencias, compras, conteos, reservas de negocio, licencias, FE, CRM, IA.

---

## Principios

1. Un solo Auth: token Hito 1.  
2. Destino operativo ya resuelto por el código de Caja.  
3. v1 = **snapshot** (full pull) + versión (`config_version` y/o `catalog_version`).  
4. Imágenes: EN1 entrega `image_url` (relativa o absoluta); APK baja bytes y cachea local.  
5. Dominio APK no habla SQL de EN1; solo DTO JSON del contrato.  
6. Contrato aprobado → implementación EN1 Dev (`GET /api/v1/devices/bootstrap`) — E2E APK pendiente.

---

## Endpoints (EN1) — v1 implementado

| Método | Ruta | Auth | Descripción |
|--------|------|------|-------------|
| `GET` | `/api/v1/devices/config` | Bearer | Hito 1 — jerarquía + currency + timezone + `config_version` |
| `GET` | `/api/v1/devices/bootstrap` | Bearer | **Hito 2** — snapshot: config + products + stock_balances |

Query opcional: `include=config,products,stock` (default: los tres).

> Rutas `/catalog` y `/stock` separadas: no requeridas en v1 (todo en bootstrap).

### Query opcionales (v1)

- `since` / `catalog_version` — si EN1 aún no versiona, ignorar y devolver full.  
- `include=products,stock,config` — default todos.

### Respuesta `200` (forma lógica)

```json
{
  "schema_version": 1,
  "generated_at": "2026-07-14T00:00:00Z",
  "config_version": 1,
  "catalog_version": 1,
  "config": {
    "organization": { "id": 5, "name": "Itsmo Brew" },
    "branch": { "ref": "centro", "name": "CENTRO" },
    "pos": { "ref": "pos-centro", "name": "POS Centro" },
    "register": { "ref": "caja-01", "name": "Caja 1" },
    "currency": "USD",
    "timezone": "America/Panama",
    "business_name": "Itsmo Brew"
  },
  "products": [ { "...": "ProductDTO" } ],
  "stock_balances": [ { "...": "StockBalanceDTO" } ]
}
```

Errores:

| HTTP | `error` |
|------|---------|
| 401 | `token_invalid` / `token_required` |
| 403 | `device_inactive` |
| 404 | `device_not_found` |

---

## Payload — ProductDTO (Sync Down v1)

| Campo | Notas |
|--------|--------|
| `product_ref` | SKU / id opaco EN1 |
| `name` | |
| `description` | nullable |
| `product_type` | `good` \| `service` \| `kit` (mapear a tipos APK) |
| `status` | `active` \| `inactive` — APK suele filtrar inactive |
| `category` | nullable |
| `barcode` | nullable |
| `unit_price` | |
| `currency` | |
| `cost_price` | nullable |
| `tracks_inventory` | bool |
| `uom` | venta (default `und`) |
| `purchase_uom` | nullable |
| `pack_factor` | number (default 1) |
| `min_stock` | nullable |
| `max_stock` | nullable |
| `image_url` | relativa (`/static/...`) o absoluta |

---

## Payload — StockBalanceDTO (v1)

Ámbito: bodega(s) resolubles desde la **sucursal/caja** del device (misma regla que inventario BO).

| Campo | Notas |
|--------|--------|
| `product_ref` | |
| `warehouse_ref` o `warehouse_org_unit_id` | preferir `warehouse_ref` opaco si existe |
| `quantity_on_hand` | |
| `quantity_reserved` | |
| `quantity_available` | on_hand − reserved |

v1: **informativo** para UI/alerta; no implica reservas reales de pedidos ni deduct por venta.

---

## Imágenes

1. APK lee `image_url` del producto.  
2. Si es path relativo, concatena base URL del servidor (`https://appdev.easynodeone.com`).  
3. Descarga HTTP GET del recurso estático; cache local por `product_ref` + hash/url.  
4. Fallo de imagen **no** bloquea el resto del catálogo.

---

## Qué hace la APK (v1)

1. Tras Hito 1 (token válido), llamar bootstrap.  
2. Persistir productos (y opcionalmente stock) en SQLite local.  
3. Descargar imágenes referenciadas.  
4. UI de venta consume **solo** catálogo bajado (o merge explícito documentado; meta: reemplazar Istmo local).  
5. Re-bootstrap: bajo demanda / al subir `catalog_version` / `config_version` (detalle en GO implementación).

---

## Fuera de alcance (explícito)

- Ventas → stock / deducciones  
- Transferencias, compras, conteos  
- Reservas reales de negocio  
- Licencias / cupos  
- FE, CRM, IA  
- Cambios al Wizard o al código=Caja (Hito 1 congelado)  
- Campos nuevos de jerarquía en el cliente  

---

## Criterio de cierre Hito 2

Tablet limpia (sin depender del seed Istmo):

1. Provisionar contra appdev.  
2. Bootstrap 200 con productos Itsmo (org 5).  
3. Imágenes visibles donde haya `image_url`.  
4. Venta en APK usa SKUs EN1 (`ib-*` u otros de la org).  

---

## Aprobación / estado

| Rol | Acción |
|-----|--------|
| EN1 | ✅ API implementada en Dev · commit **`b254735`** |
| EPosOne | Consumir `GET /api/v1/devices/bootstrap` + E2E tablet |
| Ambos | E2E tablet nueva → cierre formal Hito 2 |

**Siguiente:** chat APK / Flutter — E2E Sync Down (no reabrir API EN1 sin bug).
