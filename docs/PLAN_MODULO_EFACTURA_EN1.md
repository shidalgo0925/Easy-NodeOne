# Plan maestro — Módulo Facturación Electrónica (EN1 + efacturapty)

**Versión:** 1.0 · **Fecha:** 2026-05-28  
**Repo:** `/opt/easynodeone/dev/app` (rama `develop`)  
**Prueba API aislada (hecha):** `backend/nodeone/devtools/efacturapty_test/`

---

## Objetivo general

Crear en **Easy NodeOne (EN1)** un módulo de **Facturación Electrónica Panamá**, usando **efacturapty** como primer proveedor PAC, con arquitectura preparada para otros proveedores (HKA, Edicom, etc.).

```
EN1 → Módulo FE → Adapter PAC → API → CUFE / PDF / XML / estado fiscal
```

**Principio:** la FE **no** vive dentro de checkout, pagos ni eventos. Vive en `nodeone/modules/efactura/`; el resto del sistema la invoca cuando corresponda.

---

## 1. Arquitectura de carpetas

```
backend/nodeone/modules/efactura/
├── __init__.py
├── config.py              # flags global + helpers org
├── models/
│   ├── provider_config.py
│   ├── document.py
│   └── event_log.py
├── adapters/
│   ├── base.py            # EInvoiceProviderAdapter (ABC)
│   └── efacturapty.py     # EFacturaPTYAdapter
├── services/
│   ├── issue.py           # issue_einvoice(), retry, test_connection
│   ├── mapper.py          # EN1 estándar → JSON proveedor
│   └── validation.py
├── admin/
│   └── routes.py          # Blueprint HTML /admin/efactura
├── api/
│   └── routes.py          # Blueprint JSON /api/admin/efactura
├── templates/efactura/
├── tests/
└── docs/
    ├── README.md
    └── (instrucciones por fase en /docs/efactura/)
```

| Capa | Responsabilidad |
|------|-----------------|
| `config` | Activar/desactivar módulo y proveedor |
| `models` | Configuración, documentos fiscales, logs |
| `adapters` | Comunicación con efacturapty u otro PAC |
| `services` | Lógica fiscal interna EN1 |
| `admin` | Pantallas administrativas |
| `api` | Endpoints internos (AJAX / integraciones) |
| `templates` | Vistas HTML admin |
| `tests` | Unitarios e integración sandbox |
| `docs` | Documentación del módulo |

---

## 2. Interruptores ON/OFF

### Nivel 1 — Global (servidor)

Variable: `NODEONE_EFACTURA_MODULE_ENABLED` (default `1`).

Si `0` / `false` / `off`:

- No registrar blueprints en `nodeone/core/features.py`
- No mostrar menú admin
- No permitir emisión (API devuelve 404 o mensaje claro)

Patrón de referencia: `nodeone/services/academic_module.py` → `is_academic_globally_allowed()`.

### Nivel 2 — Por tenant (SaaS)

- Catálogo: `saas_module.code = 'efactura'` en `nodeone/services/saas_catalog_defaults.py` → `SAAS_CATALOG_MODULES`
- Por org: fila en `saas_org_module.enabled`
- Plantillas/guards: `has_saas_module_enabled(org_id, 'efactura')` vía `nodeone/services/org_scope.py`

Ejemplo operativo: RELATIC ON, IIUS OFF, Cliente X ON, Cliente Y OFF.

---

## 3. Modelo de datos

### 3.1 `electronic_invoice_provider_config`

Configuración fiscal por organización y proveedor.

| Campo | Tipo | Notas |
|-------|------|--------|
| `id` | PK | |
| `organization_id` | FK | Obligatorio, índice |
| `provider` | string | `efacturapty` (extensible: `hka`, `edicom`, …) |
| `environment` | string | `sandbox` \| `production` |
| `api_base_url` | string | Default `https://api.efacturapty.com` |
| `api_token_encrypted` | text | Cifrado en reposo (ver Fase F) |
| `default_branch` | string | Sucursal / código sucursal |
| `default_pos` | string | Punto facturación (`001`, etc.) |
| `default_currency` | string | `USD` / `PAB` según negocio |
| `enabled` | bool | Activo para esta org+proveedor |
| `last_test_status` | string | `ok` \| `error` |
| `last_test_message` | text | |
| `created_at` / `updated_at` | datetime | |

**Única fila activa por** `(organization_id, provider)` recomendada (unique constraint).

### 3.2 `electronic_invoice_document`

Documento fiscal EN1 (abstracción independiente del PAC).

