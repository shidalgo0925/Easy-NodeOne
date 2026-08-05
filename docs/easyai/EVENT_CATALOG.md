# Event Catalog — EasyAI / EN1

| Campo | Valor |
|-------|--------|
| Versión | **1.0** |
| Envelope | `EventEnvelope` (`event_type`, `domain_id`, `organization_id`, `payload`, …) |
| Fuente primaria | `platform_domain_event` (outbox) + mirrors |

Los connectors **declaran** tipos; la publicación real sigue en servicios EN1 actuales.

---

## A. Platform / commerce (outbox)

Constantes y familias en:

- `nodeone/core/platform/events.py`
- `nodeone/core/commerce/events.py`
- helpers `modules/eposone/events.py`

| event_type | domain_id catalog | Descripción | en1_source_hint |
|------------|-------------------|-------------|-----------------|
| `eposone.order.created` | `commerce` | Pedido creado (platform) | eposone events helper |
| `eposone.order.paid` | `commerce` | Pedido pagado | eposone events helper |
| `commerce.order.*` | `commerce` | Ciclo pedido commerce core | `commerce/events.py` |
| `commerce.payment.*` | `payments` | Pagos commerce | payment service |
| `commerce.cash.*` | `commerce` | Turno / movimientos caja | cash service |
| `commerce.pos.*` | `commerce` | Terminal POS | pos service |
| `commerce.inventory.*` | `products` | Reserva/ajuste stock | inventory |
| `commerce.report.*` | `analytics` | Métricas venta/void/shift | reports handlers |
| `inventory.stock.adjusted` | `products` | Ajuste stock (platform const) | platform events |
| `sales.invoice.issued` | `payments` | Factura emitida (si cableado) | platform events |

Payload: JSON ya persistido en outbox — **no redefinir tablas**; documentar campos al cablear cada tool/event consumer.

---

## B. Order Domain timeline (por pedido)

Tabla lógica `eposone_order_event` — expuesta como eventos de dominio `commerce` (mirror):

| event_type (order) | Descripción |
|--------------------|-------------|
| `pedido.creado` | Alta |
| `pedido.actualizado` | Update |
| `pedido.dividido` | Split |
| `producto.agregado` / `producto.eliminado` | Líneas |
| `cantidad.modificada` | Qty |
| `pedido.enviado` / `pedido.listo` / `pedido.entregado` | Flujo piso |
| `pago.registrado` / `pedido.cobrado` | Cobro |
| `linea.cancelada` / `pedido.anulado` / `pedido.devuelto` | Excepciones |

**Uso EasyAI:** bitácora / evidencia; pull preferente vía tool `commerce.get_order` o bitácora turno, no SQL.

---

## C. Audit / history (no siempre en outbox)

| event_type lógico | domain_id | Descripción | fuente |
|-------------------|-----------|-------------|--------|
| `audit.history.recorded` | `audit` | Acción usuario/sistema | `history_transaction` vía HistoryLogger |
| `audit.system_action` | `audit` | `AuditService.log_system_action` | audit façade |

Declarativos para el catálogo; consumo vía tools `history.*` / `audit.*`.

---

## D. Subscriptions / entitlements / licenses

| event_type | domain_id | Notas |
|------------|-----------|-------|
| `ets.subscription.changed` | `subscriptions` | Si el registry ya publica al bus; si no, **declarado** para wiring |
| `ets.entitlement.changed` | `entitlements` | Idem |
| `eposone.license.changed` | `licenses` | register license service ya publica en varios flujos |

Confirmar emisión real en wiring; el catálogo fija el **nombre estable**.

---

## E. Membership / contacts

| event_type | domain_id | Notas |
|------------|-----------|-------|
| `membership.verified` | `membership` | Access log API Center (telemetría); normalizar en wiring |
| `contact.created` / `contact.updated` | `contacts` | Si existe publish hoy → mapear; si no → declarado |

---

## F. Event bus meta

| event_type | domain_id | Descripción |
|------------|-----------|-------------|
| `platform.event.dispatched` | `event_bus` | Opcional observabilidad del worker outbox |

---

## Consumo recomendado

1. **Tiempo real / incremental:** `event_bus.pull` → outbox.  
2. **Narrativa pedido/caja:** tools commerce (order events / bitácora).  
3. **Compliance:** tools history/audit.  

No construir un segundo event store en EasyAI; **reutilizar** el outbox EN1.
