# Etapa 1 — Fronteras Core vs Apps

**EasyNodeOne Platform · Definición (sin mover código)**

| Campo | Valor |
|-------|--------|
| Etapa | 1 — Nacimiento de la plataforma (solo definición) |
| Estado | Cerrada (documento rector) |
| Master Plan | [`EN1_PLATFORM_MASTER_PLAN.md`](EN1_PLATFORM_MASTER_PLAN.md) |
| Operativa carriles | [`EN1_PLATFORM_CARRILES_Y_SOPORTE.md`](EN1_PLATFORM_CARRILES_Y_SOPORTE.md) |

---

## Objetivo de esta etapa

Separar **mentalmente y documentalmente** qué es **Core** y qué es **App**, usando el código EN1 actual como mapa.

- **No** crear otro producto ni otro repositorio.
- **No** mover archivos ni refactorizar en esta etapa.
- **No** cambiar comportamiento en IIUS/Relatic (Carril 1).

La Etapa 2 tomará este documento como contrato para extraer/formalizar el paquete Core en código.

---

## Glosario

| Término | Definición |
|---------|------------|
| **Plataforma** | EasyNodeOne Platform: Core + App Registry + Launcher + conjunto de apps |
| **Core** | Capacidades transversales sin reglas de negocio de un producto vertical |
| **App** | Solución con dominio propio: menú, dashboard, permisos y ciclo de vida independientes |
| **App Registry** | Catálogo formal de apps (`saas_module` hoy → manifest formal en Etapa 2) |
| **Shared Service (Core)** | Maestro o servicio transversal consumido por varias apps vía contrato/API Core |
| **Legacy** | Implementación actual EN1 de una app; sigue en Carril 1 hasta cutover |
| **Plataforma (runtime)** | App envuelta en shell nuevo; mejoras solo en Carril 2/3 |
| **`depends_on`** | App B requiere que la org tenga app A habilitada; sin imports cruzados |
| **Carril** | 1 Producción · 2 Plataforma · 3 Integración (ver doc carriles) |

---

## Reglas de clasificación

### Una pieza de código es **Core** si:

1. La necesitan **dos o más apps** sin conocer el dominio de la otra app.
2. Es **infraestructura**: auth, tenant, RBAC, archivos, auditoría, licenciamiento.
3. Es un **maestro transversal** acordado (ej. contactos/terceros, usuarios).
4. **No** contiene reglas de negocio de membresía, eventos, certificados, POS, académico, etc.

### Una pieza de código es **App** si:

1. Implementa un **dominio de producto** vendible o activable por tenant.
2. Tiene **menú y permisos** propios en el launcher.
3. Puede estar **apagada** por org (`saas_org_module`) salvo apps marcadas core-infrastructure.

### Prohibido (regla de oro, objetivo Etapa 2+):

- `import` directo entre apps (`events` → `certificates` en código de app).
- Lógica de negocio nueva en `app.py` monolito o en paquete Core.
- Dependencias no declaradas en App Registry.

### Permitido temporalmente (deuda EN1, retirar en integración):

- Imports cruzados legacy hasta que la app migre a shell plataforma.
- Modelos aún en `app.py` (events, etc.) — mover con la app en Etapa 5.

---

## Core — definición oficial (Etapa 1)

### Capas del Core

```text
┌─────────────────────────────────────────────────────────┐
│  Plataforma UI (futuro)                                 │
│  Launcher · org switcher · shell mínimo · admin SA       │
├─────────────────────────────────────────────────────────┤
│  Licenciamiento                                         │
│  App Registry · tenant apps · user apps · guards SaaS   │
├─────────────────────────────────────────────────────────┤
│  Seguridad                                              │
│  Login · sesión · OAuth · MFA (futuro) · JWT API        │
├─────────────────────────────────────────────────────────┤
│  Tenant                                                 │
│  Organizaciones · multiempresa · branding · config      │
├─────────────────────────────────────────────────────────┤
│  Identidad y acceso                                     │
│  Usuarios · roles · permisos · invitaciones             │
├─────────────────────────────────────────────────────────┤
│  Servicios compartidos                                  │
│  Archivos · notificaciones · email · auditoría · API    │
│  Contactos (maestro) · pagos (infra) · IA (servicio)    │
└─────────────────────────────────────────────────────────┘
```

### Inventario Core → código EN1 hoy

