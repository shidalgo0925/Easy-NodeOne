# Contrato de Pagos EPosOne V1

| Campo | Valor |
|-------|--------|
| Estado | **Borrador** — 19 jul 2026 · pendiente Analista + Arquitectura |
| Fase V6 | **2.3** — [`EN1_PLATFORM_EPOSONE_V6_ROADMAP.md`](EN1_PLATFORM_EPOSONE_V6_ROADMAP.md) |
| Depende de | [Modelo Comercial](EN1_EPOSONE_MODELO_COMERCIAL_V1.md) · [Fiscal](EN1_EPOSONE_CONTRATO_FISCAL_V1.md) · [Propinas](EN1_EPOSONE_CONTRATO_PROPINAS_V1.md) |
| Siguiente | Fase 2.4 — [`EN1_EPOSONE_CONTRATO_RECIBO_V1.md`](EN1_EPOSONE_CONTRATO_RECIBO_V1.md) (borrador listo) · luego Motor Comercial |
| Alcance | **Negocio** — sin tablas, APIs ni DDL |
| Dual Mode | Mismo contrato; catálogo local (Standalone) o EN1 (Integrado) |
| Base operativa hoy | Cobro mixto 1:N en Order Domain / Hito 3C (compatibilidad; este contrato lo formaliza y extiende) |

---

## 0. Objetivo

Definir **cómo se cobra, abona, cambia, acredita y reembolsa** un pedido, de forma única en Standalone e Integrado.

El Contrato de Pagos es una **política comercial tipificada**: qué medios están permitidos, con qué reglas, en qué caja, y cómo se comportan parciales / mixtos / CxC / reembolsos.

**No incluye:** layout de recibo (2.4), cálculo de impuestos/propinas (2.1–2.2), arqueo profundo de caja (Hito 6 — se enlaza).

---

## 1. Conceptos

| Concepto | Definición |
|----------|------------|
| **Medio / tender** | Forma de pago tipificada (efectivo, Yappy, …) |
| **Pago** | Aplicación de un monto de un medio a un pedido (idempotente) |
| **Pago mixto** | N pagos sobre el mismo pedido hasta cubrir el total |
| **Pago parcial / abono** | Suma de pagos &lt; total; pedido queda con saldo |
| **Cambio** | Vuelto al cliente; **solo efectivo** |
| **Crédito / CxC** | Pedido cerrado comercialmente con saldo a cobrar después |
| **Reembolso** | Devolución de dinero (parcial o total) referenciando pagos o el pedido |
| **Cancelación** | Anula el pedido **antes** de venta completa; no es lo mismo que reembolso |

```text
Total a cobrar (Motor de Totales: incluye impuestos + propina)
        ↓
Uno o más pagos (tenders)
        ↓
Saldo = 0 → pagado
Saldo > 0 → parcial / o crédito autorizado
        ↓
Caja (movimientos según medio) + Recibo
```

---

## 2. Datos del Contrato de Pagos

| Campo | Obligatorio | Notas |
|-------|-------------|--------|
| Nombre / código | Sí | Ej. “POS Panamá — retail estándar” |
| Activo / vigencia / versión | Sí | Snapshot en pedidos |
| Medios habilitados | Sí | Lista de tenders con flags |
| Permite mixto | Sí | Default **sí** |
| Permite parcial | Sí | Default **sí** (política puede exigir pago total) |
| Permite crédito / CxC | Sí | Default según vertical |
| Permite reembolso parcial | Sí | |
| Requiere supervisor para reembolso / anulación | Configurable | |

### Asignación

```text
Caja → Sucursal → Empresa
```

Una **caja** puede restringir el subconjunto de medios (ej. solo efectivo + Clave).

---

## 3. Catálogo de medios (tenders) v1

