# Roadmap EPosOne V6 — Sprint Comercial

| Campo | Valor |
|-------|--------|
| Estado | **Inputs técnicos** — plan de **producto** pasa a **V7** ([`EN1_POS_V7_ROADMAP.md`](EN1_POS_V7_ROADMAP.md)) |
| Sucede a | V5 ([`EN1_PLATFORM_EPOSONE_V5_ROADMAP.md`](EN1_PLATFORM_EPOSONE_V5_ROADMAP.md)) |
| Sucesor producto | **EN1-POS V7** · Release 0 · FE en Release 1 |
| Handoff | [`EN1_EPOSONE_HANDOFF_STATUS.md`](EN1_EPOSONE_HANDOFF_STATUS.md) |
| **Fase 1** | [`EN1_EPOSONE_MODELO_COMERCIAL_V1.md`](EN1_EPOSONE_MODELO_COMERCIAL_V1.md) **borrador** |
| **Fase 2.1** | [`EN1_EPOSONE_CONTRATO_FISCAL_V1.md`](EN1_EPOSONE_CONTRATO_FISCAL_V1.md) **borrador** |
| **Fase 2.2** | [`EN1_EPOSONE_CONTRATO_PROPINAS_V1.md`](EN1_EPOSONE_CONTRATO_PROPINAS_V1.md) **borrador** |
| **Fase 2.3** | [`EN1_EPOSONE_CONTRATO_PAGOS_V1.md`](EN1_EPOSONE_CONTRATO_PAGOS_V1.md) **borrador** |
| **Fase 2.4** | [`EN1_EPOSONE_CONTRATO_RECIBO_V1.md`](EN1_EPOSONE_CONTRATO_RECIBO_V1.md) **borrador** · Fase 2 completa (borrador) |
| **Fase 3** | [`EN1_EPOSONE_MOTOR_COMERCIAL_V1.md`](EN1_EPOSONE_MOTOR_COMERCIAL_V1.md) **borrador** |
| **Fase 4** | [`EN1_EPOSONE_MOTOR_TOTALES_V1.md`](EN1_EPOSONE_MOTOR_TOTALES_V1.md) **borrador** · Q1/T1 pendiente |
| **Fase 5** | [`ADR-008-EPOSONE-COMMERCIAL-ENGINE.md`](ADR-008-EPOSONE-COMMERCIAL-ENGINE.md) **borrador docs** · aprueba tras T1 + Fases 1–4 |
| **Infra políticas** | [`EN1_EPOSONE_COMMERCIAL_POLICY_ENGINE_INFRA_V1.md`](EN1_EPOSONE_COMMERCIAL_POLICY_ENGINE_INFRA_V1.md) **EN1 listo** (modelo + sync + bootstrap stub; sin algoritmos) |
| ADR-008 | [`ADR-008-EPOSONE-COMMERCIAL-ENGINE.md`](ADR-008-EPOSONE-COMMERCIAL-ENGINE.md) — **diferido a Fase 5** (documenta decisiones; no las descubre) |
| ADR licenciamiento | [`ADR-007-EPOSONE-COMMERCIAL-LICENSING-OFFLINE.md`](ADR-007-EPOSONE-COMMERCIAL-LICENSING-OFFLINE.md) ✅ |
| Contrato cajero | [`EPOSONE_EN1_HITO2_5_CASHIER_CONTRACT.md`](EPOSONE_EN1_HITO2_5_CASHIER_CONTRACT.md) ✅ |

---

## Objetivo del sprint

Cerrar el **modelo comercial único** de EPosOne para que funcione igual en:

- **Standalone** (datos locales)
- **Integrado con EN1** (datos EN1 + sync)

La diferencia es **únicamente el origen de los datos**.

**No se desarrolla lógica comercial definitiva** (fiscal/propinas/totales) hasta congelar contratos + ADR-008.

**Sí autorizado (infra):** Motor de Políticas genérico versionado, asignación por alcance, sync/bootstrap incremental, stub Order Calculation Engine — ver [`EN1_EPOSONE_COMMERCIAL_POLICY_ENGINE_INFRA_V1.md`](EN1_EPOSONE_COMMERCIAL_POLICY_ENGINE_INFRA_V1.md).

---

## Regla del Sprint (obligatoria)

```text
Modelo de negocio aprobado
  → Contratos aprobados
  → Motores (comercial + totales) aprobados
  → ADR-008 documenta decisiones
  → Desarrollo (APK + EN1 + sync + E2E)
```

Ninguna feature de impuestos, propinas, descuentos, pagos avanzados, impresión o cálculo de totales nuevos sin contrato/modelo aprobado.

### Paralelo operativo (sí permitido)

Mientras se define el modelo comercial, **Prog2** puede continuar con pendientes ya aprobados: **Hito 4**, **Cajeros**, **Sync** y pruebas **E2E** — no dependen de estos contratos comerciales.

---

## Estado actual (base V5)

| Ítem | Estado |
|------|--------|
| Provisioning / Bootstrap / Pedido / Pago mixto 1:N | ✅ |
| Cajeros / PIN / Sync Hito 2.5 (EN1) | ✅ EN1 · APK en Hito 4 |
| Dual Mode Local / Plataforma / Vincular (ADR-001/003) | ✅ arquitectura producto |
| Impuestos multi-tasa, propinas políticas, recibo por secciones, motor único | ❌ gap V6 |

---

## Fase 1 — Modelo Comercial (primero)

**Documento:** [`EN1_EPOSONE_MODELO_COMERCIAL_V1.md`](EN1_EPOSONE_MODELO_COMERCIAL_V1.md)

Responde: **¿Cómo funciona un negocio dentro de EPosOne?**

Debe definir (sin tablas ni APIs):

