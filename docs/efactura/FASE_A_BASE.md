# Fase A — Base del módulo FE

**Duración estimada:** 3–5 días  
**Dependencias:** ninguna (prueba API en `nodeone/devtools/efacturapty_test/` ya validada)

## Objetivo

Módulo activable/desactivable, configuración por org, emisión manual de prueba, historial y logs. **Sin** integración checkout/pagos.

---

## A.1 Kill switch global

1. Crear `backend/nodeone/services/efactura_module.py`:

```python
def is_efactura_globally_allowed() -> bool:
    raw = (os.environ.get('NODEONE_EFACTURA_MODULE_ENABLED') or '1').strip().lower()
    return raw not in ('0', 'false', 'no', 'off', 'disabled')

def is_efactura_enabled_for_org(organization_id) -> bool:
    if not is_efactura_globally_allowed():
        return False
    from nodeone.services.org_scope import has_saas_module_enabled
    return has_saas_module_enabled(organization_id, 'efactura')
```

2. En `nodeone/core/features.py`:
   - Comentario en cabecera: `NODEONE_EFACTURA_MODULE_ENABLED=0`
   - Función `register_efactura_blueprints(app)` (patrón `register_contador_blueprints`)
   - Llamar al final de `register_modules(app)`

3. Documentar en `.env.example` (si existe) la variable.

---

## A.2 Catálogo SaaS tenant

En `nodeone/services/saas_catalog_defaults.py`, añadir a `SAAS_CATALOG_MODULES`:

```python
(
    'efactura',
    'Facturación electrónica',
    'Emisión FE Panamá (PAC efacturapty y futuros proveedores).',
    False,  # toggleable por org en Admin → Módulos SaaS
),
```

Ejecutar bootstrap o `ensure_saas_module_catalog` en dev.

---

## A.3 Esquema BD

Crear `nodeone/services/efactura_schema.py` con `ensure_efactura_schema(db, engine, printfn)` idempotente (patrón `eco_docente_schema.py`):

Tablas:

- `electronic_invoice_provider_config`
- `electronic_invoice_document`
- `electronic_invoice_event_log`

Índices mínimos:

- `provider_config (organization_id, provider)` UNIQUE
- `document (organization_id, status, created_at)`
- `document (source_model, source_id)` — para idempotencia futura
- `event_log (organization_id, document_id, created_at)`

Registrar hook en `app.py` junto a otros `ensure_*_schema`.

Modelos SQLAlchemy en `nodeone/modules/efactura/models/` (o `models/efactura_*.py` si el proyecto prefiere carpeta global `models/` — **seguir convención de `contador`**).

---

## A.4 Estructura del módulo

Crear árbol según plan maestro. Mínimo viable:

```
efactura/
├── __init__.py
├── config.py
├── models/__init__.py  (+ re-export)
├── adapters/base.py
├── adapters/efacturapty.py
├── services/issue.py      # stub → implementar emit test
├── services/mapper.py     # stub Fase B; Fase A puede mapper mínimo inline en adapter
├── admin/routes.py
├── api/routes.py
└── templates/efactura/
```

Blueprints:

- `efactura_admin_bp` → `url_prefix='/admin/efactura'`
- `efactura_api_bp` → `url_prefix='/api/admin/efactura'`

`before_request` en ambos: global allowed + org module + login admin.

---

## A.5 Adapter efacturapty (mínimo)

`EFacturaPTYAdapter`:

- `test_connection`: `GET /api/v1/Catalogs/countries` o endpoint liviano; 200 = OK
- `emit_invoice`: portar lógica de `devtools/efacturapty_test/test_emit_invoice.py`
- Leer token y `api_base_url` desde `electronic_invoice_provider_config`
- **No** loguear header `Authorization`

Respuesta → normalizar a dict con `autorizada`, `cufe`, `protocolo`, `mensajes`, `raw_response`.

---

## A.6 Servicio `issue_einvoice` (versión manual)

Fase A: solo usado desde pantalla “Emitir prueba” y API `POST /test-invoice`.

Pasos:

1. Guards módulo
2. Load config
3. Insert `electronic_invoice_document` (`document_type=invoice`, `status=pending`)
4. Llamar adapter
5. Update document + insert `event_log`
6. Return

---

## A.7 Pantallas admin

### Configuración (`GET/POST /admin/efactura/config`)

- Formulario: environment, api_base_url, token (password field), default_pos, enabled
- Botón “Probar conexión” → `POST /api/admin/efactura/test-connection`
- Mostrar `last_test_status` / `last_test_message`
- Token guardado: mostrar solo últimos 4 caracteres si existe

### Emisiones (`/admin/efactura/emissions`)

- Tabla paginada filtrada por `organization_id` del scope admin
- Columnas: fecha, tipo, referencia, cliente, total, status, cufe

### Detalle (`/admin/efactura/emissions/<id>`)

- JSON request/response formateado (sin token)
- Mensajes PAC
- Link QR si `qr_url` o contenido en response

### Prueba (`/admin/efactura/test-invoice`)

- Form simple: monto, descripción línea, email receptor (default consumidor final)
- Submit → crea documento + emite
- Flash con CUFE o error

### Logs (`/admin/efactura/logs`)

- Últimos 100 `electronic_invoice_event_log` de la org

### Menú

En `templates/base.html` (bloque admin), condición:

```jinja2
{% if saas_module_enabled('efactura') %}
  ... Facturación electrónica ...
{% endif %}
```

---

## A.8 API admin (Fase A)

| Endpoint | Body | Respuesta |
|----------|------|-----------|
| `POST .../test-connection` | — | `{ok, message}` |
| `POST .../test-invoice` | `{amount, description, email?}` | `{ok, document_id, cufe, autorizada}` |
| `GET .../emissions` | query `page`, `status` | lista JSON |
| `GET .../emissions/<id>` | — | detalle JSON |

CSRF: mismo patrón que otros `/api/admin/*`.

---

## A.9 Pruebas manuales (aceptación Fase A)

- [ ] `NODEONE_EFACTURA_MODULE_ENABLED=0` → rutas 404, sin menú
- [ ] Módulo global ON, org sin `efactura` en SaaS → 403 o mensaje
- [ ] Org con `efactura` ON → menú visible
- [ ] Guardar config + test connection OK
- [ ] Emitir prueba → `autorizada: true`, CUFE en BD, correo al receptor (sandbox)
- [ ] Historial y detalle muestran JSON
- [ ] Segunda org no ve documentos de la primera

---

## A.10 Fuera de alcance Fase A

- Checkout, pagos, hooks automáticos
- Nota crédito / débito
- Cifrado token (Fase F; Fase A puede guardar token en texto en **dev only** con comentario TODO — o usar columna `api_token_encrypted` vacía y leer `EFACTURA_API_TOKEN` de env como fallback documentado)

**Recomendación Fase A:** permitir token en BD sin cifrar solo si `ENV=development`; en staging/prod exigir variable de entorno hasta Fase F.

---

## Entregables Fase A

1. PR en `develop` con módulo registrado (default OFF en prod hasta QA si se prefiere)
2. Migración/schema aplicada en dev
3. Captura pantalla config + emisión + detalle CUFE
4. Actualizar `devtools/efacturapty_test/README.md` con enlace al módulo