| Campo | Notas |
|-------|--------|
| `organization_id`, `provider`, `environment` | |
| `document_type` | `invoice` \| `credit_note` \| `debit_note` |
| `internal_reference` | Ej. `INV-2026-00042` |
| `source_model`, `source_id` | Origen EN1 opcional (`payment`, `invoice`, `order`, …) |
| `customer_name`, `customer_tax_id`, `customer_email` | |
| `subtotal`, `tax_total`, `discount_total`, `total`, `currency` | |
| `status` | Ver estados abajo |
| `cufe`, `pac_reference`, `authorization_message` | |
| `request_payload`, `response_payload` | JSON (text o JSONB en PG) |
| `pdf_url`, `xml_url`, `qr_url` | O paths/blob refs |
| `issued_at`, `accepted_at`, `rejected_at`, `cancelled_at` | |
| `error_message`, `retry_count` | |
| `parent_document_id` | FK self — NCR/ND referencian factura |
| timestamps | |

**Estados:** `draft` → `pending` → `sent` → `accepted` | `rejected` | `error` → `cancelled` | `credited`

### 3.3 `electronic_invoice_event_log`

Auditoría técnica por acción.

| Campo | Notas |
|-------|--------|
| `organization_id`, `document_id` (nullable en test_connection) | |
| `event_type` | Ver lista abajo |
| `message`, `http_status` | |
| `request_payload`, `response_payload` | Sin token |
| `created_at` | |

**Eventos:** `test_connection`, `emit_invoice`, `emit_credit_note`, `emit_debit_note`, `query_status`, `download_pdf`, `download_xml`, `error`, `retry`

---

## 4. Adapter PAC

### Interfaz base (`adapters/base.py`)

```python
class EInvoiceProviderAdapter(ABC):
    def test_connection(self, config) -> ProviderTestResult: ...
    def emit_invoice(self, config, document, lines) -> EmitResult: ...
    def emit_credit_note(self, config, document, parent_cufe, lines) -> EmitResult: ...
    def emit_debit_note(self, config, document, parent_cufe, lines) -> EmitResult: ...
    def query_status(self, config, cufe: str) -> StatusResult: ...
    def download_pdf(self, config, cufe: str) -> bytes | None: ...
    def download_xml(self, config, cufe: str) -> bytes | None: ...
```

### Resultado estándar EN1 (`EmitResult`)

Campos normalizados para todos los PAC:

- `success: bool`
- `autorizada: bool`
- `cufe: str | None`
- `protocolo: str | None`
- `mensajes: list[{codigo, texto}]`
- `raw_request`, `raw_response` (dict)
- `pdf_base64`, `xml_base64`, `qr_content` (opcional)

### Adapter inicial: `EFacturaPTYAdapter`

- Basado en prueba validada: `POST /api/v1/Invoices`, Bearer token, `Accept-Language: es-PA`
- Mapper EN1 → JSON según Swagger: `https://api.efacturapty.com/swagger/v1/swagger.json`
- Reutilizar lecciones de `devtools/efacturapty_test/factura_prueba.json` (consumidor final `tipoReceptorFe: 02`, `paisReceptor: PA`, correo obligatorio, ITBMS, `grupoFormasPago`)

**Factory:** `get_adapter(provider: str) -> EInvoiceProviderAdapter`

---

## 5. Servicio principal

**Función:** `issue_einvoice(organization_id, source, lines, *, document_type='invoice', parent_document_id=None)`

Flujo:

1. `is_efactura_globally_allowed()` y `has_saas_module_enabled(org, 'efactura')`
2. Cargar `electronic_invoice_provider_config` (enabled)
3. Validar líneas e impuestos (`validation.py`)
4. Crear `electronic_invoice_document` en `draft` → `pending`
5. Mapper → payload proveedor
6. Adapter.emit_* 
7. Persistir request/response en documento + `event_log`
8. Actualizar estado (`accepted` si `autorizada`)
9. Retornar `EmitResult` al llamador

**Regla:** checkout/pagos **no** importan el adapter; solo llaman `issue_einvoice()` (Fase C).

---

## 6. Admin UI

**Menú:** Admin → Facturación Electrónica (`/admin/efactura`)

| Pantalla | Ruta sugerida |
|----------|----------------|
| Configuración | `/admin/efactura/config` |
| Emisiones (listado) | `/admin/efactura/emissions` |
| Detalle emisión | `/admin/efactura/emissions/<id>` |
| Prueba de emisión | `/admin/efactura/test-invoice` |
| Logs | `/admin/efactura/logs` |

**Guards en cada ruta:** login + admin + módulo global ON + SaaS `efactura` ON para org activa.

