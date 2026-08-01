# EPosOne ↔ EN1 — Dónde quedamos (handoff)

| Campo | Valor |
|-------|--------|
| Fecha | **28 jul 2026** |
| **Post-demo Mexican Food** | Design Partner #1 · presentación comercial 28 jul · instalación **jueves 30 jul** · freeze features nuevas · SoT: [`EN1_EPOSONE_POST_DEMO_MEXICAN_FOOD_PRIORITIES.md`](EN1_EPOSONE_POST_DEMO_MEXICAN_FOOD_PRIORITIES.md) |
| **P0 inmediato** | Caja/turnos · sync 100% · estados recibos · informes/cierres (mismas cifras EN1↔EPosOne) |
| **P1 comercial** | Licenciamiento + pago EN1 + correo creación de cuenta |
| **ADR-019 / ADR-020 / ADR-021** | [ADR-019](ADR-019-ADMINISTRATIVE-HIERARCHY.md) · [ADR-020 Order Events](ADR-020-ORDER-EVENT-OWNERSHIP.md) · [ADR-021 Installation Lifecycle](ADR-021-EPOSONE-INSTALLATION-LIFECYCLE.md) (**propuesto** — bootstrap obligatorio antes de operar) |
| **ADR-011 / 012 / 013** | **Aprobados** · BrandContext Fase 1 en Dev · Arquitectura ETS · Portal `app.easytech.services` · [`ADR-011`](ADR-011-PORTAL-ETS-PUNTO-ENTRADA.md) · [`ADR-012`](ADR-012-ETS-ECOSYSTEM-ARCHITECTURE.md) · [`ADR-013`](ADR-013-PORTAL-ETS-PUNTO-ENTRADA.md) |
| **License Engine V1** | **En develop** — contrato bootstrap [`EN1_EPOSONE_LICENSE_ENGINE_V1_CONTRACT.md`](EN1_EPOSONE_LICENSE_ENGINE_V1_CONTRACT.md) · Trial 15d · features/limits · suspend/reactivate |
| **ADR-014 Subscription Registry** | **V1 en Dev** — tenant↔producto · [`ADR-014-SUBSCRIPTION-REGISTRY.md`](ADR-014-SUBSCRIPTION-REGISTRY.md) |
| **Cash Shift HTTP** | **v1.0 CONGELADO** — Device Bearer `/api/v1/cash/shifts*` · [`EN1_EPOSONE_CASH_SHIFT_HTTP_CONTRACT.md`](EN1_EPOSONE_CASH_SHIFT_HTTP_CONTRACT.md) · spec [`EN1_EPOSONE_CASH_SHIFT_SPEC_V1.md`](EN1_EPOSONE_CASH_SHIFT_SPEC_V1.md) · tag `eposone-cash-shift-http-v1.0` (tras commit) |
| **EN1-POS V7** | [`EN1_POS_V7_ROADMAP.md`](EN1_POS_V7_ROADMAP.md) — R0 P1 OK · R1 · **gates E2E/2.6** |
| **ADR-009 Caja EN1** | **Aprobado** — Caja = cobro admin · turno = unidad · `allow_en1_collect_foreign_channel` · reporte cierre · [`ADR-009-EN1-CAJA-CENTRO-COBRO.md`](ADR-009-EN1-CAJA-CENTRO-COBRO.md) · backlog **B-R1-05a/b/c** |
| **E2E oficial** | [`EN1_EPOSONE_E2E_CHECKLIST_V1.md`](EN1_EPOSONE_E2E_CHECKLIST_V1.md) — cierra Hito 2.5 |
| **Hito 2.6** | [`EN1_EPOSONE_HITO2_6_OBSERVABILITY.md`](EN1_EPOSONE_HITO2_6_OBSERVABILITY.md) — planificado |
| **R0 pack** | Prog1 firmó · faltan Analista + Prog2 + T1 |
| **B-R1-01** | Avance Empresa/sucursal/caja BO |
| Hito 3B | **Publicado** · pendiente recepción P2 |
| Hito 3C | **EN1 listo** |
| **Hito 2.5** | Código ~95% · E2E bloque **A ✅** · B–E pendiente · cierre = checklist completa |
| **Incidente 20 jul** | R-000001/2 marcados `partial` en EN1 por ITBMS auto sobre `tax:0` APK + tip acumulado · **reparado** + fix código |
| **Partial centavos** | Total 4dp vs cobro 2dp (ej. 17.1735 vs 17.17) → `partial` fantasma · **fix money2** + EN1-5-32 reparado |
| **Origen pedido** | Columna **Origen** en lista: `BO` (Caja principal) vs `Tablet` · actor BO = terminal `en1-backoffice` |
| **Lab wipe día** | `/admin/eposone/lab/wipe-today` · solo `User.is_admin` + `FLASK_ENV=development` · confirma `BORRAR HOY` · no visible a admin tenant |
| **Cajero UUID (pedido)** | APK manda UUID en `user_ref` · EN1 resuelve si llega `cashier_contact_id` · **Prog2 debe enviar** `cashier_contact_id` (+ estampar `cashier_name`) |
| **R-PAY-MULTI / R-TIP-COBRO** | Congeladas · API tip OK · **BO modal cobro + tip** · al liquidar: `status=closed` · **APK (Prog2):** sync debe sacar de abiertos si `paid`/`closed`/`financially_closed` (C20) |
| **TZ Fase 1** | **Hecho en EN1** — `TimeZoneService`, org/user TZ, filtros día local, provisioning TZ de org |
| **V6 contratos** | Inputs técnicos — [`EN1_PLATFORM_EPOSONE_V6_ROADMAP.md`](EN1_PLATFORM_EPOSONE_V6_ROADMAP.md) · mapear a R1 (**FE en R1**) |
| **V6 Infra políticas** | [`EN1_EPOSONE_COMMERCIAL_POLICY_ENGINE_INFRA_V1.md`](EN1_EPOSONE_COMMERCIAL_POLICY_ENGINE_INFRA_V1.md) **EN1 listo** · sin algoritmos |
| ADR-008 | Borrador — aprueba con motor R1 |
| Detalle estados | [`EN1_EPOSONE_HITO3B_HANDOFF_STATUS.md`](EN1_EPOSONE_HITO3B_HANDOFF_STATUS.md) |
| Roadmap V5 | [`EN1_PLATFORM_EPOSONE_V5_ROADMAP.md`](EN1_PLATFORM_EPOSONE_V5_ROADMAP.md) (historia) |
| Contrato cajero | [`EPOSONE_EN1_HITO2_5_CASHIER_CONTRACT.md`](EPOSONE_EN1_HITO2_5_CASHIER_CONTRACT.md) |
| Paquete | [`handoff-eposone/`](handoff-eposone/) · `/opt/handoff-plataformas/eposone-hito3b-Doc/` |
| Order Domain | **v1.0 CONGELADA** (R1 puede exigir extensión Venta/Recibo/FE) |
| **Cierre handoff 3B docs** | Solo cuando P2 diga: *Documentos recibidos. Comienzo implementación HTTP.* |
| **Cierre Release 0** | Prog1 OK · faltan Analista + Prog2 (+ T1) |
| **R1 código** | **B-R1-01 avance** (GO owner) · resto pendiente |

