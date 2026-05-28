# Fase C — Integración con pagos y ventas

**Dependencias:** Fases A y B.

## Objetivo

Emitir FE automáticamente tras **pago confirmado**, con idempotencia y reglas Yappy manual.

---

## C.1 Punto único de integración

**Único lugar** que debe llamar emisión automática (inicialmente):

`nodeone/services/payment_post_process.py` o equivalente donde el pago pasa a estado **confirmado/paid**.

Alternativa documentada: hook al final de `approve_yappy_manual_payment` (Yappy).

**Prohibido:** llamar adapter desde `payments_checkout/routes.py` directamente.

```python
def maybe_issue_einvoice_for_payment(payment, order_context):
    if not is_efactura_enabled_for_org(payment.organization_id):
        return None
    if already_has_document(source_model='payment', source_id=payment.id):
        return existing
    request = build_einvoice_request_from_payment(payment, order_context)
    return issue_einvoice(org_id, request, source_model='payment', source_id=payment.id)
```

---

## C.2 Builder desde origen de negocio

`services/builders.py`:

- `build_from_payment(payment) -> EInvoiceRequest`
- `build_from_invoice(accounting_invoice)` — si aplica factura comercial EN1
- Futuro: `build_from_event_registration`, `build_from_service_request`

Mapear:

| Origen | description | qty | price | tax |
|--------|-------------|-----|-------|-----|
| línea carrito / servicio | título servicio | 1 | monto | según config org |

---

## C.3 Idempotencia

Antes de emitir:

```sql
SELECT id FROM electronic_invoice_document
WHERE organization_id = ? AND source_model = ? AND source_id = ?
  AND status IN ('accepted', 'pending', 'sent')
LIMIT 1
```

Si existe → retornar sin re-emitir (log `skipped_duplicate` en event_log).

---

## C.4 Reglas de negocio

| Escenario | ¿Emitir FE? |
|-----------|-------------|
| PayPal/tarjeta confirmado | Sí |
| Yappy recibo subido | **No** |
| Yappy admin aprueba | Sí |
| Pago fallido / pendiente | No |
| Org sin módulo `efactura` | No |
| Config org disabled | No |
| Sin token/config | Log error, no romper checkout |

**Crítico:** fallo de FE **no** debe revertir pago; solo `status=error` en documento + alerta admin.

---

## C.5 UI mínima

- En detalle de pago / factura EN1: enlace “Ver FE” → `/admin/efactura/emissions/<id>`
- Badge: “FE emitida” / “FE pendiente” / “FE error”
- Campo opcional `cufe` denormalizado en tabla de pagos (solo si justifica performance; si no, join por source)

---

## C.6 API interna (opcional Fase C)

`POST /api/efactura/issue` (autenticado admin o servicio interno):

```json
{
  "source_model": "payment",
  "source_id": 12345
}
```

Para re-procesos manuales controlados.

---

## Aceptación Fase C

- [ ] Pago de prueba sandbox → FE automática + CUFE
- [ ] Repetir callback/webhook → no duplica CUFE
- [ ] Yappy pendiente → sin FE
- [ ] Yappy aprobado → FE
- [ ] Org con módulo OFF → sin FE, pago OK

---

## Fuera de alcance

- NCR automática en reembolsos (Fase D)