**Configuración:** ambiente, URL, token (input password, mostrar enmascarado `************CA57`), sucursal/POS, probar conexión, guardar.

**Emisiones:** tabla con fecha, tipo, referencia, cliente, total, estado, CUFE, mensaje; detalle con JSON y enlaces PDF/XML.

---

## 7. API interna (admin)

Prefijo: `/api/admin/efactura`

| Método | Ruta | Fase |
|--------|------|------|
| POST | `/test-connection` | A |
| POST | `/test-invoice` | A |
| GET | `/emissions` | A |
| GET | `/emissions/<id>` | A |
| POST | `/emissions/<id>/retry` | E |

Futuro (integración):

| POST | `/issue` | C |
| POST | `/credit-note` | D |
| POST | `/debit-note` | D |

---

## 8. Reglas de negocio clave

### Emisión manual primero (Fase A–B)

Admin emite factura de prueba (consumidor final, 1 línea, monto bajo) antes de automatizar.

### Integración pagos (Fase C)

- Emitir **solo** tras pago confirmado
- **Yappy manual:** recibo cargado ≠ pagado; FE solo cuando admin aprueba
- Idempotencia: no duplicar si ya existe `electronic_invoice_document` para `(source_model, source_id)`

### Consumidor final (Fase B)

Sin RUC válido → `tipoReceptorFe` consumidor final; guardar nombre/email/teléfono capturados en EN1.

### Nota de crédito / débito (Fase D)

- NCR/ND con `parent_document_id` y referencia CUFE original
- No “factura negativa”

### Reintentos (Fase E)

- Fallo → `status=error`, `retry_count++`
- Reintento **manual** desde admin hasta confirmar idempotencia con PAC

### Seguridad

- Sin token en código ni logs
- Token enmascarado en UI
- Filtrar **siempre** por `organization_id`
- Admin plataforma vs tenant (scope existente en `admin_data_scope_organization_id()`)

---

## 9. Fases de desarrollo

| Fase | Nombre | Entregable resumido |
|------|--------|---------------------|
| **A** | Base del módulo | ON/OFF, modelos, admin config/historial, adapter efacturapty, prueba manual |
| **B** | Normalización fiscal | Payload estándar EN1, mapper, validaciones, consumidor final |
| **C** | Integración pagos | Hook post-pago, checkout, Yappy, idempotencia |
| **D** | Documentos completos | Factura, NCR, ND, referencias |
| **E** | Operación | Reintentos, PDF/XML, consulta estado, dashboard |
| **F** | Producción | Cifrado tokens, hardening, migraciones, docs usuario |

**Instrucciones detalladas por fase:** carpeta [`docs/efactura/`](efactura/README.md).

---

## 10. Referencias técnicas efacturapty (validado en dev)

| Ítem | Valor |
|------|--------|
| URL base | `https://api.efacturapty.com` |
| Emisión | `POST /api/v1/Invoices` |
| Consulta | `GET /api/v1/Invoices/{cufe}` |
| Auth | `Authorization: Bearer <token>` |
| Header | `Accept-Language: es-PA` |
| Ambiente pruebas | Respuesta con `iAmb: 2` (según emisor del token) |
| Query opcional | `?xml=true&qr=true` |

Documentación: https://www.efacturapty.com/docs · Swagger en servidor.

---

## 11. Registro en EN1 (checklist global)

- [ ] `SAAS_CATALOG_MODULES` + `ensure_saas_module_catalog`
- [ ] `nodeone/services/efactura_module.py` (`is_efactura_globally_allowed`, `is_efactura_enabled_for_org`)
- [ ] `register_efactura_blueprints` en `features.py` → `register_modules`
- [ ] DDL idempotente en bootstrap (patrón `ensure_*_schema` en `app.py`)
- [ ] Menú en `templates/base.html` con `saas_module_enabled('efactura')`
- [ ] `.env.example`: `NODEONE_EFACTURA_MODULE_ENABLED=1`

---

## 12. Decisión de arquitectura (cerrada)

1. **Motor FE independiente** primero.  
2. **Conectar** ventas/pagos/eventos después vía `issue_einvoice()`.  
3. **No** mezclar lógica PAC dentro de checkout.

Así EN1 soporta efacturapty hoy y otro PAC mañana cambiando adapter + fila en `provider_config`.

---

## Documentos relacionados

- [Índice de fases para programadores](efactura/README.md)
- [Prueba API aislada](../backend/nodeone/devtools/efacturapty_test/README.md)
- [Catálogo SaaS](../backend/nodeone/services/saas_catalog_defaults.py)
- [Ubicación apps](../UBICACION-APPS.md)
