# MASTER PLAN — EasyNodeOne Platform

**Transformación de EN1 hacia una Plataforma de Aplicaciones**

| Campo | Valor |
|-------|--------|
| Versión | 1.0 |
| Estado | Aprobado (transición controlada, no migración big bang) |
| Alcance edición | Solo `/opt/easynodeone/dev/app` (Dev EN1) |
| Documento operativo | [`EN1_PLATFORM_CARRILES_Y_SOPORTE.md`](EN1_PLATFORM_CARRILES_Y_SOPORTE.md) |

---

## Objetivo estratégico

**No construir EPosOne como fin.** Construir **EasyNodeOne Platform** sin poner en riesgo a IIUS, Relatic ni las organizaciones en producción.

No es una migración. Es una **transición controlada**: cada aplicación evoluciona con su propio ciclo de vida; los clientes adoptan apps de forma individual, nunca el sistema completo de una vez.

---

## Principios (reglas de arquitectura)

### Regla 1 — Soporte permanente

IIUS y Relatic **nunca** pueden quedar sin soporte. Congelación ≠ abandono.

### Regla 2 — Producción protegida

La plataforma nueva **nunca** debe romper producción. Nada de `develop` desplegado a silos de clientes sin tag explícito.

### Regla 3 — Apps individuales

Las apps migran **una por una**. No existe migración “todo o nada” de un cliente.

### Regla 4 — Core sin negocio

El Core **no** contiene lógica de negocio (membresías, eventos, certificados, POS, etc.). Solo plataforma, maestros transversales y servicios compartidos acordados.

### Regla 5 — App autónoma en UX

Cada app posee: menú propio, dashboard propio, permisos propios, navegación propia.

### Regla 6 — Sin dependencias cruzadas entre apps

Las apps dependen **solo del Core**. Las dependencias funcionales (ej. Certificates → Events + Membership) se declaran en el **App Registry** (`depends_on`) y se resuelven por contratos/servicios del Core, no por `import` directo entre apps.

---

## Tres carriles permanentes

```text
Carril 1 — Producción     IIUS, Relatic          → solo hotfixes desde tag congelado
Carril 2 — Plataforma      Core, Registry, Launcher, EPosOne, apps nativas  → develop
Carril 3 — Integración     Apps individuales      → staging → cutover por app
```

Detalle operativo (tags, ramas, tickets, smoke tests): [`EN1_PLATFORM_CARRILES_Y_SOPORTE.md`](EN1_PLATFORM_CARRILES_Y_SOPORTE.md).

---

## Etapas

### Etapa 0 — Congelar producción

**Objetivo:** proteger clientes existentes.

| Cliente | Estado | Permitido | Prohibido |
|---------|--------|-----------|-----------|
| **IIUS** | Producción congelada | Hotfixes, soporte, incidencias críticas | Refactor, arquitectura nueva, deploy de `develop` |
| **Relatic** | Producción congelada | Idem | Idem |

**Referencias Git (IIUS):**

| Referencia | Uso |
|------------|-----|
| Tag `iius-freeze-20260527` | Línea base congelada IIUS |
| Tag `iius-go-20260522` | Release operativo mayo 2026 |
| Rama sugerida `release/iius-maint` | Hotfixes desde tag congelado |
| Validación | `backend/scripts/go_iius_validate_all.sh` |

**Relatic:** tag `relatic-freeze-20260708` en commit `86b8bca` (estado silo al 2026-07-08). Rama `release/relatic-maint`. Ver [`EN1_PLATFORM_CARRILES_Y_SOPORTE.md`](EN1_PLATFORM_CARRILES_Y_SOPORTE.md).

**Resultado:** IIUS y Relatic en **mantenimiento** con carril de soporte activo.

**Criterio de cierre Etapa 0:** tags documentados, ramas `release/*-maint` creadas, regla de equipo “solo tag a prod/relatic” comunicada.

---

### Etapa 1 — Nacimiento de EasyNodeOne Platform

**Objetivo:** separar mentalmente **Core** vs **Apps**. Todavía **no mover código**.

- No crear otro producto ni duplicar lógica.
- Mismo repo, misma base de evolución (`/opt/easynodeone/dev/app`).
- Entregable: **[`EN1_PLATFORM_ETAPA1_CORE_APPS.md`](EN1_PLATFORM_ETAPA1_CORE_APPS.md)** (glosario, inventario, catálogo apps, reglas clasificación).

**Criterio de cierre:** documento Etapa 1 publicado; ningún cambio de comportamiento en prod. **Estado: cerrada (2026-07-08).**

---

### Etapa 2 — Construcción del Core

