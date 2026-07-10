# EN1 — Roadmap producto

**Última actualización:** 9 jul 2026  
**Edición:** `/opt/easynodeone/dev/app` → rama `develop`

Índice de iniciativas planificadas o en curso en Easy NodeOne. Roadmaps de módulo con detalle propio enlazan desde aquí.

| Módulo | Documento |
|--------|-----------|
| ECalendar | [`ECALENDAR_ROADMAP.md`](ECALENDAR_ROADMAP.md) |
| Certificados | Este archivo § Certificados |
| Stripe / tarjetas | Este archivo § Stripe |
| Plataforma / EPosOne UX | Este archivo § Plataforma — EPosOne (nav) |
| Sprint UX transición apps | [`EN1_PLATFORM_SPRINT_UX_TRANSICION_APPS.md`](EN1_PLATFORM_SPRINT_UX_TRANSICION_APPS.md) |
| **EPosOne V4 (arquitectura)** | [`EN1_PLATFORM_EPOSONE_V4_ROADMAP.md`](EN1_PLATFORM_EPOSONE_V4_ROADMAP.md) · sprints 1–7 · sync: [`EN1_PLATFORM_EPOSONE_V4_SYNC.md`](EN1_PLATFORM_EPOSONE_V4_SYNC.md) · `backend/nodeone/core/eposone_domain/` |

---

## Plataforma — EPosOne (nav / UX V3.2)

**Estado:** **parcialmente resuelto** (9 jul 2026) — entrada **EPosOne** en sidebar plataforma; nav nativa si el módulo está activo en la org.

**Siguiente (Fase 2):** especificación aprobada — [`EN1_PLATFORM_SPRINT_UX_TRANSICION_APPS.md`](EN1_PLATFORM_SPRINT_UX_TRANSICION_APPS.md) (tickets UX-T1…T5). Arquitectura dos menús se mantiene; el trabajo es **experiencia de transición** (identidad, retorno al launcher, analítica POS dentro de EP1). Implementar **solo con GO por ticket**.

### Síntoma (histórico)

- En módulos de plataforma (p. ej. `/admin/contacts`) no debe aparecer la barra horizontal legacy de EPosOne (correcto tras fix UX V3.2).
- **Problema:** tampoco hay un punto de entrada claro para entrar a EPosOne y ver su menú (Dashboard, Pedidos, Clientes, Catálogo, etc.).
- URL directa `/admin/eposone/dashboard` sí muestra el sidebar nativo por dominios; el fallo es de **descubrimiento / acceso**, no de rutas internas.

### Causas identificadas

| Causa | Detalle |
|-------|---------|
| Sin ítem en sidebar ERP | El área `eposone` en `nav_menu.py` **no está** en `_SIDEBAR_TOP_LEVEL_AREA_IDS` ni en `_SIDEBAR_LAUNCHER_GROUPS` (Comercial, Operaciones, …). |
| Modo launcher `classic` | Orgs como Itsmo Brew no tienen «Mis aplicaciones»; solo ven Contactos, Comercial, Finanzas en sidebar. |
| Shell apps + sesión stale | Con `platform_active_app_id=eposone`, `merge_app_shell_nav_context` podía forzar shell EPosOne fuera de `/admin/eposone/*` (fix parcial en dev, sin commit al cierre de esta nota). |
| Código duplicado | Menú EPosOne definido en `nav_menu.py` (legacy horizontal) y `modules/eposone/nav.py` (nativo V3.2); pipeline calcula ambos. |

### Fix aplicado (dev, 9 jul 2026)

- Ítem **EPosOne** en sidebar top-level (`_SIDEBAR_TOP_LEVEL_AREA_IDS`) → enlace a `/admin/eposone/dashboard`.
- **UX-T2:** ese ítem es **atajo temporal** (comentario `TEMPORAL`, badge «App», tooltip); entrada oficial = Launcher / Mis aplicaciones. No ampliar a otras apps.
- Nav nativa V3.2 si la org tiene módulo `eposone` activo (no solo orgs seed).
- No mostrar barra horizontal EPosOne fuera de `/admin/eposone/*` en Contactos (commit `a19cc6d`).
- Enlace EPosOne en wizard empresa → paso Opciones.
- Tests: `test_eposone_in_sidebar_top_level`, `TestMergeAppShellContacts`.

### Pendiente (requiere GO)

**Sprint UX transición (Fase 2)** — ver [`EN1_PLATFORM_SPRINT_UX_TRANSICION_APPS.md`](EN1_PLATFORM_SPRINT_UX_TRANSICION_APPS.md):

