# ADR-008 — Motor Comercial, Motor de Totales y Dual Mode

| Campo | Valor |
|-------|-------|
| ID | ADR-008 |
| Título | Motores comerciales + Dual Mode (Standalone / Integrado) |
| Estado | **Borrador de documentación** — 19 jul 2026 · pendiente aprobación tras cierre T1 y Fases 1–4 |
| Ámbito | EN1 (Prog1) + EPosOne APK (Prog2) |
| Roadmap | [`EN1_PLATFORM_EPOSONE_V6_ROADMAP.md`](EN1_PLATFORM_EPOSONE_V6_ROADMAP.md) **Fase 5** |
| Principio | Este ADR **documenta** decisiones de Fases 1–4; **no** las descubre |
| Relacionados | [ADR-001](ADR-001-EPOSONE-STANDALONE.md) · [ADR-003](ADR-003-EPOSONE-SYNC.md) · [ADR-004](ADR-004-EPOSONE-MIGRATION.md) · [ADR-006](ADR-006-EPOSONE-OPERATION-VS-ADMIN.md) · [ADR-007](ADR-007-EPOSONE-COMMERCIAL-LICENSING-OFFLINE.md) |

### Fuentes (decisiones)

| Fase | Documento |
|------|-----------|
| 1 | [`EN1_EPOSONE_MODELO_COMERCIAL_V1.md`](EN1_EPOSONE_MODELO_COMERCIAL_V1.md) |
| 2.1–2.4 | Fiscal · Propinas · Pagos · Recibo |
| 3 | [`EN1_EPOSONE_MOTOR_COMERCIAL_V1.md`](EN1_EPOSONE_MOTOR_COMERCIAL_V1.md) |
| 4 | [`EN1_EPOSONE_MOTOR_TOTALES_V1.md`](EN1_EPOSONE_MOTOR_TOTALES_V1.md) |

---

## 0. Dual Mode (principio rector)

EPosOne opera en dos modos estables y un puente:

| Modo | Origen de maestros y políticas | Quién edita |
|------|--------------------------------|-------------|
| **Standalone (Local)** | Base local | Comercio en EPosOne |
| **Integrado (Plataforma)** | EN1 = source of truth | EN1 BO; POS consume |
| **Vincular** | Cutover Local → Integrado sin reinstalar | Asistente (ADR-004) |

```text
Misma lógica de negocio (contratos + motores)
              │
     ┌────────┴────────┐
 Standalone         Integrado
     │                   │
 Datos locales      Datos EN1 + sync
```

**Regla congelada de producto:**

> Toda regla de negocio se implementa **una sola vez** (misma especificación). La diferencia entre Standalone e Integrado no está en la lógica, sino en el **origen de los datos**.

Consecuencias:

1. No hay APK “lite” vs “EN1”.
2. No hay motor fiscal/propinas solo en Flutter o solo en EN1.
3. En Integrado offline: preview local con políticas cacheadas; al sync EN1 **recalcula y valida** (Motor de Totales §4).
4. Pedidos cerrados conservan **snapshot** de políticas/versiones usadas.

---

## 1. Contexto

El Order Domain (Hito 3 / 3C) ya soporta pedido, pagos escalares y pagos 1:N. Eso no escala a verticales reales (multi-impuesto, propinas políticas, promos, recibo por secciones) sin un modelo comercial único.

V6 cerró (en borrador) el modelo, los contratos y los dos motores. Este ADR fija las **decisiones arquitectónicas** derivadas.

---

## 2. Decisiones

### D1 — Pedido es el centro

El **Pedido** es el agregado raíz. Cobro, venta, recibo/factura, caja y reportes son derivados (Modelo Comercial §3).

### D2 — Políticas tipificadas versionadas

Fiscal, propinas, pagos, recibo, pricing, discount y promotion son **tipos de política** del mismo motor de políticas (Motor Comercial §1), asignables Empresa → Sucursal → POS → Caja.

### D3 — Dos motores, roles distintos