**Objetivo:** el Core nace oficialmente como paquete/contrato explícito.

Paquete: `backend/nodeone/core/platform/` · tests: `backend/tests/platform/test_core_smoke.py`

| Área | Capacidades |
|------|-------------|
| **Seguridad** | Login, sesión, JWT, OAuth, MFA |
| **Plataforma** | Organizaciones, multiempresa, usuarios, roles, permisos |
| **Servicios** | Archivos, auditoría, configuración, API, notificaciones, IA |
| **Licenciamiento** | App Registry, tenant apps, user apps |

**Resultado:** `register_platform_core` + `register_platform_apps`; facades `runtime.py`; registry declarativo.

**Criterio de cierre:** paquete platform publicado, tests humo Core OK, `register_modules` delega sin cambiar blueprints. **Estado: cerrada (2026-07-08).**

---

### Etapa 3 — Launcher

**Objetivo:** pantalla «Mis aplicaciones» post-login.

- Ruta `/platform/apps` · selección POST · `/platform/apps/switch`
- Si una sola app autorizada → entrada directa.
- Visibilidad: mismas reglas que sidebar ERP (`visible_areas` + SaaS + RBAC).
- **Modo classic** por defecto (IIUS/Relatic sin cambio).
- Activar en dev: `NODEONE_LAUNCHER_APPS_ORG_IDS=1` o `NODEONE_LAUNCHER_MODE=apps`.
- Excluir org: `NODEONE_LAUNCHER_CLASSIC_ORG_IDS`.

**Código:** `nodeone/core/platform/launcher.py`, `nodeone/modules/platform_launcher/`, `templates/platform/apps_launcher.html`.

**Criterio de cierre:** launcher v2 en dev; prod clientes en classic hasta cutover. **Estado: cerrada (2026-07-08).**

---

### Etapa 4 — Shell de aplicaciones

**Objetivo:** cada app con layout, menú y subnav propios reutilizando código existente.

- Con `NODEONE_LAUNCHER_APPS_ORG_IDS` + app activa en sesión → shell aislado.
- Sidebar mínimo (`platform_app_shell_sidebar.html`) + banner + subnav horizontal.
- Sincroniza `platform_active_app_id` con la URL visitada.
- **Classic** sin cambios para IIUS/Relatic.

**Código:** `nodeone/core/platform/app_shell.py`, partials y `platform-app-shell.css`.

**Criterio de cierre:** al menos una app en shell aislado en dev. **Estado: cerrada (2026-07-08).**

---

### Etapa 5 — Integración de apps

**Objetivo:** migrar **apps**, no clientes. Primera app: **EMembership**.

| Pieza | Ubicación |
|-------|-----------|
| Runtime org × app | `platform_org_app_runtime` · `models/platform_app.py` |
| Servicio | `nodeone/core/platform/app_integration.py` |
| Manifest EMembership | `nodeone/modules/emembership/manifest.py` |
| DDL bootstrap | `nodeone/services/platform_app_runtime_schema.py` |

**Estados:** `legacy` | `en_migracion` | `plataforma`

**Activar EMembership en dev (sin tocar IIUS/Relatic):**

```bash
# Opción A — BD (tras bootstrap)
export NODEONE_PLATFORM_SEED_EMEMBERSHIP_ORG_IDS=1
sudo systemctl restart easynodeone-dev

# Opción B — solo env
export NODEONE_APP_RUNTIME_EMEMBERSHIP_ORG_IDS=1
export NODEONE_APP_RUNTIME_EMEMBERSHIP=plataforma
```

Con runtime `plataforma`, la org entra en modo apps automáticamente y el launcher muestra solo apps integradas.

**EAppointments (5ª app) — activar en dev:**

```bash
export NODEONE_PLATFORM_SEED_EAPPOINTMENTS_ORG_IDS=1
sudo systemctl restart easynodeone-dev
```

Manifest: `nodeone/modules/eappointments/manifest.py`.

**Etapa 5 cerrada en dev (2026-07-08):** EMembership, ECRM, EEvents, ECertificates y EAppointments integradas. Cutover prod por app y cliente vía Carril 3.

**Criterio de cierre:** las 5 apps del plan con manifest + runtime + tests en dev. **Estado: cerrada (2026-07-08).**

---

### Etapa 6 — EPosOne (app nativa)

**Objetivo:** primera app **construida nativamente** sobre la plataforma; valida el modelo.

- Solo depende del **Core** (contactos, org, usuarios, archivos, licenciamiento vía contratos).
- **No** importa Membership, Events ni Certificates.

