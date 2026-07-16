# Roadmap EN1 + EPosOne V5

| Campo | Valor |
|-------|--------|
| Estado | **Aprobado** — actualizado **15 jul 2026** |
| Sucede a | V4 (ADRs 001–006, Hitos 1–2) — V4 docs siguen válidos como historia |
| Handoff | [`EN1_EPOSONE_HANDOFF_STATUS.md`](EN1_EPOSONE_HANDOFF_STATUS.md) |
| Order Domain Spec | [`EN1_EPOSONE_ORDER_DOMAIN_SPEC_V1.md`](EN1_EPOSONE_ORDER_DOMAIN_SPEC_V1.md) |
| Contrato HTTP H3 | [`EN1_EPOSONE_HITO3_ORDER_HTTP_CONTRACT.md`](EN1_EPOSONE_HITO3_ORDER_HTTP_CONTRACT.md) **3B PUBLICADO** · ejemplos completos |
| Paquete APK | [`handoff-eposone/`](handoff-eposone/) → copiar a `Doc/` |
| Spec funcional Pedido | [`EN1_EPOSONE_HITO3_SPEC_FUNCIONAL_V1.md`](EN1_EPOSONE_HITO3_SPEC_FUNCIONAL_V1.md) |
| ADR Op/Admin | [`ADR-006-EPOSONE-OPERATION-VS-ADMIN.md`](ADR-006-EPOSONE-OPERATION-VS-ADMIN.md) |

---

## Estado actual (15 jul 2026)

| Hito | Nombre | Estado |
|------|--------|--------|
| **1** | Provisioning EN1-02 | ✅ Cerrado / congelado |
| **2** | Device Bootstrap | ✅ Cerrado / congelado (API EN1; consumo APK = contrato `/api/v1/devices/bootstrap`) |
| **3** | Dominio Pedido + contrato HTTP | ✅ **3B publicado** (ejemplos + handoff-eposone) |
| **3C** | Cobro Order Domain (EN1 BO + API) | ✅ **EN1 listo** (`97f6d52`) — mixto 1:N, `OrderPaymentService`, UI Confirmar cobro |
| **4** | Operación del Pedido (APK + E2E) | ⏸ P2 · cablear HTTP H3 + cobro tablet (mismo endpoint) |
| **5** | Inventario Operativo | ⏸ |
| **6** | Caja y Pagos extendidos | ⏸ (catálogo métodos POS ya seedado en 3C; turno/caja profunda = H6) |
| **7** | Facturación | ⏸ |

```text
Arquitectura ✅ Spec CONGELADA
    ↓
P1 EN1 — Dominio + APIs + contrato HTTP ✅
    ↓
P1 EN1 — 3C Cobro BO multi-pago ✅ (develop)
    ↓
P2 EPosOne — Operación POS (Hito 4) ← GO P2
    ↓
Integración E2E (incl. cobro tablet ↔ BO sin doble cobro)
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
8. **Pagos 1:N**: un pedido admite múltiples métodos (efectivo + tarjeta + Yappy, …); POS y BO usan el **mismo** servicio de dominio.

Cadena:

```text
Pedido → Operación → Pago(s) → Venta → Inventario → Caja → Factura
```

---

## Qué no se toca (congelado)

- Provisioning (Hito 1)  
- Bootstrap (Hito 2)  
- Contrato HTTP Order Domain v1.0 (sin romper; solo consumir)  

---

## Quién trabaja ahora

| Rol | Ahora |
|-----|--------|
| **Arquitectura** | Spec + contrato HTTP **3B publicados** ✅ |
| **P1 EN1** | Hito 3/3B docs cerrados · **3C cobro BO hecho** · siguiente = soporte P2 / bugs |
| **P2 EPosOne** | Copiar `docs/handoff-eposone/*` → `Doc/` · cablear HTTP · cobro tablet vía `/payments` + `/payment-methods` |

---

## Hito 3C — detalle EN1 (cerrado en código)

| Ítem | Notas |
|------|--------|
| Servicio | `OrderPaymentService` (delegado desde `OrderDomainService.add_payment`) |
| API | `POST /api/v1/orders/{id}/payments` · `GET /api/v1/orders/payment-methods` |
| Reglas | monto ≤ saldo · suma hasta `paid` · 409 `already_paid` / overpay · idempotencia `payment_ref`/`event_id` |
| Catálogo | `eposone_payment_method` (Efectivo, Visa, Mastercard, Clave, Yappy, ACH, Vale, …) |
| BO | Detalle pedido → **Cobrar pedido** → métodos dinámicos → **Confirmar cobro** |
| Commit | `97f6d52` |

**No incluye:** UI tablet, turnos de caja, fiscal, abonos con política cliente avanzada.

---

## UX BO EPosOne (acompaña 3C — 15 jul 2026)

| Área | Estado |
|------|--------|
| Design system / dashboard operativo | ✅ |
| Nav corta nativa | ✅ |
| Pedidos filtros + detalle timeline | ✅ |
| POS ligero BO (Nuevo pedido) | ✅ |
| Shell: contexto / padding | ✅ |
| Cobro dinámico en detalle | ✅ |

---

## Política permanente — 4 entregables por hito

1. Código implementado  
2. Contrato congelado  
3. Handoff actualizado  
4. Ejemplos request/response completos  

---

## Criterio de cierre Hito 3 (Dominio + APIs EN1)

Base para Hito 4 E2E completo (ver Spec):

- Pedido nace en un POS, se modifica, sincroniza, se ve en EN1/BO  
- Cobro desde otro POS o BackOffice  
- Trazabilidad completa de eventos  
- Sin conflictos de edición (Ownership)  
- Pagos múltiples 1:N vía endpoint oficial  

El cierre **formal E2E multi-POS** (tablet) se completa en **Hito 4**; Hito 3 + 3C entregan contrato y cobro EN1 revisables.
