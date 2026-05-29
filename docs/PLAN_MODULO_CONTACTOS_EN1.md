# Plan — Módulo Contactos EN1 (Fase 1)

## Objetivo

Maestro central de **contactos / terceros** (equivalente conceptual a `res.partner` en Odoo), separado de **usuarios del sistema** (`User` = login y permisos).

## Principios

| Entidad | Uso |
|---------|-----|
| `User` | Acceso, roles, seguridad |
| `Contact` (`en1_contact`) | Sujeto comercial y fiscal |
| `Member` / `Student` / etc. | Perfiles operativos (futuro: `contact_id`) |

**No facturar** contra `users`, `members` ni `students` directamente. Facturas y FE futuras: `invoice.contact_id` → `Contact`.

## Fase 1 (esta entrega)

- Tabla `en1_contact` y modelo `Contact`
- Flag global `NODEONE_CONTACTS_MODULE_ENABLED`
- Módulo SaaS `contacts` (toggle por organización en Admin → Módulos)
- Admin UI: listado, crear, editar, detalle, desactivar, búsqueda y filtros
- Validaciones y unicidad fiscal por organización
- **Sin** migración automática, checkout, pagos, FE ni facturas

## Menú ERP (dominio Comercial)

Desde el reordenamiento del sidebar tenant admin, **Contactos** vive en:

**Comercial** → Contactos (maestro `res.partner`, no bajo Ventas ni FE).

Orden del dominio Comercial: CRM (si aplica) → **Contactos** → Servicios → Ventas.

## Activación

1. **Despliegue:** `NODEONE_CONTACTS_MODULE_ENABLED=1` (por defecto en `.env.example`)
2. **Por organización:** Admin plataforma → Módulos SaaS → activar **Contactos** (`saas_module.code = contacts`)
3. **Menú:** **Comercial → Contactos** → `/admin/contacts`

Para apagar globalmente: `NODEONE_CONTACTS_MODULE_ENABLED=0` o `NODEONE_SKIP_CONTACTS_MODULE=1`.

## Rutas admin

| Ruta | Acción |
|------|--------|
| `GET /admin/contacts` | Listado + búsqueda/filtros |
| `GET/POST /admin/contacts/nuevo` | Crear |
| `GET /admin/contacts/<id>` | Detalle |
| `GET/POST /admin/contacts/<id>/editar` | Editar |
| `POST /admin/contacts/<id>/desactivar` | Desactivar (`active=false`) |

Compat: `/admin/terceros` redirige a `/admin/contacts` cuando el módulo central está activo.

## Campos del modelo

Ver `backend/models/contact.py`: tipo persona/empresa/consumidor final, datos fiscales, roles booleanos (`is_customer`, `is_supplier`, …), `active`, timestamps.

## Validaciones

- `display_name` obligatorio (o derivado de nombre/empresa/email)
- Empresa: `company_name` obligatorio
- RUC: `tax_id` obligatorio
- Consumidor final: sin RUC/DV
- Email con formato válido si se informa
- Sin duplicado `organization_id + identification_type + tax_id + dv` (índice parcial en BD)

## Multitenant

Todas las consultas filtran por `organization_id` del tenant efectivo (`admin_data_scope_organization_id` / `effective_organization_id`). Admin plataforma puede cambiar de organización en el selector habitual.

## Archivos principales

```
backend/models/contact.py
backend/nodeone/services/contacts_module.py
backend/nodeone/services/contacts_schema.py
backend/nodeone/modules/contacts/
  __init__.py
  register.py
  service.py
  admin/routes.py
templates/contacts/
  list.html, form.html, detail.html
```

## Fases siguientes (no incluidas)

- `invoice.contact_id`, `member.contact_id`, FE desde contacto
- Migración desde `tenant_crm_contact` / CRM
- API pública para checkout y pagos

## Criterios de aceptación

1. Activar módulo `contacts` en SaaS
2. Admin → Contactos
3. CRUD persona, empresa con RUC, consumidor final
4. Búsqueda y filtros por rol
5. Desactivar contacto
6. Aislamiento por organización
