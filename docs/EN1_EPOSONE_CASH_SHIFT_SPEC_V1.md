# EPosOne ↔ EN1 — Spec funcional Turnos de Caja (v1)

| Campo | Valor |
|-------|--------|
| Estado | **v1.0** — acompaña contrato HTTP congelado |
| Contrato HTTP | [`EN1_EPOSONE_CASH_SHIFT_HTTP_CONTRACT.md`](EN1_EPOSONE_CASH_SHIFT_HTTP_CONTRACT.md) |
| ADR | [`ADR-009-EN1-CAJA-CENTRO-COBRO.md`](ADR-009-EN1-CAJA-CENTRO-COBRO.md) |
| Cajero | [`EPOSONE_EN1_HITO2_5_CASHIER_CONTRACT.md`](EPOSONE_EN1_HITO2_5_CASHIER_CONTRACT.md) |

---

## 1. Quién abre / cierra

| Actor | Abre | Cierra | Notas |
|-------|------|--------|--------|
| **POS (tablet)** | Flujo normal | Flujo normal | Device Bearer · caja fija del device |
| **BO EN1** | Excepción / lab | Excepción / emergencia | Sesión admin · UI Turnos |
| **Sync Up legado** | Handler existe | Handler existe | Prog2 **no** lo usa para desbloqueo; usa HTTP v1 |

El device ya está provisionado a una **Caja** (`register_ref`). La APK no elige caja al abrir.

---

## 2. Flujo de turno (ADR-009)

```text
Abrir → Cobrar / movimientos → Arqueo → Cerrar
```

- Unidad operativa = **turno** (no hay entidad “cierre del día”).
- Esperado de cajón = **solo efectivo** (pagos cash OD + movimientos tesorería).
- En POS, arqueo + cierre son **un solo HTTP** (`POST .../close` con `counted_amount`).
- En BO, la UI puede mostrar arqueo (`reconciling`) y luego cerrar en dos pasos.

---

## 3. Offline

1. Cajero valida PIN **local** (Hito 2.5); no requiere EN1.
2. Apertura/cierre se encolan en la APK con `client_shift_id` / timestamps locales.
3. Al recuperar red: push HTTP con Device Token.
4. Si EN1 ya cerró el turno (BO) antes del sync de close: respuesta idempotente o conflicto según estado — la APK muestra conflicto, no descarta el evento.

Apertura online preferida cuando hay red; offline permitido con `opened_at` del dispositivo.

---

## 4. Atribución

Toda apertura/cierre POS lleva `cashier_contact_id` (Hito 2.5 §5).

- Abrir: cajero debe existir y estar **activo**.
- Cerrar (replay offline): cajero debe existir; puede estar inactivo si se desactivó después.

---

## 5. BO vs POS (límites)

| Capacidad | POS HTTP v1 | BO |
|-----------|-------------|-----|
| Abrir / cerrar turno de **su** caja | Sí | Sí (cualquier caja) |
| Cambio de cajero mid-turno | No (v1) | Sí (auditado) |
| Movimiento tesorería manual | No (v1) | Sí |
| Cobrar pedidos (Order Domain) | `/api/v1/orders*` | UI BO |

---

## 6. Criterio de desbloqueo Prog2

Con este spec + contrato HTTP + tag EN1, Prog2 cablea:

- enqueue al abrir/cerrar caja
- push con Device Token
- mapear `shift_id` / `shift_number` a la sesión local

Hasta entonces el cierre local de la APK **no** actualiza EN1 (comportamiento esperado).