- Empresa, Sucursal, POS, Caja, Cajero, Cliente
- Pedido, Cobro, Venta
- Contratos comerciales y Políticas
- Dual Mode (mismo negocio; origen local o EN1)

**Estado:** borrador · pendiente aprobación.

**Criterio:** el ADR no inventa el negocio; el modelo lo congela primero.

---

## Fase 2 — Contratos

Tras aprobar Fase 1.

| # | Contrato | Debe definir (resumen) | Estado |
|---|----------|------------------------|--------|
| **2.1** | Fiscal | [`EN1_EPOSONE_CONTRATO_FISCAL_V1.md`](EN1_EPOSONE_CONTRATO_FISCAL_V1.md) | **Borrador** |
| **2.2** | Propinas | [`EN1_EPOSONE_CONTRATO_PROPINAS_V1.md`](EN1_EPOSONE_CONTRATO_PROPINAS_V1.md) | **Borrador** |
| **2.3** | Pagos | [`EN1_EPOSONE_CONTRATO_PAGOS_V1.md`](EN1_EPOSONE_CONTRATO_PAGOS_V1.md) | **Borrador** |
| **2.4** | Recibo | [`EN1_EPOSONE_CONTRATO_RECIBO_V1.md`](EN1_EPOSONE_CONTRATO_RECIBO_V1.md) | **Borrador** |

---

## Fase 3 — Motor Comercial

**Documento:** [`EN1_EPOSONE_MOTOR_COMERCIAL_V1.md`](EN1_EPOSONE_MOTOR_COMERCIAL_V1.md)

Define:

- Motor de políticas unificado (tipos + ámbito + versión)
- Pricing (lista, horario, sucursal, membresía)
- Descuentos y promociones (happy hour, 2x1, combos, cupones, umbrales)
- Orden de aplicación comercial previo al Motor de Totales
- Dual Mode

**Estado:** borrador · pendiente aprobación.

---

## Fase 4 — Motor de Totales

**Documento:** [`EN1_EPOSONE_MOTOR_TOTALES_V1.md`](EN1_EPOSONE_MOTOR_TOTALES_V1.md)

Congela el algoritmo Order Calculation Engine + ejemplos Panamá.

Orden propuesto (Analista) — **Opción A** en borrador:

```text
Pedido → Descuentos/Promos → Propinas → Impuestos → Redondeos → Total
```

**Abierto (T1):** confirmar Opción A vs B (impuesto antes de propina).

**Estado:** borrador · pendiente aprobación.

---

## Fase 5 — ADR-008

**Documento:** [`ADR-008-EPOSONE-COMMERCIAL-ENGINE.md`](ADR-008-EPOSONE-COMMERCIAL-ENGINE.md)

Documenta (no descubre):

- Dual Mode (§0)
- Motores Comercial y Totales
- Origen de datos / ownership
- Sync y responsabilidades EN1 vs EPosOne
- Orden de desarrollo post-aprobación

**Estado:** borrador de documentación · **aprobar solo tras** cierre T1 + revisión Fases 1–4.

---

## Después — Desarrollo

Orden de implementación (cuando Fase 5 esté cerrada):

1. Contrato Fiscal (código)
2. Contrato de Propinas
3. Contrato de Pagos
4. Contrato de Recibo
5. Motor Comercial
6. Motor de Totales
7. Implementación EPosOne
8. Implementación EN1
9. Sincronización
10. Validación E2E

Validación por vertical (restaurante, cafetería, food truck, estación, retail) antes de liberar features comerciales nuevas.

---

## Orden de trabajo inmediato

| Bloque | Quién | Entrega |
|--------|-------|---------|
| **1 Modelo** | Analista + Arquitectura | Aprobar [`MODELO_COMERCIAL_V1`](EN1_EPOSONE_MODELO_COMERCIAL_V1.md) |
| **2.1 Fiscal** | Analista + Arquitectura | Revisar/aprobar [`CONTRATO_FISCAL_V1`](EN1_EPOSONE_CONTRATO_FISCAL_V1.md) |
| **2.2 Propinas** | Analista + Arquitectura | Revisar/aprobar [`CONTRATO_PROPINAS_V1`](EN1_EPOSONE_CONTRATO_PROPINAS_V1.md) |
| **2.3 Pagos** | Analista + Arquitectura | Revisar/aprobar [`CONTRATO_PAGOS_V1`](EN1_EPOSONE_CONTRATO_PAGOS_V1.md) |
| **2.4 Recibo** | Analista + Arquitectura | Revisar/aprobar [`CONTRATO_RECIBO_V1`](EN1_EPOSONE_CONTRATO_RECIBO_V1.md) |
| **3 Motor Comercial** | Analista + Arquitectura | Revisar/aprobar [`MOTOR_COMERCIAL_V1`](EN1_EPOSONE_MOTOR_COMERCIAL_V1.md) |
| **4 Motor Totales** | Analista + Arquitectura | Revisar/aprobar [`MOTOR_TOTALES_V1`](EN1_EPOSONE_MOTOR_TOTALES_V1.md) · **cerrar T1 (A/B)** |
| **5 ADR-008** | Arquitectura | Documentar decisiones (ya no descubrir) |
| 3–4 Motores | Arquitectura + Analista | Comercial + Totales + ejemplos PA |
| 5 ADR-008 | Arquitectura | Documentar decisiones |
| Paralelo | Prog2 | Hito 4 / Cajeros / Sync E2E |
| Código comercial | Prog1 + Prog2 | **Solo tras** Fase 5 |

---

## Principio de cierre

Una sola definición del negocio para Standalone e Integrado. Cambios legales o de política se resuelven por **contratos + políticas versionadas**, no por forks de lógica en APK y EN1.
