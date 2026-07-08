# Etapa 10 — Modelo maestro compartido (Fase 2 ETS)

**Prioridad 1 — Crítica.** Define el ADN de EasyNodeOne Platform antes de más producto comercial.

| Campo | Valor |
|-------|--------|
| Estado | **Plan acordado** (2026-07-08) — sin migración de datos ni cambio de comportamiento en IIUS/Relatic |
| Alcance edición | Solo Dev EN1 (`develop`) |
| Master plan | [`EN1_PLATFORM_MASTER_PLAN.md`](EN1_PLATFORM_MASTER_PLAN.md) |

---

## Objetivo

Un solo modelo maestro en el **Core** para entidades transversales. Las **Apps** consumen **servicios** (Etapa 11), no tablas ajenas.

**No es big bang:** inventario → decisiones → contratos → migración gradual por dominio y por cliente (Carril 3).

---

## Principios (Etapa 10)

1. **Una entidad, muchos roles** — Cliente, miembro, empleado, proveedor = `Contact` + flags/roles, no tablas paralelas de “tipo persona”.
2. **User ≠ Contact** — `User` = acceso al sistema; `Contact` = sujeto comercial/fiscal. Vínculo explícito `User.linked_contact_id` (futuro).
3. **Un catálogo de producto/servicio** — Variantes por app vía extensiones o categorías, no catálogos duplicados por vertical.
4. **Organización → Sucursal → Punto de operación** — Jerarquía única; EPosOne “Sucursales/Cajas” cuelga de ahí.
5. **Dirección normalizada** — Tabla o componente reutilizable; hoy está embebida en 4+ modelos.
6. **Archivo = Attachment Core** — Metadatos en BD; binarios en storage; apps referencian `attachment_id`.
7. **Auditoría y notificaciones** — Puntos de extensión Core; apps emiten eventos, no duplican logs.
8. **Calendario** — Servicio compartido; citas/eventos/agenda son **consumidores**, no calendarios aislados.

---

## Inventario EN1 hoy (deuda hacia maestro)

### Personas / contactos

| Fuente | Tabla / modelo | Ubicación | Tratamiento Etapa 10 |
|--------|----------------|-----------|----------------------|
| **Maestro objetivo** | `en1_contact` → `Contact` | `models/contact.py` | **Canonical** |
| Legacy fiscal/comercial | `tenant_crm_contact` | `models/saas.py` | **Converger** a `Contact` (alias temporal) |
| Login plataforma | `user` | `models/users.py` | Core; añadir `linked_contact_id` |
| Membresía pagada | `membership` | `models/benefits.py` | App; FK a `Contact` / `User` |
| CRM lead | `crm_lead` | `nodeone/modules/crm_api/models.py` | App; oportunidad, no persona maestra |
| Asesor citas | `advisor` | `models/appointments.py` | App; perfil sobre `User` |
| Participante evento | `event_participant` | `models/events.py` | App; resolver email → `Contact` |
| Estudiante | `students` | `models/academic.py` | App; `contact_id` obligatorio a medio plazo |

**Decisión v1:** `Contact` es el único maestro de terceros. Roles vía columnas `is_*` (ya existen) + tabla futura `contact_role` si hace falta granularidad.

### Productos / catálogos (fragmentados hoy)

| Catálogo | Tablas principales | App |
|----------|-------------------|-----|
| Servicios portal | `service`, `service_category` | memberships / ventas |
| Planes membresía | `membership_plan` | EMembership |
| Eventos | `event` | EEvents |
| Tipos de cita | `appointment_type` | EAppointments |
| Programas académicos | `academic_program` | Academic |
| Inventario contador | `contador_product_*` | EContador |
| Líneas venta | `quotation_lines`, `invoice_lines` | ESales — `product_id` sin FK maestro |

**Decisión v1:** Introducir `core_product` (nombre provisional) con `product_type` (`good`, `service`, `plan`, `event_sku`, …) y extensiones por app. **No migrar en Etapa 10** — solo contrato y mapa.

### Organización y locales

| Hoy | Gap |
|-----|-----|
| `saas_organization` | OK tenant |
| — | **Sin** `branch` / `location` / `store` |
| EPosOne UI `branches` | Placeholder |
| FE `default_branch`, `default_pos` | Config suelta en EFactura |

**Decisión v1:** `org_unit` (tipo: `company` \| `branch` \| `pos_terminal` \| `warehouse`) bajo `organization_id`.

### Direcciones

Embebidas en `Contact`, `TenantCrmContact`, `SaasOrganization`, `Event`, `Student`.

**Decisión v1:** `core_address` polimórfico (`owner_type`, `owner_id`, `kind`: fiscal \| delivery \| venue) o JSON schema validado en Core.

### Documentos / archivos

Filesystem disperso (`static/uploads/...`) + columnas `*_url`.

**Decisión v1:** `core_attachment` (org_id, mime, path, checksum, uploaded_by) + `AttachmentService`.

### Auditoría

