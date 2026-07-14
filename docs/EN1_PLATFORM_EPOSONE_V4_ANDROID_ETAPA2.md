# EPosOne V4 — Etapa 2 Android (Producto)

| Campo | Valor |
|-------|--------|
| Estado | **Hito 2 E2E** 🟡 · **Hito 3 Pedido** en brief (sin código) |
| Handoff | [`EN1_EPOSONE_HANDOFF_STATUS.md`](EN1_EPOSONE_HANDOFF_STATUS.md) |
| ADR-006 | [`ADR-006-EPOSONE-OPERATION-VS-ADMIN.md`](ADR-006-EPOSONE-OPERATION-VS-ADMIN.md) |
| Hito 3 | [`EN1_EPOSONE_HITO3_ORDER_LIFECYCLE.md`](EN1_EPOSONE_HITO3_ORDER_LIFECYCLE.md) |
| Hito EN1-02 | **Cerrado** — `82c68f7` · tag `eposone-provisioning-v1.0` |
| Hito 2 Sync Down | EN1 ✅ `b254735` · APK: **`GET /api/v1/devices/bootstrap`** |
| Roadmap V4 | [`EN1_PLATFORM_EPOSONE_V4_ROADMAP.md`](EN1_PLATFORM_EPOSONE_V4_ROADMAP.md) |
| Foco P2 ahora | Cerrar Bootstrap E2E (endpoint correcto) |

---

## Cambio de foco

| Hasta ahora | Ahora |
|-------------|--------|
| Bootstrap API EN1 | E2E APK con path de contrato |
| “Siguiente = ventas→stock” | **Hito 3 = Operación del Pedido** (ADR-006) |

---

## Ubicación del código APK

| Dónde | Qué |
|-------|-----|
| Servidor Dev EN1 | Backend + docs — **sin** Flutter |
| PC desarrollador | `C:\Users\shidalgo\Documents\0. Tecnologia\EPosOne\eposone` |

---

## Sprints Etapa 2

| Sprint | Entregable | Estado |
|--------|------------|--------|
| **EN1-02 / Hito 1** | Provisioning código=destino | ✅ Congelado |
| **A/B/C** | Wizard + config | ✅ |
| **Hito 2** | Bootstrap Sync Down | ✅ EN1 · 🟡 E2E APK |
| **Hito 3** | Operación del Pedido + sync | 📋 brief — contrato/GO pendiente |
| **D+** | Inventario por eventos / caja / FE | ⏸ después Hito 3 |
| **F** | Vincular EN1 (Local) | ⏳ |

---

## Congelado en APK (P2)

POS Core · Provisioning · contrato Bootstrap (solo fix de consumo de endpoint).

No: inventarios ERP, transferencias, compras, FE, estados manuales de pedido.

---

## Fuera de alcance inmediato

Planes, licencias, FE, CRM, IA, ventas→stock sin dominio Pedido — hasta GO.
