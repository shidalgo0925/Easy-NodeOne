# EPosOne ↔ EN1 — Dónde quedamos (handoff)

| Campo | Valor |
|-------|--------|
| Fecha | **16 jul 2026** |
| Hito 3B | **Publicado** · pendiente recepción P2 |
| Hito 3C | **Avanzado en EN1** (`97f6d52`) — lista/detalle Order Domain + **cobro BO multi-pago** |
| **TZ Fase 1** | **Hecho en EN1** — `TimeZoneService`, org/user TZ, filtros día local, provisioning TZ de org |
| Detalle estados | [`EN1_EPOSONE_HITO3B_HANDOFF_STATUS.md`](EN1_EPOSONE_HITO3B_HANDOFF_STATUS.md) |
| Roadmap V5 | [`EN1_PLATFORM_EPOSONE_V5_ROADMAP.md`](EN1_PLATFORM_EPOSONE_V5_ROADMAP.md) |
| Paquete | [`handoff-eposone/`](handoff-eposone/) · `/opt/handoff-plataformas/eposone-hito3b-Doc/` |
| Order Domain | **v1.0 CONGELADA** |
| **Cierre handoff 3B docs** | Solo cuando P2 diga: *Documentos recibidos. Comienzo implementación HTTP.* |

---

## Una frase

Contrato **3B publicado** (pendiente recepción P2). En EN1, **3C operativo** + **política oficial de zona horaria (Fase 1)**: UTC en persistencia/API; presentación y filtros por IANA (usuario → empresa → `America/Panama`).

---

## Política Time Zone (Fase 1 — oficial)

| Regla | Detalle |
|-------|---------|
| Persistencia | UTC (naive en columnas `DateTime` existentes; API con sufijo `Z`) |
| Presentación | Zona efectiva vía `TimeZoneService` |
| Empresa | `saas_organization.timezone` (default `America/Panama`) |
| Usuario | prefs: `timezone`, `date_format`, `time_format`, detección/confirmación en login |
| EPosOne | Filtros `from`/`to` = día local → bounds UTC; provisioning envía TZ de la org |
| Servicio | `backend/nodeone/core/timezone_service.py` |

**Fuera de Fase 1:** Google Calendar, móvil, EPayroll, auditoría `timezone`+`offset` por evento.

---

## Estados handoff docs (regla)

1. Preparado → 2. Publicado → 3. Recibido → 4. Aceptado (= cerrado)

Docs 3B: entre **2 y 3**.

Código EN1 3C (BO cobro): **listo en develop** — no bloquea a P2.

---

## Hito 3C — qué hay en EN1 (15 jul 2026)

| Capacidad | Estado |
|-----------|--------|
| Lista/detalle BO `eposone_order` | ✅ |
| `POST /api/v1/orders/{id}/payments` | ✅ endurecido (409, idempotencia, lock) |
| `OrderPaymentService` (POS = BO) | ✅ |
| Pagos 1:N (mixto) hasta saldo | ✅ |
| Catálogo `eposone_payment_method` | ✅ seed por org |
| `GET /api/v1/orders/payment-methods` | ✅ |
| UI BO cobro dinámico (Confirmar cobro) | ✅ |
| Tablet EPosOne consume HTTP cobro | ⏸ Hito 4 (P2) |
| Caja/turno / fiscal | ⏸ Hito 6–7 |

Commit referencia: `97f6d52`.

---

## Archivos `Doc/` (APK)

```text
Doc/EN1_EPOSONE_HITO3_ORDER_HTTP_CONTRACT.md
Doc/EN1_EPOSONE_ORDER_DOMAIN_SPEC_V1.md
```

---

## EN1 congelado / siguiente

| Bloque | Estado |
|--------|--------|
| H1 · H2 | Congelado |
| H3 dominio/API + contrato HTTP | Congelado (docs) |
| H3C BO cobro | Hecho en EN1 · E2E multi-POS = Hito 4 |
| TZ Fase 1 | Hecho en EN1 |
| Inventario | No hasta Hito 5 |
| P2 | Cablear HTTP H3 + cobro tablet |