| Sistema | Alcance |
|---------|---------|
| `history_transaction` | Core transversal |
| `activity_log`, `crm_lead_log`, logs FE/contador/taller | Por app |
| `platform_domain_event` | Bus dominio (Etapa 8) |

**Decisión v1:** `AuditService.log()` + eventos de dominio para acciones de negocio; consolidar lectura admin en Core.

### Notificaciones

`Notification`, `EmailLog`, `CommunicationRule`, marketing queue.

**Decisión v1:** `NotificationService.notify(channel, template, recipient_contact_id, …)` — apps no envían SMTP directo.

### Calendario

`appointments` + `ecalendar_settings` (Google) en paralelo.

**Decisión v1:** `CalendarService` con `calendar_source` (internal \| google); slots unificados a medio plazo.

---

## Modelo objetivo v1 (diagrama lógico)

```text
                    ┌─────────────────────┐
                    │  SaasOrganization   │
                    └──────────┬──────────┘
                               │
              ┌────────────────┼────────────────┐
              ▼                ▼                ▼
        ┌──────────┐    ┌────────────┐   ┌─────────────┐
        │  OrgUnit  │    │  Contact   │   │ CoreProduct │
        │ branch/   │    │  (roles)   │   │  catalog    │
        │ pos/wh    │    └─────┬──────┘   └──────┬──────┘
        └──────────┘          │                  │
              │         ┌──────┴──────┐           │
              │         │    User     │           │
              │         │ linked_contact_id      │
              │         └─────────────┘           │
              ▼                ▼                  ▼
        ┌──────────┐    ┌────────────┐    ┌─────────────┐
        │CoreAddress│    │ Attachment │    │  Apps only  │
        │(polymorphic)   │ (files)    │    │  extensions │
        └──────────┘    └────────────┘    └─────────────┘
```

---

## Qué pertenece al Core (cerrado Etapa 10)

| Dominio | Core | Apps |
|---------|------|------|
| Tenant / org / org_unit | ✅ | — |
| Contact + roles | ✅ | extensiones CRM lead, membership state |
| User + RBAC | ✅ | — |
| Product master (SKU/servicio) | ✅ | precios por app, reglas POS |
| Address | ✅ | — |
| Attachment | ✅ | — |
| Audit + domain events | ✅ | payloads específicos |
| Notifications | ✅ | plantillas por app |
| Calendar infra | ✅ | EEvents/EAppointments consumen |
| Pedido / factura / caja | ❌ | Etapa 12 (dominio comercial) — EPosOne |

---

## Reglas de código (vigentes desde Etapa 10)

1. **Apps no importan `models` de otra app** — solo Core + su propio módulo.
2. **Lectura/escritura de maestros** — vía `nodeone/core/services/*` (Etapa 11); hasta entonces, `Contact` vía módulo `contacts` documentado como shared.
3. **Legacy `tenant_crm_contact`** — no nuevas features; nuevas integraciones usan `en1_contact`.
4. **Nuevas tablas “cliente/miembro/empleado”** — prohibidas; usar `Contact` + rol.
5. **IIUS/Relatic Carril 1** — sin DDL de convergencia hasta cutover acordado por app.

---

## Fases de implementación (después del plan)

| Fase | Entrega | Riesgo |
|------|---------|--------|
| 10a | Este doc + alineación registry | Bajo |
| 10b | DDL `org_unit`, `core_address`, `core_attachment` (vacíos) | Medio |
| 10c | Puente `tenant_crm_contact` → `Contact` (lectura dual) | Alto — solo dev |
| 10d | `core_product` + mapa catálogos legacy | Alto |
| 10e | `User.linked_contact_id` + backfill | Medio |

**Etapa 10 cierra con 10a acordado.** Las fases 10b–10e son chats/tareas separados con GO explícito.

---

## Relación con prioridades ETS

| Prioridad | Etapa | Dependencia de 10 |
|-----------|-------|-------------------|
| P1 | **10 — Modelo maestro** | — |
| P2 | 11 — Servicios compartidos | Contratos de 10 |
| P3 | 12 — Dominio comercial | Contact + Product + OrgUnit |
| P4 | 13 — Sync offline | Event bus + entidades estables |
| P5 | 14 — EPosOne MVP | 10–13 |

**EPayroll congelado** hasta validar EPosOne MVP con clientes reales (scaffold en dev no bloquea).

---

## Criterio de cierre — Etapa 10 (plan)

| # | Criterio | Estado |
|---|----------|--------|
| 1 | Inventario deuda publicado | Hecho |
| 2 | Decisiones v1 por dominio | Hecho |
| 3 | Diagrama + reglas Core vs App | Hecho |
| 4 | Roadmap Fase 2 en Master Plan | Hecho |
| 5 | Cero cambio comportamiento prod legacy | Hecho (solo docs) |

**Siguiente chat recomendado:** **GO Etapa 11 — ContactService** (primer servicio compartido) o **GO Etapa 10b — DDL org_unit** si preferís materializar esquema antes.

---

*Etapa 10 plan — 2026-07-08. Cambios de modelo requieren actualizar este doc y acuerdo del responsable.*
