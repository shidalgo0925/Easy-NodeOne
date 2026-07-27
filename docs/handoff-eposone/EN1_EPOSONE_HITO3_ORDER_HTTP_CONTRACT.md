# EPosOne ↔ EN1 — Hito 3B: Contrato HTTP Order Domain

| Campo | Valor |
|-------|--------|
| Estado | **CONGELADO / PUBLICADO** — 14 jul 2026 · Hito **3B** handoff oficial |
| Versión dominio | **Order Domain v1.0** — **CONGELADA** |
| Commit código EN1 | **`36a0eb1`** (`develop`) · tag `eposone-order-domain-v1.0` |
| Spec dominio | [`EN1_EPOSONE_ORDER_DOMAIN_SPEC_V1.md`](EN1_EPOSONE_ORDER_DOMAIN_SPEC_V1.md) |
| Base URL Dev | `https://appdev.easynodeone.com` |
| Destino APK | Copiar a `Doc/` del repo EPosOne (junto con la Spec) |
| Audiencia | **P2** — cablear Bearer + `/api/v1/orders*` **sin inventar** |

Cambios = **v1.1+** + GO arquitectura. No reinterpretar.

---

## 1. Headers obligatorios

| Header | Valor | Obligatorio |
|--------|--------|-------------|
| `Authorization` | `Bearer <access_token>` | **Sí** (POS). Token = `access_token` de `POST /api/v1/devices/register` |
| `Content-Type` | `application/json` | **Sí** en POST/PATCH con body |
| `Accept` | `application/json` | Recomendado |

### Device Token

- Se obtiene en Hito 1: `POST /api/v1/devices/register` + `X-EN1-Provisioning-Code`.
- Se reutiliza para `/api/v1/devices/config`, `/api/v1/devices/bootstrap` y **`/api/v1/orders*`**.
- **No** es JWT de usuario web. **No** sirve contra `/api/eposone/*` (`@login_required` → 401).

Ejemplo:

```http
Authorization: Bearer eyJhbGciOi..._ejemplo_token_dispositivo
Content-Type: application/json
```

---

## 2. Códigos HTTP

| Código | Significado en este contrato |
|--------|------------------------------|
| **200** | OK — lectura o mutación sin creación de recurso nuevo (GET, PATCH, events) |
| **201** | Created — alta de pedido, pago o split |
| **400** | Request inválido (`event_id_required`, `amount_invalid`, `product_ref_required`, …) |
| **401** | No autenticado — falta/ inválido Bearer |
| **403** | Prohibido — `not_owner`, `device_inactive`, `forbidden` |
| **404** | No encontrado — `order_not_found`, `line_not_found`, `lines_not_found` |
| **409** | Conflicto de negocio — `order_not_editable`, `use_modify_not_cancel`, `balance_not_zero` |
| **500** | Error interno del servidor (no esperado; reportar a EN1 con `event_id` / body) |

Cuerpo de error (salvo 500 genérico):

```json
{ "error": "<code>" }
```

| `error` (ejemplos) | HTTP |
|--------------------|------|
| `unauthorized` | 401 |
| `not_owner` / `forbidden` / `device_inactive` | 403 |
| `order_not_found` / `line_not_found` / `lines_not_found` | 404 |
| `event_id_required` / `event_type_invalid` / `amount_invalid` / `reason_required` / `product_ref_required` / `line_refs_required` / `customer_required_for_partial` | 400 |
| `order_not_editable` / `use_modify_not_cancel` / `balance_not_zero` | 409 |

---

## 3. Endpoints (índice)

| Método | Path |
|--------|------|
| `POST` | `/api/v1/orders` |
| `GET` | `/api/v1/orders` |
| `GET` | `/api/v1/orders/{id}` |
| `PATCH` | `/api/v1/orders/{id}` |
| `POST` | `/api/v1/orders/{id}/events` |
| `POST` | `/api/v1/orders/{id}/payments` |
| `POST` | `/api/v1/orders/{id}/split` |

---

## 4. Ownership (recordatorio)

| Acción | Quién |
|--------|--------|
| Patch / events (no pago) / split | Solo **owner** (`owner_device_uuid` = UUID del device del token) |
| Payments / etapa cobro | Cualquier Device Bearer de la **misma org** |
| `table_ref` null | Cada POST = Order nuevo |
| `table_ref` set | Un abierto; POST reutiliza |
| Split | Hijo hereda ownership del padre |

---

