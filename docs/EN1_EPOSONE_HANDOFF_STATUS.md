# EPosOne ↔ EN1 — Dónde quedamos (handoff)

| Campo | Valor |
|-------|--------|
| Fecha | **14 jul 2026** |
| Roadmap | **V5** — [`EN1_PLATFORM_EPOSONE_V5_ROADMAP.md`](EN1_PLATFORM_EPOSONE_V5_ROADMAP.md) |
| Spec dominio | [`EN1_EPOSONE_ORDER_DOMAIN_SPEC_V1.md`](EN1_EPOSONE_ORDER_DOMAIN_SPEC_V1.md) **CONGELADA** |
| **Contrato HTTP Hito 3** | [`EN1_EPOSONE_HITO3_ORDER_HTTP_CONTRACT.md`](EN1_EPOSONE_HITO3_ORDER_HTTP_CONTRACT.md) **CONGELADO** · commit **`36a0eb1`** |
| Silo | Solo **Dev EN1** — `https://appdev.easynodeone.com` |
| **Hito 1–2** | ✅ |
| **Hito 3** | ✅ EN1 + contrato HTTP congelado |
| **Hito 4** | ⏸ **GO P2** — APK consume contrato |
| **Quién ahora** | **P2** (Flutter) · P1 no reabre H3 sin bug |

---

## Una frase

Hito 3 cerrado en EN1: dominio + APIs + **contrato HTTP congelado**. Pelota en **P2** (Hito 4).

---

## Para P2 — empezar aquí

1. [`EN1_EPOSONE_HITO3_ORDER_HTTP_CONTRACT.md`](EN1_EPOSONE_HITO3_ORDER_HTTP_CONTRACT.md)  
2. Bearer = token de `POST /api/v1/devices/register`  
3. Catálogo = `GET /api/v1/devices/bootstrap` (no `/api/eposone/products`)  

---

## Congelado EN1

Provisioning · Bootstrap · Order Domain Hito 3 · Catálogo · Inventario maestro · POS Core  

---

## Chat nuevo

**GO P2** — Hito 4 operación Pedido en APK (máquina local Flutter).  
Sin inventario hasta Hito 5.
