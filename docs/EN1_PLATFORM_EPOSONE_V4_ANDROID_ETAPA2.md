# EPosOne V4/V5 — Etapa 2 Android (Producto)

| Campo | Valor |
|-------|--------|
| Roadmap vigente | **V5** — [`EN1_PLATFORM_EPOSONE_V5_ROADMAP.md`](EN1_PLATFORM_EPOSONE_V5_ROADMAP.md) |
| Estado | H1/H2 ✅ · **H2.5 EN1 ✅** · H3/3C ✅ · H4 operación ⏸ |
| Order Domain | [`EN1_EPOSONE_ORDER_DOMAIN_SPEC_V1.md`](EN1_EPOSONE_ORDER_DOMAIN_SPEC_V1.md) |
| Cajero Hito 2.5 | [`EPOSONE_EN1_HITO2_5_CASHIER_CONTRACT.md`](EPOSONE_EN1_HITO2_5_CASHIER_CONTRACT.md) |
| Handoff | [`EN1_EPOSONE_HANDOFF_STATUS.md`](EN1_EPOSONE_HANDOFF_STATUS.md) |
| Foco P2 | Consumir contratos H3 + H2.5 · no inventar Pedido ni PIN plano |

---

## Sprints

| Sprint | Estado |
|--------|--------|
| Hito 1 Provisioning | ✅ Congelado |
| Hito 2 Bootstrap | ✅ Congelado (`/api/v1/devices/bootstrap`) |
| Hito 2.5 Cajero (EN1) | ✅ Contrato + API EN1 · APK pendiente |
| Hito 3 Order Domain (EN1 / P1) | ✅ 3B publicado · 3C cobro EN1 |
| Hito 4 Operación Pedido (APK / P2) | ⏸ HTTP H3 + login cajero + cobro |
| Hito 5+ Inventario / Caja / FE | ⏸ |

---

## Congelado en APK

POS Core · Provisioning · Bootstrap · **no** inventar contrato de cajero (usar Hito 2.5) · Hito 4 con GO.
