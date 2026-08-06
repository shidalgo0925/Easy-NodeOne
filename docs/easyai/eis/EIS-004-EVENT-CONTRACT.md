# EIS-004 — Event Contract

| Campo | Valor |
|-------|--------|
| ID | **EIS-004** |
| Versión | **1.0.0** |
| Padre | EIS-000 |
| Estado | **Frozen / Approved** |

---

## 1. Propósito

Definir cómo un producto **publica Eventos** de negocio hacia consumidores EasyAI.

**No especifica** implementación de Event Bus. Solo el contrato de evento y de declaración de tipos.

---

## 2. Envelope canónico

```json
{
  "event_id": "evt_01JABC…",
  "event_type": "Commerce.CashShiftClosed",
  "connector_id": "eposone",
  "capability": "commerce.events",
  "organization_id": "org_123",
  "occurred_at": "2026-08-05T02:15:00Z",
  "schema_version": "1.0",
  "payload": { },
  "correlation_id": null,
  "idempotency_key": "shift:456:closed"
}
```

| Campo | Requerido | Descripción |
|-------|-----------|-------------|
| `event_id` | sí | Único global o único por connector |
| `event_type` | sí | Prefijo Dominio + PascalCase o dotted estable |
| `connector_id` | sí | Emisor |
| `organization_id` | sí* | Tenant (*salvo eventos platform globales documentados) |
| `occurred_at` | sí | UTC |
| `payload` | sí | DTO JSON |
| `schema_version` | sí | Shape de payload |
| `idempotency_key` | recomendado | Dedup |

---

## 3. Naming

Recomendado:

```text
{BoundedContext}.{PastTenseVerb}
```

Ejemplos normativos (catálogo):

| event_type | Dominio tipico |
|------------|----------------|
| `Commerce.OrderCreated` | Commerce / POS |
| `Commerce.PaymentReceived` | Payments |
| `Commerce.CashShiftClosed` | Cash |
| `Membership.MembershipApproved` | Membership |
| `License.LicenseExpired` | Licensing |
| `Marketing.CampaignPublished` | EM+Acción / marketing |

Aliases legacy del producto (ej. `eposone.order.created`) se mapean en Manifest `event_aliases`.

---

## 4. Declaración de tipos

Cada tipo se declara:

```json
{
  "event_type": "Commerce.CashShiftClosed",
  "description": "Turno de caja cerrado con arqueo.",
  "capability": "commerce.events",
  "payload_schema": { "type": "object" },
  "delivery": ["pull", "push"]
}
```

`delivery` indica intenciones; el bus real lo elige EasyAI/producto en sprint de implementación.

---

## 5. Entrega (contrato lógico)

| Modo | Descripción |
|------|-------------|
| **pull** | EasyAI consulta `events?since=&limit=` (cursor) |
| **push** | Producto notifica webhook firmado (EIS-005) |

S1: solo especifica; no implementa.

---

## 6. Inmutabilidad

Eventos publicados no se editan. Corrección = nuevo evento compensatorio (`…Corrected` / `…Cancelled`) documentado.
