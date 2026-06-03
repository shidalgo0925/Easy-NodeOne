# Fase B — Normalización fiscal EN1

**Dependencias:** Fase A completada y aceptada.

## Objetivo

Payload **estándar EN1** independiente del PAC; mapper EN1 → efacturapty; validaciones de cliente, líneas e impuestos; consumidor final.

---

## B.1 DTOs estándar (`services/dto.py` o `schemas.py`)

```python
@dataclass
class EInvoiceLine:
    description: str
    quantity: Decimal
    unit_price: Decimal
    discount: Decimal = 0
    tax_code: str = '00'   # ITBMS PA: 00 exento, 01 7%, 02 10%, 03 15%
    tax_amount: Decimal = 0

@dataclass
class EInvoiceCustomer:
    name: str
    tax_id: str | None = None      # RUC completo si contribuyente
    email: str | None = None
    phone: str | None = None
    country: str = 'PA'
    is_final_consumer: bool = False

@dataclass
class EInvoiceRequest:
    document_type: str  # invoice | credit_note | debit_note
    currency: str
    lines: list[EInvoiceLine]
    customer: EInvoiceCustomer
    internal_reference: str | None = None
    parent_cufe: str | None = None   # NCR/ND Fase D
```

---

## B.2 Validaciones (`services/validation.py`)

- Al menos 1 línea
- `quantity > 0`, `unit_price >= 0`
- Totales coherentes: `subtotal`, `tax_total`, `total`
- Cliente:
  - Si `tax_id` presente → validar formato RUC PA (reglas básicas)
  - Si no hay `tax_id` válido → forzar `is_final_consumer=True`
- Email obligatorio para efacturapty (validado en prueba)
- `document_type` permitido según fase

Errores → excepción `EInvoiceValidationError` con mensajes en español para admin.

---

## B.3 Mapper (`services/mapper.py`)

`map_to_efacturapty_invoice(request: EInvoiceRequest, config: ProviderConfig) -> dict`

Reglas conocidas (efacturapty):

| EN1 | efacturapty |
|-----|-------------|
| `is_final_consumer` | `informacionReceptor.tipoReceptorFe = "02"` |
| contribuyente | `tipoReceptorFe` + `datosRucReceptor` |
| líneas | `listaItems[]` con `grupoPrecios`, `grupoITBMS` |
| totales | `totales` con `grupoFormasPago`, `valorTotalFactura`, etc. |
| fecha | `datosGenerales.fechaEmision` ISO8601 UTC |
| POS | `config.default_pos` → `puntoFacturacion` |

**No** duplicar lógica en adapter: adapter solo HTTP; mapper solo transformación.

Tests unitarios con fixture `factura_prueba.json` golden file.

---

## B.4 Refactor `issue_einvoice`

Firma unificada:

```python
def issue_einvoice(
    organization_id: int,
    request: EInvoiceRequest,
    *,
    source_model: str | None = None,
    source_id: int | None = None,
) -> ElectronicInvoiceDocument:
```

Calcular totales desde líneas si no vienen precalculados.

Persistir `request_payload` = JSON del **estándar EN1** (no solo el del PAC).

`response_payload` = respuesta PAC.

---

## B.5 Pantalla prueba mejorada

- Selector: consumidor final vs RUC
- Campos condicionales
- Vista previa JSON EN1 antes de enviar (opcional)
- ITBMS por línea (dropdown 00/01/02/03)

---

## Aceptación Fase B

- [ ] Tests unitarios mapper (mínimo 3 casos: CF, RUC, 2 líneas)
- [ ] Validación rechaza email vacío
- [ ] Totales en BD coinciden con suma de líneas
- [ ] Emisión manual sigue autorizando en sandbox

---

## Fuera de alcance

- Hooks de pago
- NCR/ND (salvo mapper preparado con `parent_cufe` ignorado)
