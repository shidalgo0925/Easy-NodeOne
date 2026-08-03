# EN1 — Convenciones de rutas

## Registro de blueprints

- **Orquestador**: `nodeone/core/features.py` → `register_modules(app)` (llamado una vez desde `app.py`).
- **Idempotente**: cada `register_*` comprueba `if '<name>' not in app.blueprints`.
- **Guards SaaS**: se adjuntan al blueprint **antes** de `app.register_blueprint` (ver [EN1_SAAS_GUARDS.md](./EN1_SAAS_GUARDS.md)).
- **Apagado por entorno**: variables `NODEONE_SKIP_*` documentadas al inicio de `features.py`.

## Prefijos estándar

| Prefijo | Audiencia | Ejemplos |
|---------|-----------|----------|
| `/` | Público / miembro | `/login`, `/dashboard`, `/services` |
| `/admin/...` | Admin tenant o plataforma | `/admin/users`, `/admin/appointments` |
| `/api/...` | JSON autenticado (miembro o admin según ruta) | `/api/user/status`, `/api/notifications` |
| `/api/admin/...` | JSON admin | `/api/admin/payments`, `/api/admin/contacts` |
| `/api/public/...` | JSON externo con API key | Landing OCI (`public_api`) |
| `/crm/...` | CRM JSON (prefijo propio del blueprint) | `/crm/leads` |
| Sin prefijo `/api` pero JSON | Legado | `/create-payment-intent`, `/crm/...` |

Convención de **nombre de blueprint**: sufijo `_api` para APIs (`appointments_api`, `user_api`, `crm_api`).

## Paquetes de rutas

| Paquete | Patrón | Ejemplo |
|---------|--------|---------|
| `_app/modules/<dominio>/routes.py` | Blueprint en raíz o prefijo corto | `auth_bp` → `/login` |
| `nodeone/modules/<dominio>/routes.py` | Blueprint + `url_prefix` | `appointments_bp` → `/appointments` |
| `nodeone/modules/<dominio>/api/routes.py` | API separada | `contacts_api_bp` → `/api/admin/contacts` |
| `register.py` en módulo | Registro + guards | `efactura/register.py`, `contacts/register.py` |
| Rutas en `app.py` | Legacy en migración | Dashboard, algunos checkout, tenant switch |

Capa **service** (`service.py` / `nodeone/services/`): la ruta delega; no poner SQL largo en la vista.

## Autenticación en rutas

| Decorador | Quién entra |
|-----------|-------------|
| (ninguno) | Público; puede usar org por host |
| `@login_required` | Usuario con sesión |
| `@admin_required` | `is_admin` o permiso RBAC admin |
| `@platform_admin_required` | Solo `is_admin` plataforma |
| `@require_permission('x.y')` | Permiso RBAC concreto |
| `@require_saas_module('code')` | Sesión + módulo SaaS ON |

Primera línea útil en muchas vistas admin: resolver `organization_id` con `admin_data_scope_organization_id()`.

## Multi-tenant en rutas

1. **Queries**: filtrar por `organization_id` del scope correcto (no asumir `user.organization_id` si hay selector de org).
2. **Admin pagos**: preferir `admin_payments_scope_organization_id()` cuando aplique matriz de métodos.
3. **Público por subdominio**: `_organization_id_from_request_host(request)` en catálogo y guards de servicios.
4. **404 vs 403**: normativas públicas off → `abort(404)`; APIs SaaS off → `403` JSON.

## Rutas de compatibilidad

- URLs históricas se conservan con blueprints `*_legacy` o redirects (ej. `/notifications` → `/communications/inbox`).
- Reexportaciones: p. ej. `appointment_routes` reexporta blueprints de `nodeone.modules.appointments`.

## Inventario

Listado congelado P1 (no sustituye código vivo):

- `docs/ENDPOINTS_P1.txt` — rutas por archivo
- `docs/MODULOS_ACTIVOS_P1.txt` — capacidades por módulo

Para descubrir rutas en runtime:

```bash
flask --app app routes | head
```

## Ejemplo de blueprint nuevo

```python
# nodeone/modules/ejemplo/routes.py
ejemplo_bp = Blueprint('ejemplo', __name__, url_prefix='/admin/ejemplo')

@ejemplo_bp.before_request
def _schema():
    service.ensure_ejemplo_schema()

# En features.py:
# register_simple_saas_guard(ejemplo_bp, 'ejemplo')
# app.register_blueprint(ejemplo_bp)
```

## Documentos relacionados

- [EN1_API_CONTRACT.md](./EN1_API_CONTRACT.md)
- [EN1_SAAS_GUARDS.md](./EN1_SAAS_GUARDS.md)
