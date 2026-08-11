# EPosOne ↔ EN1 — Delta Cash Shift modo B (CHAIN_OF_CUSTODY)

| Campo | Valor |
|-------|--------|
| Estado | **MVP implementado en Dev** — 10 ago 2026 · v1.1 additive |
| Versión objetivo | Cash Shift HTTP **v1.1** (additive) |
| ADR | [`ADR-036-CASH-OPERATION-MODES-CHAIN-OF-CUSTODY.md`](ADR-036-CASH-OPERATION-MODES-CHAIN-OF-CUSTODY.md) |
| Base | [`EN1_EPOSONE_CASH_SHIFT_HTTP_CONTRACT.md`](EN1_EPOSONE_CASH_SHIFT_HTTP_CONTRACT.md) **v1.0** (SIMPLE; sin cambios breaking) |
| Audiencia | EN1 (implementación) · EP1 (desbloqueo modo B) |

**Regla:** v1.0 sigue válido. Este delta **solo** aplica si `cash_operation_mode = CHAIN_OF_CUSTODY` en settings de la org (default SIMPLE).  
**SIMPLE:** ignorar endpoints/campos de custody; comportamiento v1.0.

**Dev EN1 (hecho):**
- Setting `eposone_settings.cash_operation_mode`
- Bootstrap `config.register.cash_operation_mode`
- Columnas custodio + tabla `core_cash_custody_handover`
- Endpoints handover offer/accept/reject
- Close rechaza si actor ≠ custodio (`custody_required`) o hay pending
- BO detalle turno muestra custodio / modo


---

## 0. Qué desbloquea

EP1 tiene modo B bloqueado hasta que EN1 exponga:

1. Lectura del modo (bootstrap / register).
2. Custodio actual del turno.
3. Handover offer / accept / reject.
4. Close rechazado si actor ≠ custodio (salvo override BO).

---

## 1. Config — lectura (Device Bearer)

### 1.1 Extensión bootstrap (preferida)

En `GET /api/v1/devices/bootstrap` (o payload de register ya usado por EP1), añadir por caja del device:

```json
{
  "register": {
    "register_ref": "caja-1",
    "cash_operation_mode": "SIMPLE"
  }
}
```

| Campo | Valores | Default si ausente |
|-------|---------|---------------------|
| `cash_operation_mode` | `SIMPLE` \| `CHAIN_OF_CUSTODY` | `SIMPLE` |

### 1.2 Alternativa

`GET /api/v1/cash/operation-mode` → `{ "cash_operation_mode": "SIMPLE" }`  
(Solo si no se quiere tocar bootstrap; preferir §1.1.)

---

## 2. Turno actual — custodio

Extender respuesta de:

- `GET /api/v1/cash/shifts/current`
- `GET /api/v1/cash/shifts/{shift_id}`
- `POST /api/v1/cash/shifts` (open)
- `POST /api/v1/cash/shifts/{shift_id}/close`

campos **adicionales** (modo B; en SIMPLE pueden omitirse o ir null):

```json
{
  "shift": {
    "id": 11,
    "status": "open",
    "cashier_contact_id": 8,
    "custodian_cashier_contact_id": 8,
    "custodian_cashier_name": "Alberto Cajero",
    "cash_operation_mode": "CHAIN_OF_CUSTODY",
    "pending_handover": null
  }
}
```

| Campo | Significado |
|-------|-------------|
| `custodian_cashier_contact_id` | Quién tiene el cajón ahora |
| `pending_handover` | Objeto oferta pendiente o `null` |

`pending_handover` ejemplo:

```json
{
  "handover_id": "hov_…",
  "from_cashier_contact_id": 8,
  "to_cashier_contact_id": 12,
  "offered_at": "2026-08-10T15:00:00Z",
  "status": "pending"
}
```

---

## 3. Endpoints nuevos (solo CHAIN_OF_CUSTODY)

Prefijo: `/api/v1/cash/shifts/{shift_id}/…`  
Auth: Device Bearer · misma caja del device · Connected.

