# Roadmap EN1 + EPosOne V5

| Campo | Valor |
|-------|--------|
| Estado | **Aprobado** — 14 jul 2026 |
| Sucede a | V4 (ADRs 001–006, Hitos 1–2) — V4 docs siguen válidos como historia |
| Handoff | [`EN1_EPOSONE_HANDOFF_STATUS.md`](EN1_EPOSONE_HANDOFF_STATUS.md) |
| Order Domain Spec | [`EN1_EPOSONE_ORDER_DOMAIN_SPEC_V1.md`](EN1_EPOSONE_ORDER_DOMAIN_SPEC_V1.md) |
| Spec funcional Pedido | [`EN1_EPOSONE_HITO3_SPEC_FUNCIONAL_V1.md`](EN1_EPOSONE_HITO3_SPEC_FUNCIONAL_V1.md) |
| ADR Op/Admin | [`ADR-006-EPOSONE-OPERATION-VS-ADMIN.md`](ADR-006-EPOSONE-OPERATION-VS-ADMIN.md) |

---

## Estado actual (14 jul 2026)

| Hito | Nombre | Estado |
|------|--------|--------|
| **1** | Provisioning EN1-02 | ✅ Cerrado / congelado |
| **2** | Device Bootstrap | ✅ Cerrado / congelado (API EN1; consumo APK = contrato `/api/v1/devices/bootstrap`) |
| **3** | Dominio Operativo del Pedido (Order Domain) | 🟡 Arquitectura en curso — **sin código** hasta congelar Spec + GO P1 |
| **4** | Operación del Pedido (APK + E2E) | ⏸ Tras contrato H3 congelado |
| **5** | Inventario Operativo | ⏸ |
| **6** | Caja y Pagos | ⏸ |
| **7** | Facturación | ⏸ |

```text
Arquitectura ✅ (en curso → congelar Order Domain Spec)
    ↓
P1 EN1 — Dominio + APIs Pedido (Hito 3)
    ↓
Review → congelar contrato
    ↓
P2 EPosOne — Operación POS (Hito 4)
    ↓
Integración E2E
    ↓
Hito 5 Inventario → Hito 6 Caja → Hito 7 Facturación
```

---

## Principios V5 (cerrados)

1. El **Pedido** es el corazón — no la Venta, el Inventario ni la Factura.  
2. **Un solo modelo** de Pedido (food truck → franquicia).  
3. Usuario ejecuta **acciones**; el sistema cambia **estados**.  
4. **Ownership**: dueño = POS creador mientras abierto; otros ven, no editan; en etapa de cobro pueden cobrar otros POS / BackOffice.  
5. **Sin conflictos de edición** gracias a Ownership (no “último write gana” ad hoc).  
6. Sync solo por **eventos**, nunca tablas.  
7. Inventario oficial = **EN1**; POS emite eventos; EN1 decide Kardex/stock (Hito 5).  

Cadena:

```text
Pedido → Operación → Pago → Venta → Inventario → Caja → Factura
```

---

## Qué no se toca (congelado)

- Provisioning (Hito 1)  
- Bootstrap (Hito 2)  
- Catálogo / productos / inventario maestro  
- POS Core  

---

## Quién trabaja ahora

| Rol | Ahora |
|-----|--------|
| **Arquitectura** | Cerrar / congelar [`Order Domain Spec v1.0`](EN1_EPOSONE_ORDER_DOMAIN_SPEC_V1.md) |
| **P1 EN1** | **Primero** tras GO — solo dominio + APIs Pedido (sin inventario) |
| **P2 EPosOne** | Espera contrato congelado; puede usar Bootstrap cerrado; **no** inventar Order Domain |

---

## Criterio de cierre Hito 3 (dominio + APIs EN1)

Base para Hito 4 E2E completo (ver Spec):

- Pedido nace en un POS, se modifica, sincroniza, se ve en EN1/BO  
- Cobro desde otro POS o BackOffice  
- Trazabilidad completa de eventos  
- Sin conflictos de edición (Ownership)  

El cierre **formal E2E multi-POS** se completa en **Hito 4**; Hito 3 entrega el contrato y APIs EN1 revisables/congeladas.