## 5. `POST /api/v1/orders`

### Request

```http
POST /api/v1/orders HTTP/1.1
Host: appdev.easynodeone.com
Authorization: Bearer <device_token>
Content-Type: application/json
```

```json
{
  "local_number": "T-12",
  "table_ref": null,
  "user_ref": "cajero1",
  "customer_ref": null,
  "notes": null,
  "tip": 0,
  "event_id": "550e8400-e29b-41d4-a716-446655440001"
}
```

### Response `201`

```json
{
  "order": {
    "id": 12,
    "en1_number": "EN1-5-12",
    "local_number": "T-12",
    "organization_id": 5,
    "branch_ref": "centro",
    "pos_ref": "pos-centro",
    "register_ref": "caja-01",
    "owner_device_uuid": "a1b2c3d4-uuid-del-dispositivo",
    "owner_pos_ref": "pos-centro",
    "user_ref": "cajero1",
    "customer_ref": null,
    "table_ref": null,
    "status": "open",
    "payment_status": "unpaid",
    "financially_closed": false,
    "subtotal": 0.0,
    "tax": 0.0,
    "discount": 0.0,
    "tip": 0.0,
    "total": 0.0,
    "amount_paid": 0.0,
    "notes": null,
    "parent_order_id": null,
    "opened_at": "2026-07-14T16:55:41.116487Z",
    "updated_at": "2026-07-14T16:55:41.116487Z",
    "items": [],
    "payments": [],
    "events": [
      {
        "event_id": "550e8400-e29b-41d4-a716-446655440001",
        "type": "pedido.creado",
        "sequence": 1,
        "occurred_at": "2026-07-14T16:55:41.116487Z",
        "actor_user_ref": "cajero1",
        "actor_device_uuid": "a1b2c3d4-uuid-del-dispositivo",
        "payload": { "local_number": "T-12", "table_ref": null }
      }
    ]
  }
}
```

Con `table_ref` y pedido abierto existente → mismo shape (pedido reutilizado; HTTP puede ser 201 con el order existente).

---

## 6. `GET /api/v1/orders`

### Request

```http
GET /api/v1/orders?status=open&limit=50 HTTP/1.1
Host: appdev.easynodeone.com
Authorization: Bearer <device_token>
Accept: application/json
```

Query opcionales: `status`, `table_ref`, `limit` (max 200).

### Response `200`

```json
{
  "orders": [
    {
      "id": 12,
      "en1_number": "EN1-5-12",
      "status": "open",
      "total": 2.5,
      "items": [ ... ],
      "payments": []
    }
  ],
  "count": 1
}
```

---

## 7. `GET /api/v1/orders/{id}`

### Request

```http
GET /api/v1/orders/12?include=events HTTP/1.1
Host: appdev.easynodeone.com
Authorization: Bearer <device_token>
Accept: application/json
```

### Response `200`

```json
{
  "order": {
    "id": 12,
    "en1_number": "EN1-5-12",
    "status": "open",
    "total": 2.5,
    "items": [
      {
        "id": 1,
        "line_ref": "L1",
        "product_ref": "ib-agua",
        "qty": 2.0,
        "unit_price": 1.25,
        "tax": 0.0,
        "discount": 0.0,
        "notes": null,
        "line_status": "pending"
      }
    ],
    "payments": [],
    "events": [ ... ]
  }
}
```

Sin `include=events` → `events` omitido.

### Response `404`

```json
{ "error": "order_not_found" }
```

---

## 8. `PATCH /api/v1/orders/{id}`

### Request

```http
PATCH /api/v1/orders/12 HTTP/1.1
Host: appdev.easynodeone.com
Authorization: Bearer <device_token>
Content-Type: application/json
```

```json
{
  "user_ref": "cajero2",
  "notes": "Sin cebolla",
  "tip": 0.5,
  "local_number": "T-12b",
  "customer_ref": null,
  "event_id": "550e8400-e29b-41d4-a716-446655440010"
}
```

Campos admitidos: `user_ref`, `customer_ref`, `notes`, `tip`, `local_number`, `event_id` (opcional).

### Response `200`

```json
{
  "order": {
    "id": 12,
    "user_ref": "cajero2",
    "notes": "Sin cebolla",
    "tip": 0.5,
    "local_number": "T-12b",
    "total": 3.0,
    "status": "open",
    "items": [ ... ],
    "payments": []
  }
}
```

### Response `403` / `409`

```json
{ "error": "not_owner" }
```