| Capacidad Core | Ubicación actual | Notas Etapa 2 |
|----------------|------------------|---------------|
| **Auth / OAuth** | `_app/modules/auth`, `register_auth_blueprint` | Mantener; facade en Core |
| **Sesión / Flask-Login** | `app.py`, Flask-Login | Core |
| **Organizaciones** | `models/saas.py` (`SaasOrganization`) | Core |
| **Resolución tenant** | `utils/organization.py` | Core |
| **Usuarios** | `models/users.py` | Core |
| **RBAC** | `models/users.py`, `admin_users_roles`, `docs/RBAC_Y_ROLES.md` | Core |
| **App Registry (catálogo)** | `saas_catalog_defaults.py`, `models/saas.py` | Core; formalizar manifest |
| **Guards / licenciamiento** | `saas_features.py`, `saas_module_cache.py` | Core |
| **Admin plataforma (SA)** | `register_admin_platform_org_routes`, org SaaS admin | Core |
| **Archivos / media** | `media_admin`, uploads | Core |
| **Config / branding** | `OrganizationSettings`, `NODEONE_BRAND_PRESET` | Core |
| **Email / notificaciones** | `email_service`, colas marketing | Core infra; campañas = app Marketing |
| **API base / org switch** | `register_public_and_org_switch_routes`, APIs usuario | Core |
| **Pagos (infraestructura)** | `_app/modules/payments`, `payment_processors.py` | Core (`is_core=True`); apps orquestan cobro |
| **Contactos (maestro)** | `nodeone/modules/contacts`, `admin_tenant_contacts` | **Shared Service Core** |
| **IA / chatbot** | módulo `chatbot`, `register_ai_api_blueprint` | **Core servicio**; apps consumen |
| **Historial / auditoría** | `history_admin`, logs | Core |
| **Backup / export admin** | `admin_backup`, `admin_export` | Core operaciones |
| **Permisología EN1** | `rbac_matrix` | Core administración |

### Qué **no** es Core (ejemplos explícitos)

| Lógica | Por qué es App |
|--------|----------------|
| Planes y beneficios de membresía | Dominio EMembership |
| Inscripción y descuentos de eventos | Dominio EEvents |
| Emisión y plantillas de certificados | Dominio ECertificates |
| Tipos de cita y disponibilidad advisor | Dominio EAppointments |
| Kanban CRM, leads, actividades | Dominio ECRM |
| Cotizaciones, taller, órdenes SLA | Dominio Ventas / Taller |
| Matrícula académica Moodle | Dominio Academic (IIUS) |
| POS, cajas, turnos | Dominio EPosOne (futuro nativo) |
| Emisión FE PAC | Dominio EFactura |

---

## Catálogo de Apps — definición oficial (Etapa 1)

Cada fila es una **App de plataforma** (presente o futura). Columna **EN1 hoy** = dónde vive el código sin moverlo.

| App ID | Nombre | Código SaaS | EN1 hoy (código) | `depends_on` | Integración (orden) | Clientes típicos |
|--------|--------|-------------|------------------|--------------|---------------------|------------------|
| `emembership` | EMembership | `memberships` | `_app/modules/members`, `register_admin_dashboard_memberships_routes`, benefits/plans | — | **1ª** | IIUS, Relatic |
| `ecrm` | ECRM | `crm`, `crm_contacts` | `nodeone/modules` CRM, kanban, reports | `contacts` (Core) | **2ª** | Relatic |
| `eevents` | EEvents | `events` | `nodeone/modules/events` | `contacts` (opcional) | **3ª** | IIUS |
| `ecertificates` | ECertificates | `certificates` | `nodeone/modules/certificates` | `events`, `memberships` | **4ª** | IIUS, Relatic |
| `eappointments` | EAppointments | `appointments` | `nodeone/modules/appointments`, ecalendar | — | **5ª** | IIUS |
| `academic` | Academic / LMS | `academic` | `academic_enrollment`, program routes | `memberships` (flujos IIUS) | Bundle IIUS | IIUS |
| `esales` | Ventas | `sales` | `sales_accounting`, quotations | `contacts` | Componer EPosOne | Varios |
| `eworkshop` | Taller | `workshop` | `nodeone/modules/workshop` | `contacts`, `sales` (opc.) | Opcional | Talleres |
| `econtador` | Contador / inventario | `contador` | módulo contador | `contacts` | Componer EPosOne | Inventario |
| `efactura` | EFactura | `efactura` | `nodeone/modules/efactura` | `contacts`, `sales` | Posterior | PA fiscal |
| `emarketing` | EMarketing | `marketing_email` | `marketing`, comunicaciones campañas | `communications` | Etapa 9 | Marketing |
| `ecommunications` | Comunicaciones | `communications` | `admin_communications` | — | Soporte apps | Varios |
| `eanalytics` | Analítica | `analytics` | `admin_analytics` | varias (lectura) | Posterior | BI ligero |
| `eoffice365` | Office 365 | `office365` | office365 admin | — | Opcional | IIUS |
| `eposone` | EPosOne | `eposone` *(nuevo)* | **No existe** — nativa Etapa 6 | Core + `contacts` + shared inventario/ventas | **Nativa** | Restaurantes, retail |
| `epolicies` | Normativas | `policies` | `_app/modules/policies` | — | Baja prioridad | Público legal |
| `eqr` | Generador QR | `qr_generator` | `qr_generator`, `qr_tools` | — | Herramienta | Varios |

### Apps de administración / herramientas (no producto vertical)

