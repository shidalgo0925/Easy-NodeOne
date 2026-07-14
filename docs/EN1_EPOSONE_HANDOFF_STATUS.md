# EPosOne ↔ EN1 — Dónde quedamos (handoff)

| Campo | Valor |
|-------|--------|
| Fecha | **14 jul 2026** |
| Roadmap | **V5** — [`EN1_PLATFORM_EPOSONE_V5_ROADMAP.md`](EN1_PLATFORM_EPOSONE_V5_ROADMAP.md) |
| Rama | `develop` · Hito 1 tag `eposone-provisioning-v1.0` · Hito 2 API `b254735` |
| Silo | Solo **Dev EN1** — `https://appdev.easynodeone.com` |
| **Order Domain Spec** | [`EN1_EPOSONE_ORDER_DOMAIN_SPEC_V1.md`](EN1_EPOSONE_ORDER_DOMAIN_SPEC_V1.md) — borrador · **pendiente congelar** |
| **ADR-006** | [`ADR-006-EPOSONE-OPERATION-VS-ADMIN.md`](ADR-006-EPOSONE-OPERATION-VS-ADMIN.md) |
| **Hito 1** | ✅ Cerrado / congelado |
| **Hito 2** | ✅ Cerrado / congelado |
| **Hito 3** | 🟡 Arquitectura — dominio Pedido · **sin código** |
| **Hitos 4–7** | ⏸ Operación · Inventario · Caja · FE |
| **Quién ahora** | Arquitectura congela Spec → luego **GO P1** (EN1 primero) |

---

## Una frase

H1/H2 cerrados. Corazón = **Pedido** (V5). Order Domain Spec v1.0 registrada; **desarrollo H3 congelado** hasta congelar Spec + GO a Programador 1.

---

## Roadmap V5 (resumen)

| Hito | Estado |
|------|--------|
| 1 Provisioning | ✅ |
| 2 Bootstrap | ✅ |
| 3 Dominio Pedido (EN1) | 🟡 Spec |
| 4 Operación Pedido (APK) | ⏸ |
| 5 Inventario operativo | ⏸ |
| 6 Caja y pagos | ⏸ |
| 7 Facturación | ⏸ |

```text
Arquitectura → P1 dominio/APIs → congelar contrato → P2 APK → E2E → Inv → Caja → FE
```

---

## Decisiones clave (cerradas)

- Un Pedido; acciones ≠ estados; sync por eventos  
- Ownership (owner edita; cobro multi-punto)  
- Mesa: un abierto; agregar; no fusionar; sí dividir  
- Pago mixto / abonos / parciales (cliente → CxC)  
- Cocina por línea; entrega parcial; cancelación de línea  
- Inventario oficial EN1; combos → componentes; recetas después  

Detalle: Order Domain Spec.

---

## Congelado (no tocar)

Provisioning · Bootstrap · Catálogo · Productos · Inventario maestro · POS Core  

---

## Hito 2 — recordatorio APK

Catálogo Sync Down = `GET /api/v1/devices/bootstrap` + Device Bearer.  
No `/api/eposone/products` (401 con token de dispositivo).

---

## Instrucciones P1 / P2

| Quién | Ahora |
|-------|--------|
| **P1** | Esperar Spec **congelada** + GO · solo Order\* + APIs Pedido · sin inventario |
| **P2** | No inventar dominio · espera contrato · H2 cerrado |

Docs: [`EN1_EPOSONE_HITO3_ORDER_LIFECYCLE.md`](EN1_EPOSONE_HITO3_ORDER_LIFECYCLE.md)

---

## Chat nuevo

1. Arquitectura: clavar ancla sin mesa + ownership al dividir → marcar Spec **CONGELADA**  
2. **GO P1** — implementar Hito 3 en Dev EN1  
3. Review / congelar contrato HTTP  
4. **GO P2** — Hito 4  

Sin GO: no código Hito 3/4.
