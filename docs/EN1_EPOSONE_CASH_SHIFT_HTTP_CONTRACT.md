# EPosOne ↔ EN1 — Contrato HTTP Turnos de Caja (Cash Shift)

| Campo | Valor |
|-------|--------|
| Estado | **CONGELADO / PUBLICADO** — 24 jul 2026 · handoff P1→P2 |
| Versión | **Cash Shift HTTP v1.0** |
| Spec funcional | [`EN1_EPOSONE_CASH_SHIFT_SPEC_V1.md`](EN1_EPOSONE_CASH_SHIFT_SPEC_V1.md) |
| Base URL Dev | `https://appdev.easynodeone.com` |
| Destino APK | Copiar a `Doc/` del repo EPosOne |
| Audiencia | **Prog2** — cablear Bearer + `/api/v1/cash/shifts*` **sin inventar** |
| Relacionado | Hito 2.5 cajero · ADR-009 · Order Domain HTTP |

Cambios = **v1.1+** + GO arquitectura. No reinterpretar.

**Importante:** `/api/eposone/cash/shifts*` (sesión BO `@login_required`) **no** es este contrato. La tablet **solo** usa `/api/v1/cash/*` con Device Token.

---

## 1. Headers obligatorios

| Header | Valor | Obligatorio |
|--------|--------|-------------|
| `Authorization` | `Bearer <access_token>` | **Sí** (POS). Mismo token que bootstrap/orders (`POST /api/v1/devices/register`) |
| `Content-Type` | `application/json` | **Sí** en POST con body |
| `Accept` | `application/json` | Recomendado |
| `Idempotency-Key` | UUID estable del intento de apertura | Recomendado en `POST /shifts` (equivale a `client_shift_id`) |

### Device Token

- Se obtiene en Hito 1: `POST /api/v1/devices/register` + código de provisionamiento.
- Se reutiliza para `/api/v1/devices/*`, `/api/v1/orders*` y **`/api/v1/cash/*`**.
- **No** es JWT de usuario web. **No** sirve contra `/api/eposone/*` (`@login_required` → 401).

La caja (`register_ref`) la infiere EN1 del device. La APK **no** envía `register_ref` / `caja_id` en el body.

---

## 2. Códigos HTTP

| Código | Significado |
|--------|-------------|
| **200** | OK — lectura, cierre, o apertura idempotente (mismo `client_shift_id`) |
| **201** | Created — turno abierto nuevo |
| **400** | Request inválido |
| **401** | Bearer faltante/inválido |
| **403** | `device_inactive` / `forbidden` / `device_without_register` |
| **404** | `shift_not_found` / `cashier_not_found` |
| **409** | Conflicto de negocio (`shift_already_open`, `cashier_inactive`, …) |

Cuerpo de error:

```json
{ "error": "<code>" }
```

| `error` | HTTP |
|---------|------|
| `unauthorized` | 401 |
| `device_inactive` / `forbidden` / `device_without_register` | 403 |
| `shift_not_found` / `cashier_not_found` | 404 |
| `cashier_contact_id_required` / `cashier_contact_id_invalid` / `opening_float_invalid` / `counted_amount_required` / `counted_amount_invalid` / `opened_at_invalid` / `closed_at_invalid` | 400 |
| `shift_already_open` / `cashier_inactive` / `client_shift_id_conflict` / `cash_shift_not_open` | 409 |

---

## 3. Endpoints (índice)

| Método | Path | Uso |
|--------|------|-----|
| `GET` | `/api/v1/cash/shifts/current` | Turno abierto o en arqueo de **esta** caja; `shift: null` si no hay |
| `POST` | `/api/v1/cash/shifts` | Abrir turno |
| `GET` | `/api/v1/cash/shifts/{shift_id}` | Leer turno (misma caja del device) |
| `POST` | `/api/v1/cash/shifts/{shift_id}/close` | Cerrar (arqueo + close **en un paso**) |

No hay endpoint POS separado de “reconcile”. El BO sigue usando su UI (reconcile → close).

---

## 4. Shape `shift` (respuesta)