| App ID | Código SaaS | Tratamiento |
|--------|-------------|-------------|
| `rbac_matrix` | `rbac_matrix` | UI Core — administración permisos |
| `security_matrix` | `security_matrix` | Herramienta import Odoo; opcional por tenant |

---

## Shared Services del Core (decisiones Etapa 1)

Piezas que **no son apps vendibles** pero tampoco son “negocio vertical”:

| Servicio | Decisión | Consumidores |
|----------|----------|--------------|
| **Contactos / terceros** | Core (`contacts`) | ECRM, Ventas, EFactura, EPosOne |
| **Pagos (checkout, Stripe, PayPal, Yappy)** | Core infra (`payments`, `is_core=True`) | Todas las apps que cobran |
| **Email transaccional** | Core | Todas |
| **Archivos** | Core | Todas |
| **IA / chatbot** | Core servicio | Apps que configuren asistentes |
| **Portal miembro (shell)** | Core UX | Apps exponen widgets/secciones; campus IIUS agrega Academic + Events + Certificates |

---

## Bundles por cliente (referencia)

No son apps; son **presets de activación** para onboarding y migración.

### IIUS

| App | Runtime hoy | Carril cambios hoy |
|-----|-------------|-------------------|
| EMembership | Legacy | 1 |
| EEvents | Legacy | 1 |
| ECertificates | Legacy | 1 |
| EAppointments | Legacy | 1 |
| Academic | Legacy | 1 |
| EOffice365 | Legacy (si activo) | 1 |

### Relatic

| App | Runtime hoy | Carril cambios hoy |
|-----|-------------|-------------------|
| ECRM | Legacy | 1 |
| EMembership | Legacy | 1 |
| ECertificates | Legacy | 1 |
| EEvents | Legacy (si activo) | 1 |

### EPosOne (futuro)

| App | Runtime |
|-----|---------|
| EPosOne | Solo Plataforma (Carril 2) — nunca Legacy |
| ECRM | Plataforma |
| Contactos | Core |

---

## Mapa físico del repo (sin mover)

```text
backend/
├── app.py                    # Monolito — objetivo Etapa 2: solo factory + facades Core
├── models/                   # Mixto — Etapa 2+: marcar core vs app en comentarios/manifest
├── _app/modules/             # Legacy pack — destino: Core (auth, payments) o Apps (members, policies)
├── nodeone/
│   ├── core/                 # features.py, nav_menu.py → Launcher/Registry en Etapa 2–3
│   ├── modules/              # Una carpeta ≈ una App (objetivo)
│   └── services/             # Mayoría Core + shared services
├── saas_features.py          # Core
└── utils/organization.py     # Core
```

### Manifests existentes (prototipo App Registry)

| Módulo | Archivo | `depends_on` declarado |
|--------|---------|------------------------|
| Certificates | `certificates/manifest.py` | `events`, `membership` |
| Events | `events/manifest.py` | `[]` |
| Appointments | `appointments/manifest.py` | `[]` |

En Etapa 2 el manifest pasa a ser la fuente única para registro + nav + SaaS.

---

## Portal miembro vs Back Office

| Superficie | Clasificación Etapa 1 |
|------------|----------------------|
| **Back Office admin** | Cada App tiene el suyo (Etapa 4 shell) |
| **Launcher** | Core (Etapa 3) |
| **Portal miembro / campus** | Core shell + secciones aportadas por apps (Membership, Events, Certificates, Academic) |
| **Login / registro / org** | Core |

IIUS no “migra el portal entero”; migra **app por app** dentro del mismo host.

---

## Criterios de cierre — Etapa 1

| # | Criterio | Estado |
|---|----------|--------|
| 1 | Glosario Core/App/Plataforma/Carril publicado | Hecho |
| 2 | Inventario Core con ubicación EN1 | Hecho |
| 3 | Catálogo Apps con SaaS, depends_on, orden integración | Hecho |
| 4 | Decisiones Shared Services (contactos, pagos, IA) | Hecho |
| 5 | Bundles IIUS / Relatic / EPosOne | Hecho |
| 6 | Reglas clasificación para tickets nuevos | Hecho |
| 7 | **Cero cambios de comportamiento en prod** | Hecho (solo docs) |

**Siguiente etapa:** [Etapa 2 — Construcción del Core](EN1_PLATFORM_MASTER_PLAN.md#etapa-2--construcción-del-core) — paquete `nodeone/core/platform/`, tests humo, sin romper Carril 1.

---

## Plantilla — clasificar trabajo nuevo

```text
¿Es infraestructura o maestro transversal?     → Core
¿Es dominio activable por tenant con menú?    → App (¿cuál ID?)
¿Dos apps necesitan el mismo dato?             → Shared Service Core, no import cruzado
¿Cliente IIUS/Relatic Legacy?                 → Carril 1 salvo app ya en Plataforma
¿App nueva nativa (EPosOne)?                  → Carril 2, manifest desde día 1
```

---

*Etapa 1 cerrada — 2026-07-08. Modificaciones de fronteras Core/App requieren actualizar este doc y acuerdo del responsable.*
