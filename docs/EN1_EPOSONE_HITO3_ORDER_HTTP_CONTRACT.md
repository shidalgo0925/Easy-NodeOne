# EPosOne ↔ EN1 — Hito 3: Contrato HTTP Order Domain

| Campo | Valor |
|-------|--------|
| Estado | **CONGELADO** — 14 jul 2026 |
| Commit EN1 | **`36a0eb1`** · rama `develop` |
| Spec dominio | [`EN1_EPOSONE_ORDER_DOMAIN_SPEC_V1.md`](EN1_EPOSONE_ORDER_DOMAIN_SPEC_V1.md) |
| Base URL Dev | `https://appdev.easynodeone.com` |
| Audiencia | **P2 (APK)** — consumir sin inventar reglas |

Cambios a este contrato = nueva versión (v1.1+) + GO arquitectura.

---

## Auth

| Cliente | Cómo |
|---------|------|
| **POS / tablet** | `Authorization: Bearer <access_token>` del `POST /api/v1/devices/register` |
| BackOffice (opcional) | Sesión admin EN1; requiere terminal activo en la org |

Errores auth: `401` `{"error":"unauthorized"}` · `403` `device_inactive` / `forbidden` / `not_owner`.

**No** usar `GET /api/eposone/products` ni `@login_required` de BO para el Device Token.

---

## Endpoints

| Método | Path | Notas |
|--------|------|--------|
| `POST` | `/api/v1/orders` | Crear (o reutilizar abierto si `table_ref`) |
| `GET` | `/api/v1/orders` | Listar · query `status`, `table_ref`, `limit` |
| `GET` | `/api/v1/orders/{id}` | Detalle · `?include=events` |
| `PATCH` | `/api/v1/orders/{id}` | Metadatos (owner) |
| `POST` | `/api/v1/orders/{id}/events` | Acción / evento idempotente |
| `POST` | `/api/v1/orders/{id}/payments` | Pago / abono / parcial |
| `POST` | `/api/v1/orders/{id}/split` | Dividir líneas → pedido hijo |

---

## Ownership

| Acción | Quién |
|--------|--------|
| Editar / events (no pago) / split / patch | Solo **owner** (`owner_device_uuid` = `device_uuid` del token) |
| Pagos / `pedido.cobrado` | Cualquier device Bearer **de la misma org** |
| Sin mesa (`table_ref` null) | Cada `POST /orders` = Order nuevo |
| Con mesa | Un Order abierto por `(org, table_ref)`; `POST` reutiliza el abierto |
| Split | Hijo **hereda** `owner_device_uuid` / `owner_pos_ref` del padre |

`403` `not_owner` si no eres dueño.

---

## `POST /api/v1/orders`

### Body (ejemplo)

```json
{
  "local_number": "T-12",
  "table_ref": null,
  "user_ref": "cajero1",
  "customer_ref": null,
  "notes": null,
  "tip": 0,
  "event_id": "optional-uuid-for-pedido.creado"
}
```

### Response `201`

```json
{
  "order": {
    "id": 1,
    "en1_number": "EN1-5-1",
    "local_number": "T-12",
    "organization_id": 5,
    "branch_ref": "centro",
    "pos_ref": "pos-centro",
    "register_ref": "caja-01",
    "owner_device_uuid": "<device_uuid>",
    "owner_pos_ref": "pos-centro",
    "status": "open",
    "payment_status": "unpaid",
    "financially_closed": false,
    "subtotal": 0,
    "tax": 0,
    "discount": 0,
    "tip": 0,
    "total": 0,
    "amount_paid": 0,
    "items": [],
    "payments": [],
    "events": [ ... ]
  }
}
```

Si `table_ref` ya tiene pedido abierto → devuelve ese Order (mismo shape).

---

## `POST /api/v1/orders/{id}/events`

### Body

```json
{
  "event_id": "uuid-obligatorio-idempotente",
  "type": "producto.agregado",
  "actor_user_ref": "cajero1",
  "payload": { }
}
```

`event_id` **obligatorio**. Mismo `event_id` → no aplica de nuevo (idempotente).

### Tipos permitidos (`type`)

| type | payload típico |
|------|----------------|
| `pedido.actualizado` | `user_ref`, `notes`, `tip` |
| `producto.agregado` | `line_ref`, `product_ref`, `qty`, `unit_price`, `tax`, `discount`, `notes` |
| `producto.eliminado` | `line_ref` |
| `cantidad.modificada` | `line_ref`, `qty` |
| `pedido.enviado` | — |
| `linea.lista` | `line_ref` |
| `pedido.listo` | — |
| `linea.entregada` | `line_ref` |
| `pedido.entregado` | — |
| `linea.cancelada` | `line_ref` |
| `pedido.anulado` | `reason` (no si status `open`/`draft` → `use_modify_not_cancel`) |
| `pedido.devuelto` | `reason` |
| `pedido.cobrado` | solo si saldo 0 |
| `pago.registrado` / `pedido.creado` / `pedido.dividido` | preferir endpoints dedicados |

Response: `200` `{"order": ...}` (con events si se cargan).

---

## `POST /api/v1/orders/{id}/payments`

```json
{
  "amount": 2.5,
  "method": "cash",
  "kind": "payment",
  "currency": "USD",
  "customer_ref": null,
  "payment_ref": "optional",
  "event_id": "optional-uuid"
}
```

| `kind` | Regla |
|--------|--------|
| `payment` | Normal |
| `deposit` / `partial` / `abono` | Exige `customer_ref` (order o body) → CxC |

Si `amount_paid >= total` → `financially_closed=true`, `payment_status=paid` + evento `pedido.cobrado`.

Response: `201` `{"order": ...}`.

---

## `POST /api/v1/orders/{id}/split`

```json
{
  "line_refs": ["L2", "L3"],
  "local_number": null,
  "notes": null,
  "event_id": "optional-uuid"
}
```

Response: `201`

```json
{
  "parent": { "...order..." },
  "child": { "...order...", "parent_order_id": <id padre> }
}
```

---

## `PATCH /api/v1/orders/{id}`

Campos: `user_ref`, `customer_ref`, `notes`, `tip`, `local_number` (+ `event_id` opcional).  
Solo owner · status editable (`open`/`draft`/`sent`/`ready`).

---

## Errores frecuentes

| `error` | HTTP |
|---------|------|
| `unauthorized` | 401 |
| `not_owner` | 403 |
| `order_not_found` / `line_not_found` | 404 |
| `event_id_required` / `event_type_invalid` / `amount_invalid` / `reason_required` / `product_ref_required` / `line_refs_required` / `customer_required_for_partial` | 400 |
| `order_not_editable` / `use_modify_not_cancel` / `balance_not_zero` | 409 |

Cuerpo: `{"error":"<code>"}`.

---

## Fuera de este contrato

Inventario · Kardex · FE · transferencias · compras · `/api/eposone/*` session APIs.

---

## Criterio para P2 (Hito 4)

APK offline-first: cola local de eventos → sync a estos endpoints con el Bearer del Hito 1.  
No inventar tipos de evento ni paths.
