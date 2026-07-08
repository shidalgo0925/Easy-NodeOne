# MASTER PLAN — EasyNodeOne Platform

**Transformación de EN1 hacia una Plataforma de Aplicaciones**

| Campo | Valor |
|-------|--------|
| Versión | **3.1** (Roadmap Oficial Platform V3 — dominio antes de features) |
| Estado | Aprobado — alcance apps acotado; **V3 Etapa 6 Dominio Comercial en definición** |
| Alcance edición | Solo `/opt/easynodeone/dev/app` (Dev EN1) |
| Documento operativo | [`EN1_PLATFORM_CARRILES_Y_SOPORTE.md`](EN1_PLATFORM_CARRILES_Y_SOPORTE.md) |

---

## Objetivo estratégico

**No construir EPosOne como fin.** Construir **EasyNodeOne Platform** — plataforma empresarial de Easy Technology Services que administra **solo** aplicaciones con el mismo Core empresarial.

**No pretende contener todos los productos de ETS.** EPayRoll, EM+Acción, EClassOne y servicios Odoo tienen roadmap, arquitectura y despliegue **propios** — ver [Fuera del roadmap](#fuera-del-roadmap).

No es una migración. Es una **transición controlada**: cada aplicación evoluciona con su propio ciclo de vida; los clientes adoptan apps de forma individual, nunca el sistema completo de una vez.

---

## Roadmap oficial V3

### Visión

EasyNodeOne Platform será la plataforma empresarial de ETS. Solo administrará aplicaciones que compartan el mismo Core empresarial.

### Productos que pertenecen a la plataforma

| Tipo | Apps |
|------|------|
| **Apps de plataforma** | **EPosOne** · **EMembership** · **ECRM** · **EEvents** · **ECertificates** · **EAppointments** |

**EPosOne** = principal desarrollo funcional bajo la nueva arquitectura.

**EMembership, ECRM, EEvents, ECertificates, EAppointments** = evolucionan e integran progresivamente (Etapa 5 — migración por app).

### Fuera del roadmap

Los siguientes productos **no forman parte** de EasyNodeOne Platform. Cada uno mantiene arquitectura, roadmap, despliegue y clientes propios:

| Producto | Estado en EN1 dev |
|----------|-------------------|
| **EPayRoll** | Scaffold legacy en repo — **sin desarrollo ni roadmap de plataforma** |
| **EM+Acción** | Fuera de alcance |
| **EClassOne** | Fuera de alcance |
| **Odoo** (servicios profesionales) | Fuera de alcance |

### Etapas V3 (oficial)

| Etapa | Nombre | Objetivo |
|-------|--------|----------|
| **0** | Protección de producción | IIUS y Relatic congelados; solo hotfixes |
| **1** | Consolidación del Core | Seguridad, auth, multiempresa, org, usuarios, RBAC, contactos, archivos, auditoría, config, API, App Registry, licenciamiento — **sin lógica de negocio** |
| **2** | Plataforma de aplicaciones | Registry, Launcher, menú dinámico, activación tenant/usuario, bundles, `depends_on`, versionado |
| **3** | Modelo maestro compartido | Contact (roles), catálogo, direcciones, archivos, auditoría — un solo modelo |
| **4** | Servicios compartidos | ContactService, ProductService, OrganizationService, FileService, NotificationService, AuditService — Apps sin acceso cruzado |
| **5** | Migración apps existentes | EMembership → ECRM → EEvents → ECertificates → EAppointments (una por una) |
| **6** | **Dominio Comercial** | Cerrar modelo POS: org, roles, pedido, flujos, inventario/caja/pagos/facturación/sync — **solo documento, sin features nuevas** |
| **7** | Construcción del dominio | Implementar sobre dominio congelado: inventario, caja, pedidos, reportes, reembolsos, KDS, delivery, menú QR |
| **8** | Sincronización | Offline first: bus, cola, reintentos, conflictos, descarga incremental, versionado |
| **9** | Hardware | Impresora, cajón, lector, integración terminales físicas |
| **10** | FE Panamá | Facturación electrónica sobre flujo comercial definido |
| **11** | Piloto comercial | Cliente real, validación operativa, go-live controlado |

**Regla V3.1:** no avanzar Etapas 7–11 hasta **cierre aprobado** de Etapa 6 ([`EN1_PLATFORM_ETAPA6_DOMINIO_COMERCIAL.md`](EN1_PLATFORM_ETAPA6_DOMINIO_COMERCIAL.md)).

### Reglas de la plataforma (V3)

1. **El Core** nunca contiene lógica de negocio.
2. **Las Apps** solo dependen del Core.
3. **Dependencias entre Apps** solo vía `depends_on` + servicios compartidos — nunca imports directos.
4. **Migración:** nunca clientes completos; solo apps individuales.
5. **Producción:** IIUS y Relatic protegidos hasta certificar cada app.

### Resultado esperado

```text
EasyNodeOne Platform  →  plataforma empresarial (Core + Apps de plataforma)
EPosOne               →  principal producto funcional de la plataforma
EMembership … EAppointments  →  integración progresiva
EPayRoll, EM+Acción, EClassOne, Odoo  →  fuera, roadmap propio
```

### Mapa implementación EN1 → V3 (referencia)

Numeración histórica en código/commits (Etapas 1–17 EN1) mapea así:

| V3 | EN1 implementado (dev) |
|----|----------------------|
| 0 | Etapa 0 — freeze IIUS/Relatic |
| 1–2 | Etapas 1–3 — Core + Registry + Launcher/Shell |
| 3 | Etapa 10 — modelo maestro ([`EN1_PLATFORM_ETAPA10_MODELO_MAESTRO.md`](EN1_PLATFORM_ETAPA10_MODELO_MAESTRO.md)) |
| 4 | Etapa 11 — `nodeone/core/services/` |
| 5 | Etapa 5 — integración EMembership…EAppointments (runtime por org) |
| **6** | **En curso** — dominio comercial ([`EN1_PLATFORM_ETAPA6_DOMINIO_COMERCIAL.md`](EN1_PLATFORM_ETAPA6_DOMINIO_COMERCIAL.md)) |
| 7 | Scaffold exploratorio: Etapas EN1 6–7, 12, 14–17 (MVP, KDS, delivery, menú QR) — **revisar tras cierre Etapa 6** |
| 8 | Scaffold: Etapas EN1 8, 13 — bus eventos + `nodeone/core/sync/` |
| 9–11 | Pendiente — hardware, FE Panamá, piloto |

**Nota:** el scaffold EN1 12–17 validó arquitectura técnica; **no sustituye** el cierre de dominio de V3 Etapa 6.

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

### Regla 7 — Dominio antes de features (V3.1)

No implementar funcionalidades comerciales nuevas (inventario, reportes, reembolsos, hardware, FE, piloto) hasta **cerrar y aprobar** el dominio comercial — V3 Etapa 6. El scaffold técnico existente es referencia, no contrato de negocio.

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

### V3 Etapa 6 — Dominio Comercial (actual)

**Objetivo:** cerrar el modelo de negocio POS **antes** de más implementación.

| Sub-etapa | Tema |
|-----------|------|
| 6.1 | Organización comercial (empresa, sucursal, área, POS, terminal, caja, turno) |
| 6.2 | Personas (cajero, vendedor, mesero, supervisor, gerente) |
| 6.3 | Documento maestro — **Pedido** como centro del sistema |
| 6.4 | Flujos (restaurante, retail, ferretería, mayorista, delivery) |
| 6.5 | Inventario — solo modelado (reserva, descuento, devolución) |
| 6.6 | Caja — apertura, cobros, reembolsos, arqueo, cierre |
| 6.7 | Pagos — efectivo, tarjeta, mixto, Yappy, transferencia, crédito |
| 6.8 | Facturación — cuándo nace, offline, relación FE Panamá |
| 6.9 | Sincronización — eventos, offline, conflictos, prioridades |

**Entregable:** [`EN1_PLATFORM_ETAPA6_DOMINIO_COMERCIAL.md`](EN1_PLATFORM_ETAPA6_DOMINIO_COMERCIAL.md)

**Criterio de cierre:** documento 6.1–6.9 aprobado; cero preguntas abiertas críticas; **sin código nuevo** hasta entonces.

**Estado:** en definición (2026-07-08).

**Siguiente:** V3 Etapa 7 — Construcción del dominio (inventario, caja, pedidos, reportes, reembolsos).

---

### Etapa 6 — EPosOne (app nativa) — EN1 legado

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

### Etapa 9 — Plantilla nuevas apps (solo apps de plataforma)

Todo producto **de plataforma** nuevo nace como app registrada en el Registry.

| Pieza | Ubicación |
|-------|-----------|
| Descubrimiento manifests | `nodeone/core/platform/manifest_registry.py` |
| Plantilla nueva app | `NEW_APP_MANIFEST_TEMPLATE` en manifest_registry |
| Registry + SaaS | `app_registry.py` + `saas_catalog_defaults.py` |

**Checklist nueva app (Carril 2):**

1. Crear `nodeone/modules/<app>/manifest.py` (y `register.py` + rutas si `lifecycle: active`).
2. Añadir módulo a `PLATFORM_MANIFEST_MODULES`.
3. Registrar `ApplicationDescriptor` en `app_registry.py`.
4. Añadir código SaaS opt-in en `saas_catalog_defaults.py`.
5. Nav + launcher mapping si tiene UI.
6. Tests en `tests/platform/`.
7. Eventos de dominio vía bus (Etapa 8), sin sync de tablas entre apps.

**Estado:** manifest_registry operativo en dev (2026-07-08).

**Nota:** EPayRoll tiene scaffold histórico en el repo; **no** es app de plataforma V3 — sin desarrollo ni prioridad en este roadmap.

---

## Avance técnico EN1 (legado Etapas 10–17 → ver mapa V3 arriba)

**Regla vigente (V3.1):** **congelar features POS nuevas** hasta cierre dominio comercial (V3 Etapa 6). Mantener scaffold; **no** desarrollar productos fuera del alcance V3 (EPayRoll, EM+Acción, etc.).

### Prioridades implementadas (numeración EN1)

| P | Etapa EN1 | Nombre | Estado | V3 |
|---|-----------|--------|--------|-----|
| **P1** | **10** | Modelo maestro compartido | Plan cerrado | → 3 |
| **P2** | **11** | Servicios compartidos | Cerrado dev | → 4 |
| **P3** | **12** | Contratos comerciales (código) | Scaffold dev | → 6 (revisar tras dominio) |
| **P4** | **13** | Sync offline | Scaffold dev | → 8 |
| **P5** | **14** | EPosOne MVP | Scaffold dev | → 7 (post-dominio) |
| — | **15** | KDS | Scaffold dev | → 7 |
| — | **16** | Delivery | Scaffold dev | → 7 |
| — | **17** | Menú digital QR | Scaffold dev | → 7 |
| — | 18 | FE Panamá | Pendiente | → 10 |
| — | — | Hardware / piloto | Pendiente | → 9, 11 |

### Secuencia acordada (V3.1)

```text
Core + Plataforma (1–2) → Modelo + Servicios (3–4)
    → Migración apps plataforma una a una (5)
    → Cerrar Dominio Comercial (6) — solo documento
    → Construcción del dominio (7)
    → Sincronización (8) → Hardware (9) → FE Panamá (10) → Piloto (11)
```

**Fuera de secuencia plataforma:** EPayRoll, EM+Acción, EClassOne, Odoo.

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

### Etapa 12 — resumen (scaffold — sujeto a V3 Etapa 6)

Paquete `backend/nodeone/core/commerce/` — contratos de negocio para EPosOne y ventas (**borrador técnico**, alinear tras dominio aprobado):

| Dominio | Servicio | Estado |
|---------|----------|--------|
| Pedido | `OrderService` | Contrato + eventos; persistencia Etapa 14 |
| Pago | `PaymentService` | Contrato + eventos; persistencia Etapa 14 |
| Factura | `InvoiceService` | Lectura sobre `invoices` contables; emisión unificada Etapa 14 |
| Entrega | `DeliveryService` | Stub + eventos |
| Caja | `CashRegisterService` | Stub + eventos (turnos, arqueos) |
| POS | `PosTerminalService` | Stub + eventos (terminal, dispositivo) |

**Estados v1:** `constants.py` (pedido, pago, factura, entrega, caja, terminal). **Eventos:** `commerce.*` vía bus Etapa 8; EPosOne publica `commerce.*` + `eposone.*` en transición. Tests: `tests/platform/test_commerce_domain.py`.

### Etapa 13 — resumen

Paquete `backend/nodeone/core/sync/` — infraestructura offline sobre el outbox Etapa 8:

| Componente | Rol |
|------------|-----|
| `SyncOperationService` | Cola de escritura con `idempotency_key` (`platform_sync_operation`) |
| `IncrementalSyncService` | Pull incremental de `platform_domain_event` (`since_id`) |
| `SyncCursorService` | Cursores por dominio/cliente (`platform_sync_cursor`) |
| `retry.py` | Backoff exponencial; `NODEONE_EVENT_BUS_MAX_RETRIES` |
| `conflicts.py` | Detección `base_version` vs servidor |
| Bus eventos | `retry_count`, `next_retry_at`, `retry_failed_events()` |

**API:** `GET /api/platform/sync/events`, `POST /api/platform/sync/operations`, cursores `GET/PUT /api/platform/sync/cursors/<domain>`. Tests: `tests/platform/test_sync_offline.py`.

### Etapa 14 — resumen (scaffold MVP — sujeto a V3 Etapa 6)

Persistencia comercial Core + API EPosOne (exploración técnica):

| Entrega | Detalle |
|---------|---------|
| Tablas | `core_commercial_order`, `_line`, `_payment`, `core_cash_shift`, `core_pos_terminal` |
| Servicios | `OrderService`, `PaymentService.capture`, `CashRegisterService`, `PosTerminalService` activos |
| API | `/api/eposone/orders`, pagos, turnos de caja, terminales |
| UI | Sección Pedidos con listado real |
| Offline | `eposone/sync_handlers.py` — `create_order`, `capture_payment` |

**Fuera de MVP v1:** inventario POS, hardware, reportes avanzados, reembolsos. Tests: `tests/platform/test_eposone_mvp.py`.

### Etapa 15 — resumen (KDS)

| Entrega | Detalle |
|---------|---------|
| Tablas | `eposone_kds_station`, `eposone_kds_ticket`, `_line` |
| Servicio | `KdsService` — tickets al confirmar/cobrar pedido |
| API | `GET /api/eposone/kds/tickets`, transiciones de estado |
| UI | `/admin/eposone/section/kds` — grid de tickets |
| Eventos | `eposone.kds.ticket.*` vía bus |

Tests: `tests/platform/test_eposone_kds.py`.

### Etapa 16 — resumen (Delivery)

| Entrega | Detalle |
|---------|---------|
| Tabla | `eposone_delivery` (1 entrega por pedido) |
| Servicio | `EposoneDeliveryService` — crear, asignar repartidor, transiciones |
| Auto | Entrega pendiente al pasar pedido a `ready` |
| API | `GET/POST /api/eposone/deliveries`, assign, status |
| UI | `/admin/eposone/section/delivery` |

Tests: `tests/platform/test_eposone_delivery.py`.

### Etapa 17 — resumen (Menú digital)

| Entrega | Detalle |
|---------|---------|
| Tablas | `eposone_digital_menu`, `eposone_digital_menu_item` |
| Servicio | `DigitalMenuService` — catálogo + pedido vía token QR |
| Público | `GET /m/eposone/<token>`, `GET/POST /api/public/eposone/menu/<token>` |
| Admin | `GET/POST /api/eposone/digital-menus`, UI `/section/digital-menu` |

Tests: `tests/platform/test_eposone_digital_menu.py`.

---

Detalle modelo maestro Core: [`EN1_PLATFORM_ETAPA10_MODELO_MAESTRO.md`](EN1_PLATFORM_ETAPA10_MODELO_MAESTRO.md).

Detalle dominio comercial POS (V3 Etapa 6): [`EN1_PLATFORM_ETAPA6_DOMINIO_COMERCIAL.md`](EN1_PLATFORM_ETAPA6_DOMINIO_COMERCIAL.md).

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
| Construir antes de definir dominio | Regla 7 + V3 Etapa 6 antes de Etapa 7 |
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

## Visión final (V3)

```text
                EasyNodeOne Platform
                         Core
──────────────────────────────────────────
EPosOne    EMembership    ECRM    EEvents
ECertificates    EAppointments
──────────────────────────────────────────
        Apps de plataforma — mismo Core

FUERA: EPayRoll · EM+Acción · EClassOne · Odoo
```

---

## Decisiones estratégicas (resumen)

1. IIUS y Relatic congelados **funcionalmente**, con soporte y hotfixes continuos.
2. No habrá migración big bang; cada app tiene su plan de transición.
3. **Alcance V3:** solo apps de plataforma (EPosOne + cinco apps de integración). EPayRoll, EM+Acción, EClassOne y Odoo **fuera**.
4. EPosOne es la primera app **nativa** y el foco funcional principal.
5. **Dominio comercial cerrado antes de features** — V3 Etapa 6; evita rehacer inventario, caja y reportes.
6. El Core es el activo principal: auth, multiempresa, permisos, API, auditoría, licenciamiento.
7. La **plataforma** es el producto; las **apps de plataforma** son soluciones sobre el mismo núcleo.

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
| **V3 Etapa 6 dominio comercial** | [`EN1_PLATFORM_ETAPA6_DOMINIO_COMERCIAL.md`](EN1_PLATFORM_ETAPA6_DOMINIO_COMERCIAL.md) |
| Deploy clientes | [`CHECKLIST_ACTUALIZACION_Y_CLIENTES.md`](CHECKLIST_ACTUALIZACION_Y_CLIENTES.md) |
| Arquitectura EN1 | [`../backend/docs/EN1_ARCHITECTURE.md`](../backend/docs/EN1_ARCHITECTURE.md) |
| RBAC | [`RBAC_Y_ROLES.md`](RBAC_Y_ROLES.md) |
| Menú ERP | [`PLAN_MENU_ERP_DOMINIOS_EN1.md`](PLAN_MENU_ERP_DOMINIOS_EN1.md) |
| Release IIUS | [`../backend/docs/IIUS_RELEASE_MANIFEST.md`](../backend/docs/IIUS_RELEASE_MANIFEST.md) |
| Reglas equipo | [`../REGLAS-DE-TRABAJO.md`](../REGLAS-DE-TRABAJO.md) |

---

*Última actualización: 2026-07-08 (V3.1 — Etapa 6 Dominio Comercial; etapas 7–11 reorganizadas). Cambios de alcance requieren acuerdo explícito del responsable del proyecto.*
