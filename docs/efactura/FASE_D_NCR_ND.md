# Fase D — Nota de crédito y nota de débito

**Dependencias:** Fase C (o al menos B con factura estable).

## Objetivo

Soportar `credit_note` y `debit_note` con referencia a factura aceptada, sin facturas negativas.

---

## D.1 Reglas

- Padre debe estar en `status=accepted` (o `credited` parcial si se modela)
- `parent_document_id` → FK a factura original
- `parent_cufe` en request estándar para mapper
- Actualizar factura padre: `status=credited` (total o flag `partial_credit`)

---

## D.2 Adapter efacturapty

Investigar en Swagger / soporte efacturapty:

- ¿Mismo endpoint `POST /api/v1/Invoices` con `tipoDocumento` distinto?
- ¿Endpoint separado?

Implementar en `EFacturaPTYAdapter`:

- `emit_credit_note`
- `emit_debit_note`

Mapper: sección `documentosFiscalesReferenciados` según doc oficial.

---

## D.3 Admin

- Desde detalle de factura aceptada: botones “Emitir nota de crédito” / “Emitir nota de débito”
- Formulario: monto/líneas, motivo
- Listado filtra por `document_type`

---

## D.4 Servicio

```python
def issue_credit_note(organization_id, parent_document_id, request: EInvoiceRequest) -> ...
def issue_debit_note(organization_id, parent_document_id, request: EInvoiceRequest) -> ...
```

Validar que líneas NCR no excedan saldo facturable (regla negocio a definir con contador).

---

## Aceptación Fase D

- [ ] NCR sandbox autorizada con referencia a CUFE factura
- [ ] ND sandbox (si aplica negocio)
- [ ] Factura padre marcada `credited`
- [ ] Logs `emit_credit_note` en event_log