```json
{ "error": "order_not_editable" }
```

---

## 9. `POST /api/v1/orders/{id}/events`

### Request — agregar producto

```http
POST /api/v1/orders/12/events HTTP/1.1
Host: appdev.easynodeone.com
Authorization: Bearer <device_token>
Content-Type: application/json
```

```json
{
  "event_id": "550e8400-e29b-41d4-a716-446655440020",
  "type": "producto.agregado",
  "actor_user_ref": "cajero1",
  "payload": {
    "line_ref": "L1",
    "product_ref": "ib-agua",
    "qty": 2,
    "unit_price": 1.25,
    "tax": 0,
    "discount": 0,
    "notes": null
  }
}
```

`event_id` **obligatorio** e idempotente.

### Response `200`

```json
{
  "order": {
    "id": 12,
    "subtotal": 2.5,
    "tax": 0.0,
    "discount": 0.0,
    "tip": 0.0,
    "total": 2.5,
    "items": [
      {
        "id": 1,
        "line_ref": "L1",
        "product_ref": "ib-agua",
        "qty": 2.0,
        "unit_price": 1.25,
        "tax": 0.0,
        "discount": 0.0,
        "notes": null,
        "line_status": "pending"
      }
    ],
    "events": [
      {
        "event_id": "550e8400-e29b-41d4-a716-446655440020",
        "type": "producto.agregado",
        "sequence": 2,
        "occurred_at": "2026-07-14T16:56:01.000000Z",
        "actor_user_ref": "cajero1",
        "actor_device_uuid": "a1b2c3d4-uuid-del-dispositivo",
        "payload": {
          "line_ref": "L1",
          "product_ref": "ib-agua",
          "qty": 2,
          "unit_price": 1.25
        }
      }
    ]
  }
}
```

### Tipos `type` permitidos

| type | payload |
|------|---------|
| `pedido.actualizado` | `user_ref`, `notes`, `tip` |
| `producto.agregado` | `line_ref`, `product_ref`, `qty`, `unit_price`, `tax`, `discount`, `notes` |
| `producto.eliminado` | `line_ref` |
| `cantidad.modificada` | `line_ref`, `qty` |
| `pedido.enviado` | `{}` |
| `linea.lista` | `line_ref` |
| `pedido.listo` | `{}` |
| `linea.entregada` | `line_ref` |
| `pedido.entregado` | `{}` |
| `linea.cancelada` | `line_ref` |
| `pedido.anulado` | `reason` |
| `pedido.devuelto` | `reason` |
| `pedido.cobrado` | `{}` (saldo 0) |

Preferir `/payments` y `/split` para cobro y división (en lugar de inventar payloads en events).

### Response `400`

```json
{ "error": "event_id_required" }
```

---

## 10. `POST /api/v1/orders/{id}/payments`

### Request

```http
POST /api/v1/orders/12/payments HTTP/1.1
Host: appdev.easynodeone.com
Authorization: Bearer <device_token>
Content-Type: application/json
```

```json
{
  "amount": 2.5,
  "method": "cash",
  "kind": "payment",
  "currency": "USD",
  "tip": 0,
  "reference": null,
  "customer_ref": null,
  "payment_ref": "pay-local-001",
  "event_id": "550e8400-e29b-41d4-a716-446655440030"
}
```

| `kind` | Regla |
|--------|--------|
| `payment` | Cobro normal |
| `deposit` / `partial` / `abono` | Requiere `customer_ref` → CxC |

### Métodos de pago canónicos

| `method` | Etiqueta | Referencia |
|----------|----------|------------|
| `cash` | Efectivo | No |
| `visa` | Visa | Sí |
| `mastercard` | Mastercard | Sí |
| `clave` | Clave | Sí |
| `yappy` | Yappy | Sí |
| `ach` | ACH | Sí |
| `voucher` | Vale | No |
| `customer_credit` | Crédito Cliente | No |
| `gift_card` | Gift Card | Sí |
| `other` | Otros | No |

Compatibilidad EN1:

- Acepta el método en `method`, `method_key`, `payment_method`, `payment_type`,
  `forma_pago` o `tipo_pago`.
- Normaliza etiquetas y alias (`Efectivo`, `Yappy`, `tarjeta`, `card`,
  `Crédito Cliente`, etc.).
- `card` se conserva como método legacy genérico; P2 debe preferir
  `visa`, `mastercard` o `clave`.
