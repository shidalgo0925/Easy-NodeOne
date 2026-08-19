# Roadmap EN1 + EPosOne V5

| Campo | Valor |
|-------|--------|
| Estado | **Aprobado** — actualizado **18 jul 2026** · sucesor activo: [**V6 Sprint Comercial**](EN1_PLATFORM_EPOSONE_V6_ROADMAP.md) |
| Sucede a | V4 (ADRs 001–006, Hitos 1–2) — V4 docs siguen válidos como historia |
| Sucesor | [`EN1_PLATFORM_EPOSONE_V6_ROADMAP.md`](EN1_PLATFORM_EPOSONE_V6_ROADMAP.md) · [`Modelo Comercial V1`](EN1_EPOSONE_MODELO_COMERCIAL_V1.md) · ADR-008 diferido a V6 Fase 5 |
| Handoff | [`EN1_EPOSONE_HANDOFF_STATUS.md`](EN1_EPOSONE_HANDOFF_STATUS.md) |
| Order Domain Spec | [`EN1_EPOSONE_ORDER_DOMAIN_SPEC_V1.md`](EN1_EPOSONE_ORDER_DOMAIN_SPEC_V1.md) |
| Contrato HTTP H3 | [`EN1_EPOSONE_HITO3_ORDER_HTTP_CONTRACT.md`](EN1_EPOSONE_HITO3_ORDER_HTTP_CONTRACT.md) **3B PUBLICADO** · ejemplos completos |
| **Hito 2.5 Cajero** | [`EPOSONE_EN1_HITO2_5_CASHIER_CONTRACT.md`](EPOSONE_EN1_HITO2_5_CASHIER_CONTRACT.md) **EN1 listo** · consumo APK pendiente |
| Paquete APK | [`handoff-eposone/`](handoff-eposone/) → copiar a `Doc/` |
| Spec funcional Pedido | [`EN1_EPOSONE_HITO3_SPEC_FUNCIONAL_V1.md`](EN1_EPOSONE_HITO3_SPEC_FUNCIONAL_V1.md) |
| ADR Op/Admin | [`ADR-006-EPOSONE-OPERATION-VS-ADMIN.md`](ADR-006-EPOSONE-OPERATION-VS-ADMIN.md) |

---

## Estado actual (18 jul 2026)

| Hito | Nombre | Estado |
|------|--------|--------|
| **1** | Provisioning EN1-02 | ✅ Cerrado / congelado · SOP instalación en sitio (técnico + correo propio + código por caja) **REALIZADO** 19 ago 2026 — [`EN1_ROADMAP.md`](EN1_ROADMAP.md) § Instalación |
| **2** | Device Bootstrap | ✅ Cerrado / congelado (API EN1; consumo APK = contrato `/api/v1/devices/bootstrap`) |
| **2.5** | Cajero POS (snapshot + PIN + sync Up) | ✅ **EN1 listo** — contrato congelado · CRUD PIN hash · bootstrap `cashiers` · Sync Up con `cashier_contact_id` · **APK pendiente P2** |
| **3** | Dominio Pedido + contrato HTTP | ✅ **3B publicado** (ejemplos + handoff-eposone) |
| **3C** | Cobro Order Domain (EN1 BO + API) | ✅ **EN1 listo** — mixto 1:N, catálogo completo, compatibilidad APK y propina antes del pago |
| **TZ-1** | Time Zone oficial (plataforma + EPosOne) | ✅ **Fase 1** — `TimeZoneService`, org/user TZ, filtros día local, provisioning |
| **4** | Operación del Pedido (APK + E2E) | ⏸ P2 · cablear HTTP H3 + cobro tablet + **login cajero Hito 2.5** |
| **5** | Inventario Operativo | ⏸ |
| **6** | Caja y Pagos extendidos | ⏸ (catálogo métodos POS ya seedado en 3C; turno/caja profunda = H6; apertura normal desde POS = H2.5) |
| **7** | Facturación | ⏸ |

