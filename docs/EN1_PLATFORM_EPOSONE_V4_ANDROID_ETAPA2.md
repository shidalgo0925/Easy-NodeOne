# EPosOne V4 — Etapa 2 Android (Producto)

| Campo | Valor |
|-------|--------|
| Estado | **Hito 1 EN1-02 CERRADO** · siguiente = **Hito 2 Device Bootstrap (Sync Down)** |
| Handoff | [`EN1_EPOSONE_HANDOFF_STATUS.md`](EN1_EPOSONE_HANDOFF_STATUS.md) |
| Etapa previa | Infra EN1 POS/LicensePolicy — `18f6593` |
| Hito EN1-01 | Legacy — `847a09f` |
| Hito EN1-02 | **Cerrado** — `82c68f7` · tag `eposone-provisioning-v1.0` |
| Hito 2 Sync Down | Contrato: [`EN1_EPOSONE_HITO2_DEVICE_BOOTSTRAP_SYNC_DOWN.md`](EN1_EPOSONE_HITO2_DEVICE_BOOTSTRAP_SYNC_DOWN.md) (**sin código**) |
| Roadmap V4 | [`EN1_PLATFORM_EPOSONE_V4_ROADMAP.md`](EN1_PLATFORM_EPOSONE_V4_ROADMAP.md) |
| Foco ahora | Aprobar contrato Hito 2 → GO implementación (chat nuevo) |

---

## Cambio de foco

| Hasta ahora | Ahora |
|-------------|--------|
| Servidor EN1 provisioning | Pruebas E2E tablet ↔ appdev |
| Código por org + refs | Código = **Caja** (destino) |

---

## Ubicación del código APK

| Dónde | Qué |
|-------|-----|
| Servidor Dev EN1 | Backend + docs — **sin** proyecto Flutter |
| PC desarrollador | `C:\Users\shidalgo\Documents\0. Tecnologia\EPosOne\eposone` |

---

## Sprints Etapa 2

| Sprint | Entregable | Estado |
|--------|------------|--------|
| **EN1-02 / Hito 1** | Provisioning código=destino | ✅ Cerrado · tag `eposone-provisioning-v1.0` |
| **A/B** | Wizard URL+código + registro | ✅ E2E tablet Itsmo |
| **C** | Config automática post-registro | ✅ vía `/config` |
| **Hito 2** | Device Bootstrap Sync Down | 📋 contrato — sin implementar |
| **D+** | Sync ventas / stock operativo | ⏳ después Hito 2 |
| **E** | Este dispositivo | ✅ en E2E Hito 1 |
| **F** | Vincular EN1 (Local) | ⏳ |

---

## Fuera de alcance (Hito 2)

Planes, licencias, FE, CRM, IA, ventas→stock, transferencias — hasta nuevo GO.
