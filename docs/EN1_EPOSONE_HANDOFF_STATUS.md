# EPosOne ↔ EN1 — Dónde quedamos (handoff)

| Campo | Valor |
|-------|--------|
| Fecha | **14 jul 2026** |
| Roadmap | **V5** — [`EN1_PLATFORM_EPOSONE_V5_ROADMAP.md`](EN1_PLATFORM_EPOSONE_V5_ROADMAP.md) |
| Spec | [`EN1_EPOSONE_ORDER_DOMAIN_SPEC_V1.md`](EN1_EPOSONE_ORDER_DOMAIN_SPEC_V1.md) **CONGELADA** |
| Silo | Solo **Dev EN1** — `https://appdev.easynodeone.com` |
| **Hito 1** | ✅ |
| **Hito 2** | ✅ |
| **Hito 3** | ✅ EN1 dominio + `/api/v1/orders*` (Device Bearer) · review/contrato HTTP |
| **Hito 4** | ⏸ GO P2 — operación APK |
| **Quién ahora** | Review Hito 3 → congelar contrato HTTP → **GO P2** |

---

## Una frase

Order Domain Spec congelada e **implementada en EN1 Dev**. Siguiente: review + GO P2 (APK consume APIs).

---

## APIs Hito 3 (Device Bearer)

```http
POST   /api/v1/orders
GET    /api/v1/orders
GET    /api/v1/orders/{id}?include=events
PATCH  /api/v1/orders/{id}
POST   /api/v1/orders/{id}/events
POST   /api/v1/orders/{id}/payments
POST   /api/v1/orders/{id}/split
```

Auth: `Authorization: Bearer <token>` del register (igual Hito 1/2).  
Tablas: `eposone_order*` · sin inventario/Kardex.

---

## Congelado

Provisioning · Bootstrap · Catálogo · Inventario maestro · POS Core · no FE  

---

## Chat nuevo

1. Review Hito 3 (contrato HTTP / tag)  
2. **GO P2** — Hito 4  
3. No inventario hasta Hito 5  
