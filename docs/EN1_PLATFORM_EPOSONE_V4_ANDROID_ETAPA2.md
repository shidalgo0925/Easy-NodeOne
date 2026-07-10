# EPosOne V4 — Etapa 2 Android (Producto)

| Campo | Valor |
|-------|--------|
| Estado | **EN1-02 congelado** · siguiente = **E2E APK** (URL + código) contra appdev |
| Handoff | [`EN1_EPOSONE_HANDOFF_STATUS.md`](EN1_EPOSONE_HANDOFF_STATUS.md) |
| Etapa previa | Infra EN1 POS/LicensePolicy — `18f6593` |
| Hito EN1-01 | Legacy — `847a09f` |
| Hito EN1-02 | **Congelado** — `82c68f7` · contrato [`EPOSONE_EN1_HITO1_PROVISIONING_CONTRACT.md`](EPOSONE_EN1_HITO1_PROVISIONING_CONTRACT.md) |
| Roadmap V4 | [`EN1_PLATFORM_EPOSONE_V4_ROADMAP.md`](EN1_PLATFORM_EPOSONE_V4_ROADMAP.md) |
| Foco ahora | Equipo **EPosOne**: Wizard URL+código → register → token → config → PIN |

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
| **EN1-02** | Provisioning código=destino | ✅ `82c68f7` congelado |
| **A/B** | Wizard URL+código + registro | ⏳ APK E2E |
| **C** | Config automática post-registro | ⏳ (config mínima ya en `/config`) |
| **D** | Sync fino | ⏳ después E2E |
| **E** | Este dispositivo | ⏳ |
| **F** | Vincular EN1 (Local) | ⏳ |

---

## Fuera de alcance

Planes, licencias, FE, CRM, IA, sync de catálogo/ventas — hasta nuevo GO.