```text
Arquitectura ✅ Spec CONGELADA
    ↓
P1 EN1 — Dominio + APIs + contrato HTTP ✅
    ↓
P1 EN1 — 3C Cobro BO multi-pago ✅ (develop)
    ↓
P1 EN1 — Hito 2.5 Cajero (bootstrap + PIN + sync) ✅ (develop)
    ↓
P2 EPosOne — Operación POS (Hito 4) ← GO P2
    ↓
Integración E2E (incl. cobro tablet ↔ BO sin doble cobro + cajero offline)
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
9. **Time Zone**: persistencia y APIs en **UTC**; presentación/filtros en zona IANA del usuario (o de la empresa); conversiones solo vía `TimeZoneService`.

Cadena:

```text
Pedido → Operación → Pago(s) → Venta → Inventario → Caja → Factura
```

---

## Qué no se toca (congelado)

- Provisioning (Hito 1)  
- Bootstrap (Hito 2) — extensión **cajero** documentada en Hito 2.5 (mismo endpoint)  
- Contrato Hito 2.5 cajero v1 (PIN = verificador; nunca PIN plano)  
- Contrato HTTP Order Domain v1.0 (sin romper; solo consumir)  

---

## Hito 2.5 — Cajero POS (EN1 cerrado 18 jul 2026)

| Ítem | Notas |
|------|--------|
| Contrato | [`EPOSONE_EN1_HITO2_5_CASHIER_CONTRACT.md`](EPOSONE_EN1_HITO2_5_CASHIER_CONTRACT.md) |
| Persona | `en1_contact.is_cashier` · CRUD en EPosOne → Cajeros |
| PIN | PBKDF2-HMAC-SHA256 · tabla `eposone_cashier_credential` · BO nunca muestra/almacena plano |
| Bootstrap | `GET /api/v1/devices/bootstrap` incluye `cashiers` + `cashiers_version` · sync incremental con `?cashiers_version=` |
| Sync Up | Operaciones de turno/pedido/pago/reembolso/movimiento exigen `cashier_contact_id` |
| Flujo normal | POS abre turno tras login local PIN · BO = excepción / auditoría |
| Pendiente P2 | Catálogo local, Keystore, cabecera Caja/Cajero/Turno, open shift desde APK |

**No incluye:** UI tablet, rotación avanzada de PIN, límites de intentos (lado APK).

---

## Quién trabaja ahora

| Rol | Ahora |
|-----|--------|
| **Arquitectura** | Spec + contrato HTTP **3B publicados** ✅ · contrato **Hito 2.5** ✅ |
| **P1 EN1** | Hito 3/3B/3C + **2.5 cajero** hechos · siguiente = soporte P2 / bugs |
| **P2 EPosOne** | Copiar contratos (`handoff-eposone` + Hito 2.5) → `Doc/` · cablear HTTP H3 · login cajero + bootstrap `cashiers` · cobro tablet |

---

## Hito 3C — detalle EN1 (cerrado en código)

| Ítem | Notas |
|------|--------|
| Servicio | `OrderPaymentService` (delegado desde `OrderDomainService.add_payment`) |
| API | `POST /api/v1/orders/{id}/payments` · `GET /api/v1/orders/payment-methods` |
| Reglas | monto ≤ saldo · suma hasta `paid` · idempotencia `payment_ref`/`event_id` · propina explícita (`tip`/`propina`) o inferida como compatibilidad |
| Catálogo | Efectivo, Visa, Mastercard, Clave, Yappy, ACH, Vale, Crédito Cliente, Gift Card, Otros + `card` legacy |
| Compatibilidad APK | Acepta `method`, `method_key`, `payment_method`, `payment_type`, `forma_pago` o `tipo_pago`; normaliza etiquetas/alias |
| Referencia | Visa/Mastercard/Clave/Yappy/ACH/Gift Card deben enviarla; EN1 genera `NR-{payment_ref}` solo como fallback para no perder el cobro |
| Pago mixto | 1:N sobre el pedido; P2 debe enviar un POST idempotente por componente del pago |
| BO | Detalle pedido → **Cobrar pedido** → métodos dinámicos → **Confirmar cobro** |
| Corrección Yappy | 18 jul: R-000002 recuperado como Yappy B/.14.12; causa = total EN1 B/.12.84 sin propina B/.1.28 |

**Contrato P2:** sincronizar `tip` antes o junto al pago; mandar referencia real en métodos que la exigen. La inferencia de propina y referencia `NR-*` son redes de seguridad, no el flujo normal.

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
