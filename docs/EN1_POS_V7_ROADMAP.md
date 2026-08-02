# EN1-POS V7 — Roadmap de producto

| Campo | Valor |
|-------|--------|
| Estado | **Activo** — **estabilización post-demo** · Design Partner Mexican Food · **28 jul 2026** |
| Sucede a | V6 ([`EN1_PLATFORM_EPOSONE_V6_ROADMAP.md`](EN1_PLATFORM_EPOSONE_V6_ROADMAP.md)) |
| Rector | [`EN1_POS_CONSTITUCION_V1.md`](EN1_POS_CONSTITUCION_V1.md) |
| Backlog | [`EN1_POS_BACKLOG_V7.md`](EN1_POS_BACKLOG_V7.md) |
| **Prioridades inmediatas** | [`EN1_EPOSONE_POST_DEMO_MEXICAN_FOOD_PRIORITIES.md`](EN1_EPOSONE_POST_DEMO_MEXICAN_FOOD_PRIORITIES.md) ← **SoT hasta instalación jueves** |
| E2E oficial | [`EN1_EPOSONE_E2E_CHECKLIST_V1.md`](EN1_EPOSONE_E2E_CHECKLIST_V1.md) |
| Hito 2.6 | [`EN1_EPOSONE_HITO2_6_OBSERVABILITY.md`](EN1_EPOSONE_HITO2_6_OBSERVABILITY.md) |
| Handoff | [`EN1_EPOSONE_HANDOFF_STATUS.md`](EN1_EPOSONE_HANDOFF_STATUS.md) |

---

## Estado actual (28 jul 2026) — pivote post-demo

Presentación comercial con **Mexican Food**: validación de producto frente a cliente real.  
**No pidieron features nuevas.** Siguiente paso: **instalación en sitio jueves 30 jul**.

| Bloque | Estado |
|--------|--------|
| **Fase** | Estabilización para producción · **freeze** features nuevas |
| **Design Partner #1** | Mexican Food (Starter) |
| **P0 (antes jueves)** | Caja/turnos · sync 100% · estados recibos · informes/cierres |
| **P1 comercial** | Licenciamiento + pago EN1 + correo cta |
| **P2+** | Portal comercial · onboarding automático · features nuevas |
| Release 0 / V6 motor | Siguen en backlog; **no** despriorizar P0 del jueves |

### Gates inmediatos (reemplazan el orden “solo docs” hasta el jueves)

```text
1. Caja y turnos: apertura/cierre sync + mismos números EN1↔EPosOne
2. Sincronización confiable (offline → online, sin perder ventas)
3. Estados de pedidos/recibos (ADR-020: no delete post-confirm)
4. Informes operativos (venta, cajero, medios, X/Z, turnos)
5. Instalación en sitio Mexican Food (jueves)
6. Luego P1: licenciamiento + pago EN1 + onboarding correo
```

Filtro: *¿Ayuda a que la instalación del jueves sea impecable?* Si no → siguiente ciclo.

### Gates legacy (Analista 19 jul — siguen válidos, cola tras P0)

```text
1. Firmar R0 (A + P2) + T1 propinas
2. E2E Hito 2.5 — checklist A–E
3. Hito 2.6 Observabilidad (mínimo)
4. Freeze contratos V6
5. Motor Totales / Comercial
6. Resto cadena R1
```

---

## Evaluación producto (reconciliada)

| Producto | Infra | Falta inmediato |
|----------|-------|-----------------|
| **EPosOne** | ~95–97% lista | E2E tablet + cerrar 2.5 · Ownership firma P2 |
| **EN1-POS** | ~85–90% infra | BO políticas, config comercial, algoritmo totales, reportes, **2.6 obs**, E2E vista BO |

Docs que el Analista pedía y **ya existen** (firmar, no reescribir): Ownership, Gap/Capability, DoD, Constitución, Domain, Backlog.

---

## Paquete Release 0

| # | Documento | Estado |
|---|-----------|--------|
| 1–7 | Constitución · Domain · Ownership · DoD · Gap · Backlog · Arquitectura | Prog1 OK · falta A+P2 |

---

## Hitos transversales (antes / junto a R1 motor)

| Hito | Doc | Estado |
|------|-----|--------|
| **2.5 Cajeros** | Contrato + E2E | 🟡 E2E pendiente |
| **2.6 Observabilidad** | [Hito 2.6](EN1_EPOSONE_HITO2_6_OBSERVABILITY.md) | 📋 Planificado |
| **E2E oficial** | [Checklist A–E](EN1_EPOSONE_E2E_CHECKLIST_V1.md) · **C17–C25** multi-device + propina |

---

## Releases

### R0 — Constitución  
### R1 — Cadena comercial + FE (+ 2.6 obs como P0 de soporte)  
### R2 — Inventario / compras / crédito / rentabilidad  
### R3 — Restaurante / APIs / marketplace  

Detalle ítems: [`EN1_POS_BACKLOG_V7.md`](EN1_POS_BACKLOG_V7.md).

---

## Regla de oro

> Tabla/endpoint/pantalla ≠ terminado. Solo **DoD** + **E2E** donde aplique.

---

## Distribución inmediata

| Rol | Acción |
|-----|--------|
| **Analista** | Firmar R0; T1; revisar checklist E2E + 2.6 |
| **Prog2** | Ejecutar E2E A–E en tablet; firmar Ownership; pantalla diagnóstico 2.6 |
| **Prog1** | Verificar C11–C16 en EN1; panel 2.6 BO; BO políticas cuando toque post-gates |

---

## Índice

- E2E · Hito 2.6 · Constitución · Domain · Ownership · DoD · Gap · Backlog · Arquitectura  
- V6 contratos / ADR-008 · Histórico V4/V5