- [x] **UX-T1** Retorno `← Mis aplicaciones` + identidad shell EPosOne (dev, 9 jul 2026)
- [x] **UX-T2** Atajo ERP classic documentado como **temporal** (dev, 9 jul 2026)
- [x] **UX-T3** Dashboard: quitar “Core Compuesto”; empty states cortos (dev, 9 jul 2026)
- [x] **UX-T4** Analítica POS dentro de EPosOne (sin `?source=eposone` como diseño) (dev, 9 jul 2026)
- [ ] **UX-T5** (Opcional) Micro-transición visual al entrar a la app

Otros:

- [ ] Consolidar nav (una fuente: `eposone/nav.py`; retirar ítems duplicados en `nav_menu.py`).
- [ ] UAT en appdev: desde Contactos → clic **EPosOne** en sidebar → menú dominios visible.

### Referencias

| Pieza | Ubicación |
|-------|-----------|
| Nav nativa V3.2 | `nodeone/modules/eposone/nav.py`, `nodeone/core/platform/app_nav.py` |
| Shell / merge | `nodeone/core/platform/app_shell.py` |
| Zona eposone | `nav_menu.py` área `eposone` (`zone_path_prefixes=/admin/eposone`) |
| Plan maestro | [`EN1_PLATFORM_MASTER_PLAN.md`](EN1_PLATFORM_MASTER_PLAN.md) § Etapa 6–7 EPosOne |

---

## Certificados — eventos y membresía

**Estado:** **operativo en `develop` y Relatic** (jun 2026) — refactor cerrado; fix rutas PDF membresía en `804edf6`.

Hay **dos flujos** (no mezclar):

| Familia | Pantalla usuario | Pantalla admin | Emisión |
|---------|------------------|----------------|---------|
| **Eventos** (seminarios) | Mis Certificados → descarga | Eventos → Certificados | Admin genera PDF |
| **Membresía** (`PLAN-BASIC`, `PLAN-PRO`, …) | Mis Certificados → **Solicitar** / descarga | Certificados → Eventos (formatos MEM/PLAN) | Usuario solicita si cumple plan |

### Entregado (jun 2026)

| Entrega | Commit / nota |
|---------|----------------|
| Refactor módulo `nodeone/modules/certificates/` + tests | `314d1f7`, fases 0–5 |
| Editor único de formato + retorno al evento | `1d878d4` |
| Regenerar **todos** los PDF de un evento | `33dde91` |
| Un certificado por plan comercial (`PLAN-{slug}`) + elegibilidad por membresía vigente | `certificate_membership_rules.py` |
| Admin: listar y **eliminar emisiones** MEM/PLAN (re-solicitar con plantilla vigente) | `6b9c17f`, `1911a9f` |
| Fix rutas PDF membresía (`app/instance/certificates/`) tras refactor | **`804edf6`** — desplegado Relatic |
| PDF membresía: descarga y regeneración si falta archivo en disco | `certificate_http.py`, `api_routes.py` |

### Reglas de negocio (membresía)

- **Básico** → solo `PLAN-BASIC` si membresía `basic` vigente.
- **Pro / Premium / …** → solo el formato del plan que coincida con suscripción o `membership` activa.
- Código emitido: `PLAN-PRO-O1-2026-XXXX` (legacy `MEM-O1-…` sigue descargable si existe fila en BD).
- Sin plan coincidente → tarjeta **Requisitos pendientes** (sin botón Solicitar). Con emisión previa → **Emitido** + Descargar aunque el plan haya cambiado.

### QA mínimo (smoke)

- [ ] Mis Certificados carga `/api/my-certificates` (tarjetas por plan).
- [ ] Usuario con plan Pro → Solicitar → PDF en `instance/certificates/` → descarga 200.
- [ ] Admin → formato PLAN → Ver emitidos → Eliminar → usuario puede volver a solicitar.
- [ ] Evento con participantes → Regenerar todos (N) tras cambio de plantilla.

### Referencias

| Documento | Uso |
|-----------|------|
| [`EN1_CERTIFICADOS_EVENTOS_CONTEXTO.md`](EN1_CERTIFICADOS_EVENTOS_CONTEXTO.md) | Eventos: formato, plantilla, emitir, regenerar |
| [`EN1_CERTIFICADOS_ENTREGA_ANALISTA_2026-06.md`](EN1_CERTIFICADOS_ENTREGA_ANALISTA_2026-06.md) | Entrega analista jun 2026 |
| `backend/docs/MANUAL_ADMIN_CERTIFICADOS_EN1.md` | Admin membresía + eventos |
| `backend/docs/MANUAL_USUARIO_CERTIFICADOS_EN1.md` | Usuario final |

