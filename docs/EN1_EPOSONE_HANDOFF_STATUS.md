# EPosOne ↔ EN1 — Dónde quedamos (handoff)

| Campo | Valor |
|-------|--------|
| Fecha | **19 jul 2026** |
| **EN1-POS V7** | **Release 0 activo** — [`EN1_POS_V7_ROADMAP.md`](EN1_POS_V7_ROADMAP.md) (plan de producto) |
| **R0 pack** | Constitución · Domain · Ownership · DoD · Gap · Backlog · Arquitectura — **borradores** (ver índice V7) |
| Hito 3B | **Publicado** · pendiente recepción P2 |
| Hito 3C | **EN1 listo** — lista/detalle + cobro multi-pago + catálogo APK + compatibilidad Yappy/propina |
| **Hito 2.5** | **EN1 listo** — cajero POS · contrato + PIN hash + bootstrap `cashiers` + Sync Up |
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
| **Cierre Release 0** | Aprobación Analista + Prog1 + Prog2 · **sin código R1 antes** |

---

## Una frase

**V7 Release 0** en marcha (Constitución, Domain Model, Ownership, DoD, Gap por capacidades, Backlog, Arquitectura). R1 cierra la cadena operativa **con FE Panamá**. V6 = contratos input. EN1: 3C + cajero + políticas infra; motor totales = stub. Prog2: Hito 4 en paralelo. **No features nuevas hasta aprobar R0.**

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
| Apertura de turno desde tablet | ⏸ P2 (BO sigue para excepciones) |

---

## EN1 congelado / siguiente

| Bloque | Estado |
|--------|--------|
| H1 · H2 | Congelado |
| H2.5 Cajero | EN1 listo · contrato congelado · APK = Hito 4 |
| H3 dominio/API + contrato HTTP | Congelado (docs) |
| H3C BO cobro | Hecho en EN1 · E2E multi-POS = Hito 4 |
| TZ Fase 1 | Hecho en EN1 |
| Inventario | No hasta Hito 5 |
| P2 | Cablear HTTP H3 + cobro tablet + cajero H2.5 |