```json
{
  "shift_id": 11,
  "shift_number": 11,
  "client_shift_id": "550e8400-e29b-41d4-a716-446655440100",
  "caja_id": "caja-01",
  "caja_name": "Caja Principal",
  "register_ref": "caja-01",
  "cashier_contact_id": 8,
  "cashier_name": "Alberto Cajero",
  "status": "open",
  "opening_float": 100.0,
  "opening_balance": 100.0,
  "opened_at": "2026-07-24T12:00:00Z",
  "closed_at": null,
  "counted_amount": null,
  "expected_balance": 100.0,
  "closing_balance": null,
  "cash_variance": null,
  "closed_by_cashier_contact_id": null
}
```

| Campo | Notas |
|-------|--------|
| `shift_id` / `shift_number` | En v1.0 son el mismo entero EN1 (`core_cash_shift.id`) |
| `caja_id` | = `register_ref` de la unidad org tipo register |
| `status` | `open` · `reconciling` · `closed` |
| `opening_float` | Alias canónico POS; `opening_balance` ecoado por compat |
| Timestamps | UTC con sufijo `Z` |

---

## 5. `GET /api/v1/cash/shifts/current`

### Request

```http
GET /api/v1/cash/shifts/current HTTP/1.1
Host: appdev.easynodeone.com
Authorization: Bearer <device_token>
```

### Response `200` (con turno)

```json
{ "shift": { "shift_id": 11, "status": "open", "...": "..." } }
```

### Response `200` (sin turno)

```json
{ "shift": null }
```

---

## 6. `POST /api/v1/cash/shifts` — Abrir

### Request

```http
POST /api/v1/cash/shifts HTTP/1.1
Host: appdev.easynodeone.com
Authorization: Bearer <device_token>
Content-Type: application/json
Idempotency-Key: 550e8400-e29b-41d4-a716-446655440100
```

```json
{
  "client_shift_id": "550e8400-e29b-41d4-a716-446655440100",
  "cashier_contact_id": 8,
  "cashier_name": "Alberto Cajero",
  "opening_float": 100.0,
  "opened_at": "2026-07-24T12:00:00Z"
}
```

| Campo | Obligatorio | Notas |
|-------|-------------|--------|
| `cashier_contact_id` | **Sí** | Contacto `is_cashier=true` **activo** |
| `cashier_name` | No | Si falta, EN1 usa `display_name` del contacto |
| `opening_float` | No (default 0) | También acepta `opening_balance` |
| `opened_at` | No | ISO-8601; si falta = ahora UTC en servidor. Offline: mandar hora local→UTC del dispositivo |
| `client_shift_id` | Muy recomendado | UUID estable del intento; o header `Idempotency-Key` |

### Response `201` (nuevo)

```json
{
  "shift": {
    "shift_id": 11,
    "shift_number": 11,
    "client_shift_id": "550e8400-e29b-41d4-a716-446655440100",
    "caja_id": "caja-01",
    "caja_name": "Caja Principal",
    "register_ref": "caja-01",
    "cashier_contact_id": 8,
    "cashier_name": "Alberto Cajero",
    "status": "open",
    "opening_float": 100.0,
    "opening_balance": 100.0,
    "opened_at": "2026-07-24T12:00:00Z",
    "closed_at": null,
    "expected_balance": 100.0
  }
}
```

### Response `200` (idempotente)

Mismo body si se reenvía el mismo `client_shift_id` / `Idempotency-Key`.

### Errores típicos

- `409` `shift_already_open` — ya hay turno `open`/`reconciling` en esa caja (otro `client_shift_id`)
- `409` `cashier_inactive`
- `404` `cashier_not_found`

---

## 7. `POST /api/v1/cash/shifts/{shift_id}/close` — Cerrar

Un solo request: EN1 calcula esperado, registra contado, cierra (`status=closed`).

### Request

```http
POST /api/v1/cash/shifts/11/close HTTP/1.1
Host: appdev.easynodeone.com
Authorization: Bearer <device_token>
Content-Type: application/json
```