| Pieza | Ubicación |
|-------|-----------|
| Manifest | `nodeone/modules/eposone/manifest.py` |
| Rutas / home | `nodeone/modules/eposone/routes.py` |
| Módulo SaaS | `eposone` en `saas_catalog_defaults.py` (opt-in, no en toggleable global) |
| Nav / launcher | área `eposone` en `nav_menu.py` + `launcher.py` |

**Activar EPosOne en dev:**

```bash
export NODEONE_PLATFORM_SEED_EPOSONE_ORG_IDS=1
sudo systemctl restart easynodeone-dev
```

El seed marca runtime `plataforma` y habilita `saas_org_module` para `eposone` en esas orgs.

**Criterio de cierre:** EPosOne operativo en dev con launcher + shell; home en `/admin/eposone/`. Back office POS completo → Etapa 7.

**Estado Etapa 6 (scaffold):** implementado en dev (2026-07-08).

**Criterio de cierre Etapa 6:** home/dashboard en `/admin/eposone/` con launcher + shell. **Cerrada (2026-07-08).**

---

### Etapa 7 — Back Office POS (EPosOne)

Menú propio de operación comercial:

- Dashboard, Pedidos, Ventas, Clientes, Productos, Inventario
- Sucursales, Terminales, Cajas, Turnos, Promociones, Reportes, Configuración

Puede **componer** capacidades existentes del Core (`sales`, `contacts`, inventario) sin acoplarse a apps académicas.

| Pieza | Ubicación |
|-------|-----------|
| Menú shell | `nav_menu.py` área `eposone` |
| Rutas nativas | `/admin/eposone/section/<slug>` · `eposone/sections.py` |
| Dashboard | `templates/eposone/dashboard.html` |
| Compose Core | enlaces condicionados en dashboard + ítems nav a ventas/contactos/contador |

**Estado Etapa 7 (scaffold):** menú back office + pantallas nativas placeholder + composición Core en dev (2026-07-08). Lógica transaccional POS y KPIs → iteraciones posteriores / Etapa 8 (eventos).

---

### Etapa 8 — Sincronización (bus de eventos)

**Regla:** nunca sincronizar tablas entre apps. **Eventos.**

Ejemplo:

```text
Pedido creado → Inventario → Facturación → Reportes
```

| Pieza | Ubicación |
|-------|-----------|
| Outbox | `platform_domain_event` · `models/platform_events.py` |
| API bus | `nodeone/core/platform/events.py` — `publish_domain_event`, `subscribe`, `dispatch_pending_events` |
| DDL bootstrap | `nodeone/services/platform_events_schema.py` |
| EPosOne helpers | `nodeone/modules/eposone/events.py` |

**Env dev:** `NODEONE_EVENT_BUS_SYNC=1` (default) despacha handlers en el mismo proceso tras commit.

**Estado Etapa 8 (scaffold):** outbox + bus in-process + tests en dev (2026-07-08). Cola/worker externo → iteración futura.

---

### Etapa 9 — Nuevas apps

Todo producto nuevo nace como app registrada: Payroll, Marketing, Inventory, HR, BI, etc.

| Pieza | Ubicación |
|-------|-----------|
| Descubrimiento manifests | `nodeone/core/platform/manifest_registry.py` |
| Plantilla nueva app | `NEW_APP_MANIFEST_TEMPLATE` en manifest_registry |
| Ejemplo planificada | `nodeone/modules/epayroll/manifest.py` (`lifecycle: planned`) |
| Registry + SaaS | `app_registry.py` + `saas_catalog_defaults.py` |

**Checklist nueva app (Carril 2):**

1. Crear `nodeone/modules/<app>/manifest.py` (y `register.py` + rutas si `lifecycle: active`).
2. Añadir módulo a `PLATFORM_MANIFEST_MODULES`.
3. Registrar `ApplicationDescriptor` en `app_registry.py`.
4. Añadir código SaaS opt-in en `saas_catalog_defaults.py` (no toggleable global salvo acuerdo).
5. Nav + launcher mapping si tiene UI.
6. Tests en `tests/platform/`.
7. Eventos de dominio vía bus (Etapa 8), sin sync de tablas entre apps.

**Estado Etapa 9 (scaffold):** manifest_registry + EPayroll scaffold en dev (2026-07-08).

**Nota estratégica:** EPayroll queda **congelado en producto** hasta cerrar EPosOne MVP (Etapa 14) y validar con clientes. El scaffold en dev no implica desarrollo de nómina legal.

---

## Fase 2 ETS — Post-plataforma (Etapas 10–30)

**Regla de oro:** no más funcionalidades de producto hasta consolidar base (Etapas 10–13). EPosOne MVP es el primer producto comercial; EPayroll y demás apps **después** de validar la plataforma.

