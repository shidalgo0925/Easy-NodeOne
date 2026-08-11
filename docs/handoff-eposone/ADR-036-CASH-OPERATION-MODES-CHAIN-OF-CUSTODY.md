# ADR-036 — Modos de operación de caja y cadena de custodia

| Campo | Valor |
|-------|--------|
| Estado | **Propuesto / alineado EP1** — 10 ago 2026 |
| Origen EP1 | Repo EPosOne · commit `66aea96` · `Doc/ADR-036-CASH-OPERATION-MODES-CHAIN-OF-CUSTODY.md` |
| Ámbito | EN1 (SoT Connected) + EPosOne APK (operación) |
| Relación | Amplía [ADR-009](ADR-009-EN1-CAJA-CENTRO-COBRO.md) · [ADR-006](ADR-006-EPOSONE-OPERATION-VS-ADMIN.md) · Cash Shift HTTP v1.0 |
| Delta HTTP | [`EN1_EPOSONE_CASH_SHIFT_MODE_B_DELTA.md`](EN1_EPOSONE_CASH_SHIFT_MODE_B_DELTA.md) |
| Implementación EN1 | **Pendiente GO** — modo B bloqueado en EP1 hasta este delta |

> Si el texto canónico en EP1 diverge, prevalece el ADR-036 del repo EP1 tras reconciliación explícita. Este documento es la **copia de trabajo EN1** para desbloquear el delta.

---

## Contexto

EP1 cerró P0 de turnos Connected (open/close → EN1 vía `enqueueAndKickSync`) sobre el contrato Cash Shift **v1.0**, que asume un modelo simple: **un cajero activo por turno de una caja**.

Algunas operaciones (cambio de cajero mid-turno, custodia del efectivo, handovers auditables) no caben en ese modelo sin romper v1.0. EP1 introdujo dos **modos de operación de caja**; el modo cadena de custodia queda **bloqueado en APK** hasta que EN1 publique política + API.

---

## Decisión

Toda organización Connected opera cada **Caja** (`register`) bajo un modo:

| Modo | Código | Default | Resumen |
|------|--------|---------|---------|
| **Simple** | `SIMPLE` | **Sí** | Un cajero por turno. Open → cobrar/movimientos → arqueo → close. Sin handover mid-turno. = comportamiento Cash Shift HTTP **v1.0**. |
| **Cadena de custodia** | `CHAIN_OF_CUSTODY` | No | El efectivo/cajón tiene **custodio** explícito. Cambio de cajero = evento de handover (entrega → aceptación), no “editar cajero” silencioso. Cierre solo por quien tiene custodia (o supervisor con override auditado). |

### Principios

1. **Default = SIMPLE** — cero regresión para P0 / Connected actual.
2. **EN1 es SoT del modo** — la APK lee el modo (bootstrap / register / org setting); no inventa política local que contradiga EN1.
3. **v1.0 sigue válido** para SIMPLE; CHAIN_OF_CUSTODY es **v1.1+** (delta), no reinterpretación de v1.0.
4. **Standalone** — fuera de alcance de sync de turnos a EN1 (spec §0); modo B no aplica a push EN1.
5. **Movimientos se ven por turno** — atribución al turno abierto, no “solo mi cajero” como filtro duro de dominio (la UI puede filtrar; el ledger es del turno).

### Dónde vive la config (EN1)

| Nivel | Uso |
|-------|-----|
| **Organización** | Default de modo para cajas nuevas |
| **Caja (`register`)** | Override opcional por caja (cadena puede activar solo “Caja principal”) |

Nombre canónico propuesto (implementación futura):

```text
cash_operation_mode = SIMPLE | CHAIN_OF_CUSTODY
```

(org default + opcional por `register_ref`)

---

## Modo SIMPLE (congelado = v1.0)

```text
Abrir (cashier_contact_id)
  → Cobrar / movimientos de tesorería (BO; POS según contrato)
  → Arqueo + Cerrar (cashier_contact_id + counted_amount)
```

- Sin handover.
- Cambio de cajero mid-turno: **no** en POS v1; BO puede tener flujo auditado aparte (ya previsto en spec §5).
- EP1 puede implementar y sincronizar **hoy** contra EN1 sin este ADR implementado en código (ya lo hace).

---