### Fuera de alcance (esta fase)

- Re-emitir automáticamente todos los MEM legacy al cambiar plantilla (solo regeneración bajo demanda / admin elimina emisión).
- Certificados de membresía sin plan vinculado (formatos huérfanos REL/MEM sueltos — desactivados en siembra).

---

## Stripe — pagos con tarjeta

**Estado:** **código reactivado en `develop`** (jun 2026) — pendiente credenciales tenant, webhook en Stripe Dashboard y QA E2E en IIUS/prod.

### Lo que ya existe

| Pieza | Detalle |
|-------|---------|
| Librería | `stripe==7.8.0` en `requirements.txt` |
| Procesador | `StripeProcessor` en `payment_processors.py` |
| Webhook | `POST /stripe-webhook` (`payments_checkout` blueprint, **sin** prefijo `/api`) |
| Admin | `/admin/payments?context=config` — sección **Stripe** (pk, sk, webhook secret) |
| BD | `PaymentConfig.stripe_*` + matriz `organization_payment_methods` (clave `stripe`) |
| UI checkout | `templates/payment_methods/stripe.html`, Stripe Elements en `checkout.html` |

### Lo que falta (orden obligatorio)

```text
1. Reactivar código Stripe en dev
2. Desplegar a staging → validar → prod
3. Configurar credenciales por tenant en admin
4. Activar método Stripe en matriz de pagos del tenant
5. Crear webhook en Stripe Dashboard
6. Probar pago E2E (tarjeta test → payment_intent.succeeded)
```

#### 1. Código (dev)

| Tarea | Archivo / nota |
|-------|----------------|
| Descomentar `stripe` en `PAYMENT_METHODS` | `backend/payment_processors.py` |
| Devolver `client_secret` en respuesta de checkout | `payments_checkout/routes.py` (`create_payment_intent`) |
| Reactivar detección de credenciales / modo demo Stripe | mismo archivo (bloques comentados ~L277–404, ~L600) |
| Verificar flujo `confirmCardPayment` en frontend | `templates/checkout.html` |
| Tests | `backend/tests/payments/test_payment_routes.py` (`stripe_webhook`) |

#### 2. Configuración por tenant (admin)

En **Configuración → Pagos → Stripe**:

- Publishable key (`pk_live_…` / `pk_test_…`)
- Secret key (`sk_live_…` / `sk_test_…`)
- Webhook signing secret (`whsec_…`)

**No** reutilizar las credenciales de login social (`GOOGLE_CLIENT_ID` en `.env`); Stripe usa `PaymentConfig` por organización.

#### 3. Matriz de métodos

- Activar **Tarjeta (Stripe)** en la matriz del tenant (`organization_payment_methods.enabled = true`).
- Perfiles por defecto (`panama`, `international`) tienen `stripe: false` — hay que activarlo explícitamente para IIUS u otros clientes que lo requieran.

#### 4. Webhook en Stripe (solo tras deploy)

| Campo | Valor |
|-------|--------|
| URL | `https://<host-en1>/stripe-webhook` |
| Evento mínimo | `payment_intent.succeeded` |
| Signing secret | Guardar en admin → Stripe → Webhook signing secret |

**URLs que no existen en EN1:** `/api/payments/stripe/webhook`, `/api/v1/payments/stripe/webhook`.

#### 5. QA mínimo

- [ ] Checkout muestra opción Stripe con tenant configurado
- [ ] `POST /create-payment-intent` con `payment_method=stripe` devuelve `client_secret`
- [ ] Pago test completa en Stripe
- [ ] Webhook recibido → `Payment.status = succeeded` + post-proceso (suscripción / carrito)
- [ ] `curl` o health operativo en el entorno desplegado

### Fuera de alcance (esta fase)

- Suscripciones recurrentes Stripe Billing
- Apple Pay / Google Pay
- Multi-moneda distinta de USD en checkout actual
- Sustituir PayPal en perfiles que no lo requieran

### Referencias técnicas

| Documento | Uso |
|-----------|-----|
| `md/STRIPE_SETUP.md` | Setup histórico |
| `md/CONFIGURACION_PAGOS.md` | PaymentConfig y troubleshooting webhook |
| `backend/docs/EN1_API_CONTRACT.md` | Contrato `/stripe-webhook`, `/create-payment-intent` |
| `docs/FASE_0_INVENTARIO_SEGURIDAD.md` | Webhook sin sesión; validación por firma |

---

## Otras iniciativas

Ver roadmaps y planes por dominio en `docs/` y `backend/docs/EN1_*.md`. Añadir aquí nuevas entradas cuando el negocio abra un epic con GO explícito.
