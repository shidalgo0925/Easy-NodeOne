# EN1 — Contratos de API

Convenciones JSON del backend EN1 para clientes web, Flutter y landings externos. No hay OpenAPI generado; este documento es la referencia viva.

## Transporte y autenticación

| Aspecto | Contrato |
|---------|----------|
| Formato | `application/json` en body y respuestas API |
| Sesión web/móvil | Cookie de sesión Flask-Login (`credentials: include` en fetch / Dio con cookies) |
| CSRF | Formularios HTML usan CSRF; muchas rutas `/api/*` JSON solo exigen sesión (validar por ruta al integrar) |
| HTTPS | Obligatorio en producción (ProxyFix respeta `X-Forwarded-Proto`) |

### API pública (landing)

Prefijo `/api/public/*` (`nodeone/modules/public_api`):

- Header o query: API key (`landing_service.extract_api_key_from_request`).
- Errores: `ok: false`, códigos `landing_api_not_configured`, `unauthorized`, `rate_limited`.
- CORS explícito en `after_request` para orígenes configurados.

## Formas de respuesta (familias)

El código usa **tres familias**; el cliente debe tolerarlas según el endpoint.

### Familia A — `success` (user API, CRM, muchos admin)

```json
{ "success": true, "items": [] }
{ "success": false, "error": "mensaje legible" }
```

HTTP: `200`/`201` en éxito; `400` validación; `404` no encontrado; `500` error interno.

Ejemplos: `/api/user/status`, `/crm/*`, contactos admin con mezcla de `ok`.

### Familia B — `ok` (público, contactos, algunos módulos nuevos)

```json
{ "ok": true, "services": [] }
{ "ok": false, "error": "module_disabled" }
```

### Familia C — mínima / legacy

```json
{ "error": "Módulo no habilitado", "module": "events" }
{ "error": "Forbidden", "message": "No tienes permiso para esta acción." }
```

Pagos, guards SaaS, `require_permission` en JSON.

## Códigos HTTP habituales

| Código | Cuándo |
|--------|--------|
| `200` | Lectura / acción OK |
| `201` | Creación (`demo-request`, leads CRM) |
| `400` | Validación de campos |
| `401` | No autenticado (`contacts` API: `unauthorized`) |
| `403` | Sin permiso RBAC, módulo SaaS off, org inválida |
| `404` | Recurso inexistente o módulo global off (`module_disabled`) |
| `429` | Rate limit API pública |
| `500` | Excepción no controlada (a veces incluye `str(e)` — evitar en producción cliente) |

## Errores SaaS y tenant (referencia)

| `error` | HTTP | Acción cliente |
|---------|------|----------------|
| `Módulo no habilitado` + `module` | 403 | Ocultar feature; no reintentar |
| `organization_context_lost` | 403 | Cerrar sesión / re-login |
| `Organización no disponible` | 403 | Re-seleccionar org |
| `module_disabled` / `contacts_module_disabled` | 403/404 | Feature no contratado |
| `unauthorized` | 401 | Login |
| `Forbidden` | 403 | RBAC |

## Endpoints miembro (Flutter / SPA)

| Método | Ruta | Respuesta clave |
|--------|------|-----------------|
| GET | `/api/user/status` | `{ success, status }` |
| GET | `/api/user/dashboard` | `{ success, dashboard }` |
| GET | `/api/user/membership` | Membresía o `404` + `error` |
| GET/POST | `/api/user/settings` | `{ success, preferences }` |
| GET/PUT | `/api/user/communication-preferences` | `{ success, items }` |
| GET | `/api/notifications?type=&status=&limit=` | `{ unread_count, total, notifications }` |
| POST | `/api/notifications/<id>/read` | `{ success, notification }` |
| POST | `/api/onboarding/seen` | `{ success: true }` |

Requiere módulo `communications` ON para bandeja (guard en blueprint).

## Endpoints admin JSON (muestra)

| Prefijo | Guard típico | Forma |
|---------|--------------|-------|
| `/api/admin/payments/*` | `payments` + scope org pagos | `success` / errores negocio |
| `/api/admin/contacts/*` | `contacts` + RBAC | `ok` + array en búsqueda |
| `/api/admin/efactura/*` | `efactura` | `ok` / documentos |
| `/api/admin/analytics/*` | `analytics` | KPIs por org |
| `/crm/*` | `crm` | `success` + `items` / `item` |

Scope org: implícito en servidor vía `admin_data_scope_organization_id()` — **no** confiar en `organization_id` del body sin validar acceso.

## Pagos (checkout)

| Ruta | Notas |
|------|-------|
| POST `/create-payment-intent` | Método debe estar activo en `organization_payment_methods` |
| POST `/stripe-webhook` | Sin sesión; excluido de guard SaaS checkout |
| GET `/api/payments/<id>/success` | Estado post-pago |

Error típico método desactivado: **400** con mensaje de negocio (ver checklist en `docs/ETAPA1_DEV_CHECKLIST.md`).

## Paginación y filtros

No hay estándar global. Patrones frecuentes:

- Query: `limit` (cap 100 en notificaciones), `q` búsqueda, `type`, `status`.
- Listas CRM: `items` + serialización por `_serialize_*`.

## Fechas y tipos

- Fechas ISO 8601 en JSON (`membership.end_date`, actividades CRM).
- IDs enteros.
- Booleanos explícitos (`is_active`, `enabled`).

## Versionado

- Sin prefijo `/v1` en la mayoría del monolito.
- Pack `_app/api/v1/` existe pero el registro activo pasa por blueprints concretos.
- Cambios breaking: coordinar con app móvil y documentar en commit / `FLUTTER_SYNC.md`.

## Documentos relacionados

- [EN1_ROUTES.md](./EN1_ROUTES.md)
- [FLUTTER_SYNC.md](./FLUTTER_SYNC.md)
- `docs/ENDPOINTS_P1.txt` — inventario ampliado