### Prioridades reales

| P | Etapa | Nombre | Estado |
|---|-------|--------|--------|
| **P1** | **10** | **Modelo maestro compartido** | **Plan cerrado** — [`EN1_PLATFORM_ETAPA10_MODELO_MAESTRO.md`](EN1_PLATFORM_ETAPA10_MODELO_MAESTRO.md) |
| **P2** | **11** | **Servicios compartidos (APIs Core)** | **Cerrado en dev** — `nodeone/core/services/` |
| P3 | 12 | Dominio comercial (pedido, pago, factura, caja, POS) | Pendiente |
| P4 | 13 | Sincronización offline (cola, reintentos, conflictos) | Pendiente |
| P5 | 14 | **EPosOne MVP comercial** | Pendiente |
| — | 15–18 | KDS, Delivery, Menú digital, FE Panamá | Post-MVP POS |
| — | 19 | EPayroll (motor legal) | **Después de EPosOne validado** |
| — | 20–24 | CRM, Membership, Events, Certificates, Appointments | Migración por app |
| — | 25–30 | Marketplace, APIs públicas, IA, Observabilidad, Multiempresa, Plataforma ETS | Largo plazo |

### Secuencia acordada

```text
Consolidar plataforma (10 → 11 → 12 → 13)
    → EPosOne MVP (14)
    → Validar 1–2 clientes reales
    → EPayRoll, CRM, Membership, …
```

### Etapa 10 — resumen

- **Contact** (`en1_contact`) = maestro de terceros con roles; converger `tenant_crm_contact`.
- **Un catálogo** producto/servicio (contrato `core_product` — diseño, sin migrar aún).
- **OrgUnit** para sucursales/locales/cajas.
- **Address, Attachment, Audit, Notification, Calendar** como servicios Core.
- **Sin big bang** en IIUS/Relatic.

### Etapa 11 — resumen

Paquete `backend/nodeone/core/services/` — APIs internas para Apps (sin ORM expuesto):

| Servicio | Estado | Delegación / notas |
|----------|--------|-------------------|
| `ContactService` | Activo | `nodeone.modules.contacts.service` → `ContactDTO` |
| `OrganizationService` | Activo | `resolve_organization_id` + `SaasOrganization` |
| `AuditService` | Activo | `publish_domain_event` + `HistoryLogger.log_system_action` |
| `NotificationService` | Activo | `CommunicationEngine.trigger` |
| `ProductService` | Stub | Pendiente `core_product` (Etapa 10d) |
| `DocumentService` | Stub | Pendiente `core_attachment` (Etapa 10b) |
| `CalendarService` | Stub | Pendiente convergencia con EAppointments |

**Consumidor ejemplo:** EPosOne eventos usan `AuditService.publish_domain_event`. Tests: `tests/platform/test_core_services.py`.

---

Detalle completo: [`EN1_PLATFORM_ETAPA10_MODELO_MAESTRO.md`](EN1_PLATFORM_ETAPA10_MODELO_MAESTRO.md).

---

## Ciclo de vida de una app

```text
Idea → Diseño → Core Contracts → Desarrollo → Staging → Producción → Legacy → Retiro
```

Cada app evoluciona sola.

---

## Ciclo de vida de un cliente (cambio fundamental)

**Los clientes no migran completos. Migran por aplicación.**

### Ejemplo IIUS

| Momento | EMembership | ECertificates | EEvents |
|---------|-------------|---------------|---------|
| Hoy | Legacy | Legacy | Legacy |
| +3 meses | **Plataforma** | Legacy | Legacy |
| +6 meses | Plataforma | **Plataforma** | Legacy |
| Después | Plataforma | Plataforma | **Plataforma** |

Nunca todo junto.

---

## Soporte según estado de la app

| Estado app para el cliente | Dónde se hacen mejoras funcionales |
|-----------------------------|-------------------------------------|
| **Legacy** | Carril 1 (hotfix desde tag) o código legacy en repo |
| **En migración** | Carril 3 (staging); prod no hasta sign-off |
| **Plataforma** | Carril 2 (`develop`); legacy de esa app en solo hotfixes de seguridad hasta retiro |

No se obliga al cliente a migrar una app hasta que esté lista y acordada.

---

## Gestión de riesgo

| Riesgo | Mitigación |
|--------|------------|
| Refactor rompe IIUS/Relatic | Etapa 0 + carril 1 |
| Big bang | Regla 3 + carril 3 por app |
| Dos implementaciones eternas | Fecha de retiro legacy por app al declarar Plataforma |
| Imports cruzados | Regla 6 + manifest `depends_on` |
| Deploy accidental de develop | Reglas de desarrollo + checklist deploy |