| Método | Ruta | Acción |
|--------|------|--------|
| `POST` | `.../custody/handover` | Custodio ofrece handover a `to_cashier_contact_id` |
| `POST` | `.../custody/handover/{handover_id}/accept` | Destino acepta |
| `POST` | `.../custody/handover/{handover_id}/reject` | Destino rechaza |
| `GET` | `.../custody/events` | (Opcional MVP+) historial de custody del turno |

### 3.1 Offer

```http
POST /api/v1/cash/shifts/11/custody/handover
Authorization: Bearer <device>
Content-Type: application/json

{
  "from_cashier_contact_id": 8,
  "to_cashier_contact_id": 12,
  "notes": "Cambio de turno tarde"
}
```

**200** — handover `pending`.  
**409** — ya hay pending; actor no es custodio; turno no `open`.  
**400** — ids inválidos / mismo from=to.

### 3.2 Accept / Reject

```http
POST /api/v1/cash/shifts/11/custody/handover/hov_…/accept
{ "cashier_contact_id": 12 }

POST /api/v1/cash/shifts/11/custody/handover/hov_…/reject
{ "cashier_contact_id": 12, "notes": "No puedo" }
```

Accept → `custodian_cashier_contact_id = 12`.  
Reject → custodio sin cambio; pending limpio.

### 3.3 Close (regla modo B)

`POST .../close` **v1.0** se mantiene.

Si modo = `CHAIN_OF_CUSTODY`:

| Condición | Resultado |
|-----------|-----------|
| `cashier_contact_id` del body = custodio actual | OK (v1.0) |
| ≠ custodio y no override | **409** `custody_required` |
| Override supervisor | **Solo BO** (`/api/eposone/...`), no Device API en MVP |

Códigos de error nuevos (propuestos):

| code | HTTP |
|------|------|
| `cash_operation_mode_mismatch` | 409 |
| `custody_required` | 409 |
| `handover_pending` | 409 |
| `handover_not_found` | 404 |
| `not_handover_target` | 403 |
| `not_custodian` | 403 |

---

## 4. Movimientos de tesorería desde POS (opcional MVP+)

Spec v1.0: movimiento manual = BO.

Si modo B requiere cash-in/out en tablet **antes** del close:

| Método | Ruta | Nota |
|--------|------|------|
| `POST` | `/api/v1/cash/shifts/{shift_id}/movements` | `type`, `amount`, `cashier_contact_id` (= custodio), `notes` |
| `GET` | `/api/v1/cash/shifts/{shift_id}/movements` | Ledger del **turno** (no “solo mi cajero”) |

Fuera del MVP mínimo de handover si EP1 aún no lo exige para desbloquear UI modo B.

---

## 5. Fuera de este delta

- Breaking changes a open/close v1.0 para SIMPLE.
- Historial global de cierres para POS (handoff Connected: fase aparte).
- Standalone push a EN1.
- Inventario / Pedidos UI.

---

## 6. Criterio de hecho (desbloqueo EP1)

- [ ] Bootstrap (o endpoint) devuelve `cash_operation_mode`
- [ ] SIMPLE: E2E open/close idéntico a v1.0
- [ ] CHAIN_OF_CUSTODY: offer → accept cambia custodio; close por no-custodio → 409
- [ ] Eventos custody visibles en BO/OCC (mínimo detalle de turno)
- [ ] Doc + tag/versión **v1.1** publicada → EP1 quita bloqueo modo B

---

## 7. Orden de implementación EN1 (cuando haya GO código)

1. Setting org/register `cash_operation_mode` (default SIMPLE).  
2. Exponer en bootstrap.  
3. Persistir `custodian_*` en `CoreCashShift` (+ tabla/eventos handover).  
4. Endpoints handover + reglas close.  
5. OCC/detalle turno: custodio + timeline custody.  
6. Congelar este doc como v1.1 + handoff a EP1.