| Código | Etiqueta típica | Efectivo en caja | Requiere referencia | Notas |
|--------|-----------------|------------------|---------------------|-------|
| `cash` | Efectivo | Sí (+) | No | Único que genera **cambio** |
| `visa` | Visa | No* | Sí (auth/voucher) | *Propina/liquidación bancaria aparte |
| `mastercard` | Mastercard | No* | Sí | |
| `clave` | Clave | No* | Sí | |
| `card` | Tarjeta (legacy) | No* | Sí | Alias; normalizar a marca si se conoce |
| `yappy` | Yappy | No | Sí (recomendado) | Wallet |
| `ach` | ACH / transferencia | No | Sí | |
| `voucher` | Vale | No | Sí | |
| `customer_credit` | Crédito cliente | No | Cliente registrado | Abre / usa CxC |
| `gift_card` | Gift Card | No | Sí (nº tarjeta) | **Preparado** — saldo GC fase posterior |
| `other` | Otros | Configurable | Configurable | |

\* “No efectivo en cajón”: no mueve `opening_balance` de billetes; sí registra venta no-efectivo en el turno.

### Flags por medio

| Flag | Descripción |
|------|-------------|
| `enabled` | Visible en cobro |
| `requires_reference` | Obliga referencia (con fallback operativo hoy `NR-*` solo como red de seguridad) |
| `allows_overpay` | Solo `cash` para cambio; otros no deben exceder saldo salvo tip ya en total |
| `opens_drawer` | Tipicamente efectivo |
| `counts_as_cash_in_shift` | Para arqueo |
| `requires_customer` | Crédito / vale nominativo |
| `max_amount` / `min_amount` | Opcional |

---

## 4. Pago único, mixto y parcial

### 4.1 Reglas

1. Un pedido admite **N pagos** (`1:N`).
2. Cada pago tiene: medio, monto, referencia (si aplica), identidad de cajero, idempotencia (`payment_ref` / `event_id`).
3. `suma(pagos capturados) ≤ total` salvo efectivo con cambio (ver §5).
4. Cuando `suma = total` → pedido **pagado**.
5. Cuando `suma < total` → **parcial** (saldo pendiente) si el contrato lo permite; si no, el cobro se rechaza hasta completar.
6. POS y BO usan las **mismas** reglas (ya alineado en 3C).

### 4.2 Propina y pagos

- El **total a cobrar** ya incluye propina (Contrato Propinas + Motor Totales).
- No se “aplana” un mixto a un solo método en la venta persistida: cada tender queda registrado.
- Pregunta abierta P3 (Propinas): tip solo en un tender del mixto — decidir en revisión.

### 4.3 Idempotencia

Reintentos de sync / cola no duplican cobros: misma clave de pago → mismo resultado.

---

## 5. Cambio (vuelto)

| Regla | Valor |
|-------|--------|
| Solo medio | `cash` |
| Cálculo | `monto_recibido − saldo_pendiente_antes_del_pago` (si &gt; 0) |
| Impacto caja | Entra el recibido; sale el cambio (neto = saldo cubierto) |
| Otros medios | Monto no puede superar el saldo (rechazo) |

---

## 6. Crédito y cuentas por cobrar (CxC)

| Tema | Regla v1 |
|------|----------|
| Quién | Cliente **registrado** (no contado) |
| Autorización | Límite de crédito / supervisor según política |
| Al cobrar con `customer_credit` | Pedido puede quedar `paid` en eje operativo POS **o** `on_account` con saldo CxC — **decidir en P6** |
| Efectivo en turno | No incrementa billetes hasta cobro posterior de la CxC |
| Cobro de CxC | Documento/flujo posterior (abono a cuenta); enlaza pedido origen |

**Preparado, no cerrado:** estados exactos `payment_status` vs “venta a crédito entregada”.

---

## 7. Gift Card y depósitos

| Medio | Estado en v1 contrato |
|-------|------------------------|
| Gift Card | Medio tipificado; **motor de saldo GC** = fase posterior (preparado) |
| Depósitos / anticipos | Preparado: pago anticipado vinculado a cliente/pedido futuro — detalle en iteración CxC |