```json
{
  "cashier_contact_id": 8,
  "counted_amount": 351.37,
  "notes": "Cierre turno noche",
  "closed_at": "2026-07-24T22:15:00Z"
}
```

| Campo | Obligatorio | Notas |
|-------|-------------|--------|
| `cashier_contact_id` | **Sí** | Quien cierra (puede estar inactivo si ya existía al abrir offline) |
| `counted_amount` | **Sí** | Efectivo contado en cajón. Alias: `closing_float` |
| `notes` | No | Va a auditoría de evento |
| `closed_at` | No | ISO-8601 UTC; default = ahora servidor |

`cash_variance` / diferencia: **la calcula EN1** (`counted − expected`). La APK puede mostrarla en UI local pero **no** la impone.

### Response `200`

```json
{
  "shift": {
    "shift_id": 11,
    "shift_number": 11,
    "caja_id": "caja-01",
    "caja_name": "Caja Principal",
    "cashier_contact_id": 8,
    "cashier_name": "Alberto Cajero",
    "status": "closed",
    "opening_float": 100.0,
    "opened_at": "2026-07-24T12:00:00Z",
    "closed_at": "2026-07-24T22:15:00Z",
    "counted_amount": 351.37,
    "expected_balance": 351.37,
    "closing_balance": 351.37,
    "cash_variance": 0.0,
    "closed_by_cashier_contact_id": 8
  }
}
```

### Idempotencia de cierre

Si el turno **ya** está `closed`, EN1 responde `200` con el mismo shape (no error). Reintentos offline seguros.

### Errores típicos

- `404` `shift_not_found` — id inexistente o de **otra** caja
- `400` `counted_amount_required`

---

## 8. Idempotencia (offline)

| Operación | Mecanismo |
|-----------|-----------|
| Abrir | `client_shift_id` (body) **o** `Idempotency-Key` (header). Unique por org. Reintento → `200` + mismo `shift_id` |
| Cerrar | Si `status=closed` → `200` eco. No crear segundo turno |

La APK debe:

1. Generar `client_shift_id` al abrir en local.
2. Guardar `shift_id` / `shift_number` de la respuesta EN1 en la sesión local.
3. Encolar open/close y pushear con Device Token (mismo patrón que orders).

---

## 9. Ejemplo curl (Dev)

```bash
TOKEN='<access_token>'
CID='550e8400-e29b-41d4-a716-446655440100'

# Actual
curl -sS 'https://appdev.easynodeone.com/api/v1/cash/shifts/current' \
  -H "Authorization: Bearer $TOKEN"

# Abrir
curl -sS -X POST 'https://appdev.easynodeone.com/api/v1/cash/shifts' \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -H "Idempotency-Key: $CID" \
  -d '{"cashier_contact_id":8,"cashier_name":"Alberto Cajero","opening_float":100,"client_shift_id":"'"$CID"'"}'

# Cerrar
curl -sS -X POST 'https://appdev.easynodeone.com/api/v1/cash/shifts/11/close' \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"cashier_contact_id":8,"counted_amount":100,"notes":"demo"}'
```

---

## 10. Fuera de contrato v1.0

- Movimientos de tesorería HTTP (`cash_in` / `cash_out`) — BO o sync futuro
- Endpoint POS `reconcile` separado
- `shift_number` distinto de `shift_id`
- Sync Up `open_cash_shift` / `close_cash_shift` como sustituto de este HTTP (legacy; Prog2 usa HTTP)

---

## 11. Changelog

| Versión | Fecha | Cambio |
|---------|-------|--------|
| **v1.0** | 2026-07-24 | Contrato inicial Device Bearer: current / open / get / close one-shot · idempotencia `client_shift_id` |

---

## 12. Confirmación oficial

| Ítem | Valor |
|------|--------|
| Cash Shift HTTP | **v1.0 CONGELADO** |
| Código EN1 | rama `develop` · tag `eposone-cash-shift-http-v1.0` (tras commit) |
| Acción P2 | Encolar open/close · push Bearer · mapear `shift_id` a sesión local |

Confirmación P2 (cierra handoff docs):

```text
Documentos recibidos. Comienzo implementación HTTP turnos.
```