---

## Reglas de desarrollo

1. **Nunca** desarrollar directamente sobre producción (silos prod/relatic).
2. **Nunca** desplegar `develop` a IIUS/Relatic.
3. Toda app nueva se registra en el **App Registry**.
4. Toda app depende **únicamente** del Core.
5. Dependencias funcionales vía Registry + Core, no imports entre apps.
6. Cada ticket indica: **App**, **Cliente**, **Estado app**, **Carril** (ver plantilla en carriles).

---

## Visión final

```text
                EasyNodeOne Platform
                         Core
──────────────────────────────────────────
EPosOne    EMembership    ECRM    EEvents
ECertificates    EAppointments    EPayments
EMarketing    EPayRoll    EInventory    BI
──────────────────────────────────────────
               Todos usan el mismo Core
```

---

## Decisiones estratégicas (resumen)

1. IIUS y Relatic congelados **funcionalmente**, con soporte y hotfixes continuos.
2. No habrá migración big bang; cada app tiene su plan de transición.
3. EPosOne es la primera app **nativa** de plataforma (validación del modelo).
4. El Core es el activo principal de ETS: auth, multiempresa, permisos, API, auditoría, licenciamiento.
5. La **plataforma** es el producto; las **apps** son soluciones independientes sobre el mismo núcleo.

---

## Apéndice A — Inventario inicial Core vs Apps (EN1 hoy)

### Core (objetivo Etapa 2)

| Componente | Ubicación actual |
|------------|------------------|
| Auth / OAuth | `_app/modules/auth` |
| Organizaciones / tenant | `models/saas.py`, `utils/organization.py` |
| Usuarios / RBAC | `models/users.py`, `docs/RBAC_Y_ROLES.md` |
| Catálogo tenant | `saas_module`, `saas_org_module`, `saas_catalog_defaults.py` |
| Guards / licenciamiento | `saas_features.py`, `saas_module_cache.py` |
| Archivos / media | `media_admin`, uploads |
| Config / branding | `OrganizationSettings`, presets |
| API transversal | rutas base en `app.py` |
| Notificaciones / email | `email_service`, colas |
| IA / chatbot | módulo `chatbot` (evaluar Core vs app) |

### Apps (objetivo envoltorio Etapa 4–5)

| App futura | Módulo EN1 actual | Código SaaS |
|------------|-------------------|-------------|
| EMembership | `_app/modules/members`, memberships | memberships |
| EEvents | `nodeone/modules/events` | events |
| ECertificates | `nodeone/modules/certificates` | certificates |
| EAppointments | `nodeone/modules/appointments` | appointments |
| ECRM | `nodeone/modules` CRM + contacts | crm, crm_contacts, contacts |
| Academic (IIUS) | `academic_enrollment` | academic |
| EPosOne | **nuevo** (nativo Etapa 6) | eposone (nuevo) |

### Manifest existente (prototipo Registry)

`backend/nodeone/modules/certificates/manifest.py` — extender este patrón al App Registry formal.

---

## Apéndice B — Documentos relacionados

| Tema | Archivo |
|------|---------|
| Carriles y soporte | [`EN1_PLATFORM_CARRILES_Y_SOPORTE.md`](EN1_PLATFORM_CARRILES_Y_SOPORTE.md) |
| **Etapa 10 modelo maestro** | [`EN1_PLATFORM_ETAPA10_MODELO_MAESTRO.md`](EN1_PLATFORM_ETAPA10_MODELO_MAESTRO.md) |
| Deploy clientes | [`CHECKLIST_ACTUALIZACION_Y_CLIENTES.md`](CHECKLIST_ACTUALIZACION_Y_CLIENTES.md) |
| Arquitectura EN1 | [`../backend/docs/EN1_ARCHITECTURE.md`](../backend/docs/EN1_ARCHITECTURE.md) |
| RBAC | [`RBAC_Y_ROLES.md`](RBAC_Y_ROLES.md) |
| Menú ERP | [`PLAN_MENU_ERP_DOMINIOS_EN1.md`](PLAN_MENU_ERP_DOMINIOS_EN1.md) |
| Release IIUS | [`../backend/docs/IIUS_RELEASE_MANIFEST.md`](../backend/docs/IIUS_RELEASE_MANIFEST.md) |
| Reglas equipo | [`../REGLAS-DE-TRABAJO.md`](../REGLAS-DE-TRABAJO.md) |

---

*Última actualización: 2026-07-08 (Fase 2 Etapas 10–30 añadidas). Cambios de alcance requieren acuerdo explícito del responsable del proyecto.*
