# EPosOne ↔ EN1 — Handoff productos + inventario (para APK)

| Campo | Valor |
|-------|--------|
| Fecha | **13 jul 2026** |
| Audiencia | Programador **EPosOne (APK / Flutter)** |
| Silo | Solo **Dev EN1** — `https://appdev.easynodeone.com` · `easynodeone-dev` |
| Org demo negocio | **Itsmo Brew = organization_id `5`** (no confundir con org `1` «Easy NodeOne - Dev») |
| Estado Git | Cambios de este bloque en **working tree Dev** (pueden no estar todos en un solo commit) |
| Relacionado | Provisioning: [`EN1_EPOSONE_HANDOFF_STATUS.md`](EN1_EPOSONE_HANDOFF_STATUS.md) · Roadmap V4: [`EN1_PLATFORM_EPOSONE_V4_ROADMAP.md`](EN1_PLATFORM_EPOSONE_V4_ROADMAP.md) |

---

## Una frase

EN1 BackOffice + APIs de **catálogo** ya exponen los campos alineados con la ficha EPosOne (incl. UOM/empaque/stock máx. e imagen). Inventario muestra **on hand / reserved / available** y **kardex**. **Sync catálogo/ventas APK↔EN1 aún no.**

---

## 1. Maestro de productos

### Campos (`core_product` → DTO → API)

| Campo | Tipo / notas |
|--------|----------------|
| `product_ref` | SKU (obligatorio, único por org) |
| `name`, `description` | |
| `product_type` | `good` \| `service` \| `kit` |
| `status` | `active` \| `inactive` |
| `unit_price`, `currency`, `cost_price` | |
| `barcode`, `category` | |
| `image_url` | relativa o URL; ver §2 |
| `tracks_inventory` | bool |
| `min_stock`, `max_stock` | alertas en Inventario BO |
| `uom` | UOM **venta** (default `und`) |
| `purchase_uom` | UOM **compra** (ej. `pack`, `caja`) |
| `pack_factor` | und de venta por **1** UOM compra (default `1`) |
| `source_app_id` | en create BO suele ser `eposone` |

### BO

- URL: `/admin/eposone/section/products`
- Crear / editar / eliminar-o-desactivar + foto

### API (sesión login EN1)

| Método | Ruta |
|--------|------|
| `GET`, `POST` | `/api/eposone/products` |
| `GET`, `PATCH`, `DELETE` | `/api/eposone/products/<product_ref>` |
| `POST` | `/api/eposone/products/<product_ref>/image` — multipart field `image_file` |

Respuesta de colección/ítem: `product` / `products` con `to_dict()` (incluye UOM, pack, min/max, imagen).

### Ejemplo Itsmo — `ib-agua`

- `uom=und`, `purchase_uom=pack`, `pack_factor=12`
- `min_stock=6`, `max_stock=48`
- `image_url=/static/uploads/eposone/products/o5_….jpg`

---

## 2. Imágenes de producto

- Guardado bajo: `static/uploads/eposone/products/o{orgId}_{hash}.{ext}`
- URL pública: `/static/uploads/eposone/products/...`
- Formatos: PNG, JPG, GIF, WebP · máx. ~3 MB
- Prioridad al guardar: **archivo** > URL form > conservar / `clear_image`
- Runtime escribe como usuario **`nodeone`** (carpeta debe ser writable por ese usuario)

---

## 3. Inventario

### Modelo (ya en Core)

- Saldo: `core_stock_balance` — `quantity_on_hand`, `quantity_reserved`, disponible = on_hand − reserved
- Movimiento: `core_stock_movement` — tipos: `adjust`, `reserve`, `release`, `deduct`, `return`

### BO

- URL: `/admin/eposone/section/inventory` (bodegas + ajuste + **saldos** + **kardex**)
- Saldos: nombre producto/bodega, UOM, alerta bajo mínimo / sobre máximo
- Kardex: últimos movimientos (fecha, tipo, cantidad, pedido, notas)

### API

| Método | Ruta |
|--------|------|
| `GET` | `/api/eposone/stock-balances` — query: `warehouse_org_unit_id`, `product_ref`, `limit` |
| `GET` | `/api/eposone/stock-movements` — query: `warehouse_org_unit_id`, `product_ref`, `movement_type`, `limit` |
| `POST` | `/api/eposone/stock-adjust` — body JSON (bodega, product_ref, quantity ±, notes) |

---

## 4. Demo Itsmo Brew (org 5)

- Jerarquía: sucursal centro → POS → **caja-01** + bodega
- Productos `ib-*` (agua, café, latte, croissant, …)
- Stock seed en varios SKUs; movimientos iniciales tipo `adjust` (notas seed)
- Provisioning EN1-02: **código = Caja** (no org/branch/pos en el Wizard)

---

## 5. Fuera de alcance (hasta nuevo GO)

- Sync fino **catálogo** APK ↔ EN1  
- Sync **venta** → deducción de stock en EN1  
- Transferencias bodega ↔ bodega (documento propio)  
- Licencias/cupos POS  
- Despliegue staging / prod / relatic de este bloque  

---

## 6. Checklist rápido para APK / QA

1. Login appdev con usuario que vea **Itsmo Brew** (org 5).  
2. Productos: listar / editar UOM + pack + foto.  
3. Inventario: ver saldos (reserved/disponible) y kardex tras un ajuste.  
4. Provisioning tablet: URL `https://appdev.easynodeone.com` + código de **caja-01** (contrato EN1-02).  
5. No esperar aún pull completo de catálogo desde EN1 hacia la APK.

---

## 7. Mensaje corto (copiar al chat del prog EPosOne)

```text
EN1 Dev (appdev) — Itsmo org 5.

Productos: además de SKU/precio/barcode/costo/categoría/imagen/min, hay
uom, purchase_uom, pack_factor, max_stock.
API: GET/POST /api/eposone/products · PATCH/DELETE …/<ref> · POST …/<ref>/image

Inventario: on_hand, reserved, available.
Kardex: GET /api/eposone/stock-movements
Saldos: GET /api/eposone/stock-balances
Ajuste: POST /api/eposone/stock-adjust

Imágenes: URL relativa /static/uploads/eposone/products/...

Provisioning sigue EN1-02: solo URL + código de caja.
Sync catálogo/ventas aún no — GO aparte cuando toque.

Probar Productos + Inventario en Itsmo Brew en appdev.
Doc: docs/EN1_EPOSONE_HANDOFF_PRODUCTOS_INVENTARIO.md
```

---

## 8. Repos

| Pieza | Dónde |
|-------|--------|
| EN1 | `/opt/easynodeone/dev/app` · rama `develop` · GitHub Easy-NodeOne |
| APK EPosOne | PC del equipo (proyecto Flutter local; **no** en el silo del servidor) |