| Motor | Responsabilidad |
|-------|-----------------|
| **Motor Comercial** | Precio efectivo, descuentos, promociones → bases comerciales tipificadas |
| **Motor de Totales** (Order Calculation Engine) | Propina + impuestos + redondeo → `total` + detalle |

Ninguno es UI ni impresora. El **Contrato de Recibo** solo formatea el resultado.

### D4 — Orden de cálculo

Según Motor de Totales (Opción **A**, pendiente cierre Analista **T1**):

```text
Pedido → Descuentos/Promos → Propinas → Impuestos → Redondeos → Total
```

Propina e impuestos **nunca** se fusionan en desglose ni recibo.

Si T1 elige Opción B, se actualiza el Motor de Totales y **este ADR** en la misma aprobación; no se implementa código hasta entonces.

### D5 — Source of truth por modo

| Artefacto | Standalone | Integrado |
|-----------|------------|-----------|
| Políticas / catálogo | Local | EN1 |
| Resultado comercial del pedido | Local | EN1 (validado) |
| Preview offline | Local | Local (caché) + reconciliación |

### D6 — Responsabilidades EN1 vs EPosOne

| Capacidad | EN1 | EPosOne |
|-----------|-----|---------|
| Edición políticas (Integrado) | Sí | No (solo lectura sync) |
| Edición políticas (Standalone) | N/A | Sí |
| Ejecutar Motor Comercial / Totales | Sí (Integrado / validación) | Sí (ambos modos) |
| Cobro en piso / impresión | — | Sí |
| SoT multi-sucursal / FE / portal | Sí | Consume |

### D7 — Sync

- Eventos, no tablas (ADR-003).
- Pagos: idempotencia ya exigida (Hito 3C); se mantiene.
- Totales: tolerancia de centavos documentada en Motor de Totales; divergencias mayores → rechazo/corrección.
- Fallbacks legacy (inferencia tip, `NR-*`) son redes de seguridad, no el contrato normal.

### D8 — Sin código comercial nuevo hasta aprobación

Ninguna feature de impuestos multi-tasa, propinas políticas, promos, recibo seccionado o recálculo oficial sin:

1. Aprobación Fases 1–4 (incl. T1), y  
2. Este ADR en estado **Aprobado (congelado)**.

**Paralelo permitido:** Hito 4, Cajeros, Sync E2E (ya aprobados).

---

## 3. Alternativas rechazadas

| Opción | Por qué no |
|--------|------------|
| Lógica solo en EN1 | Rompe Standalone (ADR-001) |
| Lógica solo en Flutter | EN1 no puede ser cerebro en Integrado; reportes divergen |
| Configs aisladas sin motor de políticas | Duplicación y forks por vertical |
| ADR antes del modelo | Descubre reglas; rechazado por Analista 19 jul |

---

## 4. Consecuencias

### Positivas

- Un producto, dos modos, un comportamiento.
- Upsell Standalone → Integrado sin reinstalar.
- Cambios legales vía políticas versionadas, no parches.

### Costos

- Dos runtimes de la misma spec (APK + EN1) a mantener alineados por `engine_version`.
- Bloqueo temporal de features comerciales hasta firmar T1 + ADR.
- Migración gradual desde totales escalares a desglose tipificado.

---

## 5. Criterio de aprobación de este ADR

1. Fases 1–4 revisadas por Analista + Arquitectura.  
2. **T1 cerrado** (A o B) y Motor de Totales actualizado si aplica.  
3. Dual Mode §0 aceptado por Prog1 y Prog2.  
4. Estado pasa a **Aprobado (congelado)** → desbloquea desarrollo en el orden V6.

Hasta entonces: **borrador de documentación** — no implementar motores en código.

---

## 6. Orden de desarrollo (post-aprobación)

1. Fiscal → 2. Propinas → 3. Pagos → 4. Recibo → 5. Motor Comercial → 6. Motor de Totales → 7. EPosOne → 8. EN1 → 9. Sync → 10. E2E  

(Detalle: roadmap V6 § Después.)

---

*ADR-008 Fase 5 V6. Sustituye el placeholder “borrador diferido” del 19 jul matutino.*