- Si un método que exige referencia llega sin ella, EN1 persiste
  `NR-{payment_ref}` para no perder el cobro. P2 debe enviar la referencia real.

### Propina

P2 debe enviar `tip` (también se acepta `propina`) antes o junto con el pago.
EN1 recalcula el total antes de validar el saldo.

Como compatibilidad, si el monto excede el saldo exactamente por una propina aún
no sincronizada, EN1 infiere la diferencia con un límite de 50% sobre la base.
Esto evita perder el pago, pero no reemplaza el envío explícito de `tip`.

Ejemplo Yappy:

```json
{
  "amount": 14.12,
  "method": "yappy",
  "tip": 1.28,
  "reference": "YAPPY-839201",
  "kind": "payment",
  "currency": "USD",
  "payment_ref": "r000002-yappy-01",
  "event_id": "f8eb6746-0d44-4e30-bd84-bfce037d16db"
}
```

### Pago mixto

Un pedido admite pagos 1:N. P2 debe enviar **un POST por componente**, cada uno
con `payment_ref` y `event_id` únicos. Ejemplo:

```text
POST /payments  { "amount": 5.00, "method": "cash", ... }
POST /payments  { "amount": 9.12, "method": "yappy", "reference": "...", ... }
```

Solo efectivo admite cálculo de vuelto en la APK. EN1 registra el monto aplicado
al pedido; el vuelto no se registra como pago adicional.

### Response `201` (cierre completo)

```json
{
  "order": {
    "id": 12,
    "total": 2.5,
    "amount_paid": 2.5,
    "payment_status": "paid",
    "financially_closed": true,
    "payments": [
      {
        "id": 1,
        "payment_ref": "pay-local-001",
        "amount": 2.5,
        "method": "cash",
        "kind": "payment",
        "currency": "USD",
        "created_at": "2026-07-14T16:57:00.000000Z"
      }
    ],
    "items": [ ... ]
  }
}
```

### Response `400`

```json
{ "error": "customer_required_for_partial" }
```

---

## 11. `POST /api/v1/orders/{id}/split`

### Request

```http
POST /api/v1/orders/12/split HTTP/1.1
Host: appdev.easynodeone.com
Authorization: Bearer <device_token>
Content-Type: application/json
```

```json
{
  "line_refs": ["L2"],
  "local_number": "T-12-B",
  "notes": null,
  "event_id": "550e8400-e29b-41d4-a716-446655440040"
}
```

### Response `201`

```json
{
  "parent": {
    "id": 12,
    "en1_number": "EN1-5-12",
    "total": 10.0,
    "owner_device_uuid": "a1b2c3d4-uuid-del-dispositivo",
    "items": [
      { "line_ref": "L1", "product_ref": "x", "qty": 1.0, "unit_price": 10.0, "line_status": "pending" }
    ]
  },
  "child": {
    "id": 13,
    "en1_number": "EN1-5-13",
    "parent_order_id": 12,
    "total": 5.0,
    "owner_device_uuid": "a1b2c3d4-uuid-del-dispositivo",
    "table_ref": null,
    "items": [
      { "line_ref": "L2", "product_ref": "y", "qty": 1.0, "unit_price": 5.0, "line_status": "pending" }
    ]
  }
}
```

---

## 12. Ejemplo curl (Itsmo Dev)

```bash
TOKEN='<access_token>'

curl -sS -X POST 'https://appdev.easynodeone.com/api/v1/orders' \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"local_number":"DEMO-1","user_ref":"cajero1"}'

curl -sS -X POST "https://appdev.easynodeone.com/api/v1/orders/12/events" \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"event_id":"'"$(uuidgen)"'","type":"producto.agregado","payload":{"line_ref":"L1","product_ref":"ib-agua","qty":2,"unit_price":1.25}}'

curl -sS -X POST "https://appdev.easynodeone.com/api/v1/orders/12/payments" \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"amount":2.5,"method":"cash","kind":"payment"}'
```

---

## 13. Fuera de contrato

Inventario · Kardex · FE · `/api/eposone/products` · inventar `event.type`.

---

## 14. Confirmación oficial

| Ítem | Valor |
|------|--------|
| Order Domain | **v1.0 CONGELADA** |
| Contrato HTTP | **v1.0 CONGELADO / PUBLICADO (Hito 3B)** |
| Código EN1 | tag `eposone-order-domain-v1.0` · `36a0eb1` |
| Acción P2 | Quitar stubs · cablear HTTP real |