## Modo CHAIN_OF_CUSTODY (modo B) — contrato conceptual

```text
Abrir → Custodio = cajero A
  → Operación (pedidos/pagos/movimientos del turno)
  → Handover: A entrega → B acepta (o rechaza)
  → Custodio = B
  → …
  → Solo custodio (o supervisor override) cierra con arqueo
```

### Eventos mínimos

| Evento | Quién | Efecto |
|--------|-------|--------|
| `custody.opened` | Cajero A al abrir turno | Custodio = A |
| `custody.handover_offered` | Custodio actual | Pendiente aceptación por B |
| `custody.handover_accepted` | Cajero B | Custodio = B; oferta cerrada |
| `custody.handover_rejected` | Cajero B | Custodio sigue A |
| `custody.closed` | Custodio (o override) al close | Fin turno |

Cada evento: `shift_id`, `from_cashier_contact_id`, `to_cashier_contact_id` (si aplica), timestamps, `actor_cashier_contact_id`, motivo/notas opcionales.

### Reglas

- No hay dos custodios a la vez.
- Pagos/movimientos de caja en POS (si se exponen) requieren actor = custodio **o** política explícita de “cajero ayudante” (fuera de MVP modo B).
- Override supervisor: solo BO EN1 o rol autorizado; queda en auditoría; no es el camino feliz EP1.
- Arqueo / `counted_amount`: quien cierra debe ser el custodio vigente (salvo override).

---

## Consecuencias

| + | − |
|---|---|
| EP1 puede shippear SIMPLE sin esperar modo B | Modo B exige delta HTTP + OCC/BO |
| Cadena de custodia auditable para retail multi-cajero | Más estados y UX en tablet |
| Alineado ADR-006 (EN1 admin / POS opera) | Riesgo si se “apaga” modo B a medias en una caja |

### No implica (este ADR)

- Inventario / tragos / merma.
- Meter cierres dentro de pantalla Pedidos.
- Cambiar Cash Shift HTTP **v1.0** para clientes SIMPLE.
- Paridad Standalone ↔ EN1.

---

## Plan de adopción

| Paso | Dueño | Estado |
|------|-------|--------|
| ADR-036 en EP1 | EP1 | Hecho (`66aea96`) |
| ADR-036 en EN1 (este doc) | EN1 | **Hecho (docs)** |
| Delta contrato modo B | EN1 | [`EN1_EPOSONE_CASH_SHIFT_MODE_B_DELTA.md`](EN1_EPOSONE_CASH_SHIFT_MODE_B_DELTA.md) — **borrador** |
| Setting + APIs + OCC | EN1 | Pendiente **GO** implementación |
| Cableado modo B en APK | EP1 | Bloqueado hasta EN1 publique delta |

---

## Criterio de hecho (modo B Connected)

1. Org/caja en `CHAIN_OF_CUSTODY`; bootstrap/APK conoce el modo.
2. Open → custodio A visible en EN1 y EP1.
3. Handover A→B (offer + accept) queda en ledger; B puede cerrar.
4. Cierre sin ser custodio → rechazo (salvo override BO auditado).
5. SIMPLE sigue pasando E2E open/close sin regresiones.

---

## Referencias

- [`EN1_EPOSONE_CASH_SHIFT_HTTP_CONTRACT.md`](EN1_EPOSONE_CASH_SHIFT_HTTP_CONTRACT.md) v1.0  
- [`EN1_EPOSONE_CASH_SHIFT_SPEC_V1.md`](EN1_EPOSONE_CASH_SHIFT_SPEC_V1.md)  
- [`EPOSONE_EP1_CASH_SHIFT_CONNECTED_HANDOFF.md`](EPOSONE_EP1_CASH_SHIFT_CONNECTED_HANDOFF.md)  
- [`EPOSONE_EN1_HITO2_5_CASHIER_CONTRACT.md`](EPOSONE_EN1_HITO2_5_CASHIER_CONTRACT.md)  
- [`ADR-009-EN1-CAJA-CENTRO-COBRO.md`](ADR-009-EN1-CAJA-CENTRO-COBRO.md)  
- [`ADR-006-EPOSONE-OPERATION-VS-ADMIN.md`](ADR-006-EPOSONE-OPERATION-VS-ADMIN.md)  