---

## 8. Reembolsos

| Tipo | Descripción |
|------|-------------|
| **Total** | Devuelve el total cobrado; invierte impuestos/propina según snapshot del pedido |
| **Parcial** | Por monto o por líneas/cantidades; prorratea fiscales (Contrato Fiscal §10) |
| **Multi-método** | Preferencia: devolver por los mismos medios; si no es posible, política de “reembolso en efectivo” con autorización |

### Reglas

1. Reembolso **≠** cancelación (cancelar = antes de venta completa, sin movimiento de reembolso de caja).
2. Requiere pedido con pagos capturados (o política de nota de crédito fiscal — FE).
3. Supervisor / permiso según contrato.
4. Cada reembolso es un movimiento tipificado enlazado al pedido (y opcionalmente al pago origen).
5. Turno de caja: `refund_cash` solo si sale efectivo.

---

## 9. Cancelaciones

| Caso | Acción |
|------|--------|
| Pedido sin pagos | Cancelar; sin reembolso |
| Pedido con pagos parciales | Primero reembolsar (o política “forzar cancelación con reembolso automático”) |
| Factura fiscal emitida | Nota de crédito / anulación FE — fuera del detalle v1; enlace FE |

---

## 10. Resultado en el pedido (negocio)

| Salida | Descripción |
|--------|-------------|
| Lista de pagos | Medio, monto, referencia, estado, cajero, timestamps |
| `amount_paid` / `balance` | Calculados |
| `payment_status` | `unpaid` / `partial` / `paid` / `refunded` / `on_account` (propuesto) |
| Cambio | Si hubo efectivo con overpay |
| Snapshot | Versión del Contrato de Pagos + medios permitidos en esa caja |

---

## 11. Dual Mode

| | Standalone | Integrado |
|--|------------|-----------|
| Catálogo de medios y flags | Local | EN1 (seed + BO) |
| Registro de pagos | SQLite | EN1 SoT; APK cola + sync |
| Validación | Motor local | EN1 recalcula saldo / rechaza inconsistencias (como hoy 3C) |

---

## 12. Criterio de aprobación

1. Catálogo de medios cubre Panamá operativo (efectivo, tarjetas, Clave, Yappy, ACH, vale, crédito, GC, otros).
2. Mixto + parcial + cambio solo efectivo quedan inequívocos.
3. Reembolso parcial/total/multi-método tipificado.
4. CxC y Gift Card marcados preparado vs cerrado.
5. Dual Mode y no aplanar mixtos en persistencia.
6. Preguntas §13 resueltas o aplazadas con dueño.

---

## 13. Preguntas abiertas

| # | Pregunta | Dueño |
|---|----------|-------|
| Pay1 | ¿Pago parcial deja el pedido entregable (retail) o bloquea fulfillment? | Analista por vertical |
| Pay2 | ¿Crédito = `paid` + CxC interna o `on_account` explícito? | Analista |
| Pay3 | ¿Reembolso siempre mismo medio o efectivo por defecto? | Analista |
| Pay4 | ¿Yappy/ACH sin referencia: rechazo duro vs `NR-*` solo legacy? | Arquitectura (tender a rechazo duro post-migración) |
| Pay5 | ¿Depósitos / anticipos en v1 o diferir? | Analista |
| Pay6 | Propina en un solo tender del mixto | Analista (enlace P3 Propinas) |

---

## 14. Relación con otros docs

| Doc | Relación |
|-----|----------|
| Hito 3C / Order Payment | Implementación actual a alinear a este contrato |
| Contrato Propinas | Total incluye tip |
| Contrato Fiscal | Reembolsos fiscales |
| Contrato Recibo 2.4 | Impresión de medios y cambio |
| Caja / Hito 6 | Arqueo, retiros, fondo de turno |

---

*Borrador V6 Fase 2.3. Sin implementación nueva hasta aprobación de Fases 1–5; el cobro 1:N actual sigue como base compatible.*
