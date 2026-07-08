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

**Objetivo:** pantalla “Mis aplicaciones” post-login.

```text
EasyNodeOne Platform
  Mis aplicaciones
    EPosOne
    Membership
    CRM
    Events
    Certificates
    …
```

- Si el usuario solo tiene **una** app autorizada → entrada directa.
- Visibilidad: org + perfil + App Registry.

**Base EN1:** `nodeone/core/nav_menu.py`, `sidebar_admin_areas.html`, triple filtro (SaaS + RBAC + endpoint).

**Criterio de cierre:** launcher v2 en dev; orgs IIUS/Relatic siguen en `launcher_mode=classic` hasta cutover por app.

---

### Etapa 4 — Shell de aplicaciones

**Objetivo:** cada app con layout, menú, dashboard y permisos propios.

- Reutilizar código de negocio existente (`nodeone/modules/*`).
- **No reescribir** lógica de negocio en esta etapa.

**Criterio de cierre:** al menos una app de prueba corre en shell aislado en dev (sin afectar prod).

---

### Etapa 5 — Integración de apps (una por una)

**Objetivo:** migrar **apps**, no clientes.

| Orden sugerido | App | Notas |
|----------------|-----|-------|
| 1 | **EMembership** | Primera integración; base de IIUS |
| 2 | **ECRM** | Maestro comercial transversal |
| 3 | **EEvents** | Antes de certificados |
| 4 | **ECertificates** | `depends_on`: events, membership; la más delicada |
| 5 | **EAppointments** | Relativamente aislada |

Cada app: desarrollo → staging → validación → cutover prod **solo esa app**.

**Estado por org × app:** `legacy` | `en_migracion` | `plataforma` (extensión futura de `saas_org_module` o convención por flag).

**Criterio de cierre por app:** manifest completo, shell propio, sin imports cruzados, smoke test cliente en staging, sign-off.

---

### Etapa 6 — EPosOne (app nativa)

**Objetivo:** primera app **construida nativamente** sobre la plataforma; valida el modelo.

- Solo depende del **Core** (contactos, org, usuarios, archivos, licenciamiento vía contratos).
- **No** importa Membership, Events ni Certificates.

**Criterio de cierre:** EPosOne operativo en dev/staging con launcher + shell; checklist funcional POS acordado.

---

### Etapa 7 — Back Office POS (EPosOne)

Menú propio de operación comercial:

- Dashboard, Pedidos, Ventas, Clientes, Productos, Inventario
- Sucursales, Terminales, Cajas, Turnos, Promociones, Reportes, Configuración

Puede **componer** capacidades existentes del Core (`sales`, `contacts`, inventario) sin acoplarse a apps académicas.

---

### Etapa 8 — Sincronización (bus de eventos)

**Regla:** nunca sincronizar tablas entre apps. **Eventos.**

Ejemplo:

```text
Pedido creado → Inventario → Facturación → Reportes
```

Implementación progresiva (cola, outbox, o bus interno). No bloqueante para Etapas 0–7.

---

### Etapa 9 — Nuevas apps

Todo producto nuevo nace como app registrada: Payroll, Marketing, Inventory, HR, BI, etc.

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
| **Etapa 1 Core vs Apps** | [`EN1_PLATFORM_ETAPA1_CORE_APPS.md`](EN1_PLATFORM_ETAPA1_CORE_APPS.md) |
| Deploy clientes | [`CHECKLIST_ACTUALIZACION_Y_CLIENTES.md`](CHECKLIST_ACTUALIZACION_Y_CLIENTES.md) |
| Arquitectura EN1 | [`../backend/docs/EN1_ARCHITECTURE.md`](../backend/docs/EN1_ARCHITECTURE.md) |
| RBAC | [`RBAC_Y_ROLES.md`](RBAC_Y_ROLES.md) |
| Menú ERP | [`PLAN_MENU_ERP_DOMINIOS_EN1.md`](PLAN_MENU_ERP_DOMINIOS_EN1.md) |
| Release IIUS | [`../backend/docs/IIUS_RELEASE_MANIFEST.md`](../backend/docs/IIUS_RELEASE_MANIFEST.md) |
| Reglas equipo | [`../REGLAS-DE-TRABAJO.md`](../REGLAS-DE-TRABAJO.md) |

---

*Última actualización: 2026-07-08. Cambios de alcance de etapas requieren acuerdo explícito del responsable del proyecto.*