---

## Una frase

**Post-demo 28 jul:** Mexican Food listo para instalar el jueves. Congelar features nuevas. P0 = caja/turnos + sync + estados recibos + informes. El cliente no pidió features — foco = confiabilidad. Detalle: [`EN1_EPOSONE_POST_DEMO_MEXICAN_FOOD_PRIORITIES.md`](EN1_EPOSONE_POST_DEMO_MEXICAN_FOOD_PRIORITIES.md).

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
| Métodos APK | ✅ Efectivo, Visa, Mastercard, Clave, Yappy, ACH, Vale, Crédito Cliente, Gift Card, Otros |
| Alias legacy | ✅ `card`/Tarjeta y etiquetas localizadas normalizadas |
| Referencias | ✅ requeridas por contrato; fallback `NR-{payment_ref}` evita perder cobros legacy |
| Propina | ✅ `tip`/`propina` explícita; inferencia controlada si el monto la incluye y EN1 aún no la recibió |
| UI BO cobro dinámico (Confirmar cobro) | ✅ |
| Tablet EPosOne consume HTTP cobro | 🟡 operativo; P2 debe cerrar cola/reintento y referencia real |
| Caja/turno / fiscal | ⏸ Hito 6–7 |

### Incidente validado — Yappy R-000002 (18 jul)

- APK: subtotal B/.12.84 + propina B/.1.28 = Yappy B/.14.12.
- EN1 recibió el pedido y sus ítems, pero no la propina antes del pago.
- El cobro excedía el total EN1 y no se persistió.
- EN1 ahora aplica propina explícita o infiere la diferencia dentro del límite de seguridad.
- El pedido fue recuperado: `R-000002`, `method=yappy`, B/.14.12, estado `paid`.
- P2 debe seguir enviando `tip` y `reference`; los fallbacks EN1 son compatibilidad, no sustituyen el contrato.

---

## Archivos `Doc/` (APK)

```text
Doc/EN1_EPOSONE_HITO3_ORDER_HTTP_CONTRACT.md
Doc/EN1_EPOSONE_ORDER_DOMAIN_SPEC_V1.md
```

---

## Hito 2.5 — Cajero (18 jul 2026)

| Capacidad | Estado |
|-----------|--------|
| Contrato congelado | ✅ [`EPOSONE_EN1_HITO2_5_CASHIER_CONTRACT.md`](EPOSONE_EN1_HITO2_5_CASHIER_CONTRACT.md) |
| CRUD cajeros EPosOne + PIN | ✅ (hash PBKDF2; nunca plano) |
| Bootstrap `cashiers` / `cashiers_version` | ✅ mismo `GET /api/v1/devices/bootstrap` |
| Sync Up con `cashier_contact_id` | ✅ turno / pedido / pago / reembolso / movimiento |
| Login local APK + Keystore | ⏸ P2 |
| Apertura / cierre turno HTTP Device Bearer | ✅ EN1 [`EN1_EPOSONE_CASH_SHIFT_HTTP_CONTRACT.md`](EN1_EPOSONE_CASH_SHIFT_HTTP_CONTRACT.md) · cableado APK = **P2** |
| Apertura excepcional BO | ✅ Turnos UI |

---

## EN1 congelado / siguiente

| Bloque | Estado |
|--------|--------|
| H1 · H2 | Congelado |
| H2.5 Cajero | EN1 listo · contrato congelado · APK = Hito 4 |
| Cash Shift HTTP | **v1.0 congelado** · pendiente recepción P2 |
| H3 dominio/API + contrato HTTP | Congelado (docs) |
| H3C BO cobro | Hecho en EN1 · E2E multi-POS = Hito 4 |
| TZ Fase 1 | Hecho en EN1 |
| Inventario | No hasta Hito 5 |
| P2 | Cablear HTTP H3 + cobro tablet + cajero H2.5 + **turnos cash** |
