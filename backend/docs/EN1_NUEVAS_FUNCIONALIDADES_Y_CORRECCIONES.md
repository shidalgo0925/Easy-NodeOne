# EN1 — Nuevas funcionalidades y correcciones

**Release desplegado en prod:** `deaf1df` (`main`)  
**Rango previo en prod:** `806f32c` → `deaf1df` (**84 commits**)  
**Fecha de referencia:** junio 2026  
**Entorno de edición:** `/opt/easynodeone/dev/app` → rama `develop`

Documento de comunicación interna y para clientes. Complementa la documentación técnica EN1 (`EN1_ARCHITECTURE.md`, `EN1_SAAS_GUARDS.md`, etc.).

---

## Resumen ejecutivo

Esta actualización concentra el **ERP con menú tipo Odoo**, **contactos maestro**, **pagos manuales (Yappy y transferencias)**, **facturación electrónica (Fase A Panamá)**, **eventos con certificados e importación**, **release IIUS/educación**, **matriz de seguridad Odoo**, mejoras de **rendimiento SaaS** y correcciones de **taller**, **checkout**, **analítica** y **despliegue en BD legacy**.

Tras el deploy en prod fue necesario aplicar **migraciones DDL adicionales** (columnas en `invoices` y `payment`) documentadas en § Correcciones operativas post-deploy.

---

## Nuevas funcionalidades

### 1. Interfaz y navegación ERP

| Funcionalidad | Descripción |
|---------------|-------------|
| Sidebar ERP oscuro | Tema `sidebar-erp-theme`, iconos por aplicación, filas compactas. |
| Subnav horizontal Odoo | Barra de pestañas sobre el área de trabajo (por módulo activo). |
| Menú por dominios | **Comercial** → **Operaciones** → **Finanzas** (flujo de negocio acordado). |
| Configuración en engranaje | Branding, SMTP, usuarios, organizaciones, impuestos, FE, etc. **fuera** del sidebar lateral. |
| App launcher por áreas | Acceso agrupado a módulos (estilo lanzador de apps). |
| Analítica alineada a Odoo | Subnav y grupo lateral coherentes con el resto del ERP. |
| UX multitenant | Selector de empresa oculto si solo hay una org; ajustes de drawer y mosaico de iconos. |

**Referencias:** `docs/RESUMEN_2026-05-21_MENU_ERP_CONTACTOS.md`, `docs/PLAN_MENU_ERP_DOMINIOS_EN1.md`

---

### 2. Módulo Contactos (`contacts` / `en1_contact`)

| Funcionalidad | Descripción |
|---------------|-------------|
| Maestro de terceros | Tabla y modelo `en1_contact` (clientes, proveedores, datos fiscales). |
| Admin y API | Listado, alta/edición, foto; prefijo `/api/admin/contacts`. |
| Integración comercial | `contact_id` en **cotizaciones** y **facturas**. |
| Menú ERP | **Comercial → Contactos**; redirect legacy `/admin/terceros`. |
| Activación | Módulo SaaS `contacts` + flag `NODEONE_CONTACTS_MODULE_ENABLED` si aplica. |

**Referencias:** `docs/PLAN_MODULO_CONTACTOS_EN1.md`, `docs/PLAN_MAESTRO_CONTACTOS_FACTURACION_FE_EN1.md`

---

### 3. Ventas, tienda y carrito

| Funcionalidad | Descripción |
|---------------|-------------|
| Tienda / catálogo | Mejoras en flujo de compra y menú ERP. |
| Carrito multi-tenant | Resolución de org alineada con `/services` y checkout. |
| Cotizaciones | Edición estilo Odoo; vínculo con contactos; envío por correo. |
| Marketing por campañas | Gestión de campañas en admin marketing. |

---

### 4. Pagos y checkout

| Funcionalidad | Descripción |
|---------------|-------------|
| Pagos por organización | Matriz de métodos y `PaymentConfig` por tenant. |
| Yappy manual | Flujo en checkout (pasos + comprobante obligatorio); admin de revisión y validación. |
| Transferencia SWIFT / Banco General | Instrucciones editables en admin; visualización en checkout. |
| Checkout wizard | Selector de métodos por pasos; estados demo configurables. |
| Admin Pagos ampliado | Sección Yappy manual, listados, API de configuración. |
| PayPal / IIUS | Documentación y checklist para pagos en campus académico (release IIUS). |

**Nota:** Stripe desactivado en checkout según política de este release. Plan de activación: [`docs/EN1_ROADMAP.md`](../../docs/EN1_ROADMAP.md) § Stripe.

---

### 5. Facturación electrónica — Fase A Panamá (`efactura`)

| Funcionalidad | Descripción |
|---------------|-------------|
| Módulo FE | Config por org, emisión de prueba, logs, adaptador `efacturapty`. |
| Menú | Acceso desde **Finanzas** / configuración (según guards SaaS). |
| Plan por fases | Documentación `docs/efactura/FASE_*.md`. |

---

### 6. Contabilidad y analítica

| Funcionalidad | Descripción |
|---------------|-------------|
| Columnas legacy en facturas | Soporte BD antigua (`amount_paid`, contactos, moneda, etc.). |
| Analítica | KPIs de ventas/CRM con DDL previo a consultas. |
| Contabilidad | Ajustes de esquema y rutas admin. |

---

### 7. Taller (`workshop`)

| Funcionalidad | Descripción |
|---------------|-------------|
| Órdenes de trabajo (OT) | Recepción, vehículo, líneas, estados, fotos entrada/proceso/salida. |
| Inspección | Mapa de zonas, puntos, severidad, fotos por punto. |
| SLA por etapa | Semáforo, monitor, KPIs, configuración de procesos y por servicio. |
| Cotización desde OT | Genera `Q-xxxx` en Ventas (requiere módulo `sales`). |
| Manual de operaciones | `backend/docs/EN1_OPERACIONES_TALLER.md` |

**Código SaaS:** `workshop` (opt-in por organización).

---

### 8. Eventos, certificados y marketing

| Funcionalidad | Descripción |
|---------------|-------------|
| Participantes | Alta, edición, importación (plantillas A–J, revisores, genérico). |
| Certificados EN1 | Emisión/gestión por participante y evento. |
| Detalle público | Hero en grid de tres columnas. |
| Email marketing | Newsletter con flyer (ej. Seminario); URLs absolutas de imágenes. |
| Preview import | Store temporal para vista previa de importación. |

---

### 9. Educación / IIUS (release integrado)

| Funcionalidad | Descripción |
|---------------|-------------|
| Campus `academic_closed` | Acceso al campus solo con matrícula activa (gate en middleware). |
| Programas en BD | Landings de inscripción, programas publicados, matrículas. |
| Matriz de pagos IIUS | Configuración y documentación de circuito (PayPal, QA). |
| Handoff y runbooks | `backend/docs/IIUS_*.md`, `ETAPA2_IIUS_RUNBOOK.md`. |

---

### 10. Seguridad, RBAC y herramientas

| Funcionalidad | Descripción |
|---------------|-------------|
| Matriz seguridad Odoo (`security_matrix`) | Import XLS, catálogo, vista permisos, análisis asistido. |
| Permisología EN1 | Matriz roles × permisos en admin (`rbac_matrix`). |
| Generador QR | Módulo `qr_generator` en menú ERP. |
| Landing EN1 | Componentes de producto (showcases, ecosistema, casos de uso). |

---

### 11. Rendimiento y plataforma

| Funcionalidad | Descripción |
|---------------|-------------|
| Precarga SaaS | Flags de módulos por org en `before_request` (menos consultas en plantillas). |
| Caché por request | Flags SaaS y resolución SMTP sin reinicializar Mail en cada hit. |
| Contexto lazy | Carga diferida de académico/eventos y settings de org. |

---

### 12. Documentación EN1 (en `develop`, pendiente de `main`)

Commit `2b3d585` (aún no en prod si `main` = `deaf1df`):

| Documento | Contenido |
|-----------|-----------|
| `EN1_ARCHITECTURE.md` | Capas, multi-tenant, auth. |
| `EN1_ROUTES.md` | Blueprints y convenciones de rutas. |
| `EN1_API_CONTRACT.md` | Familias JSON (`success` / `ok` / legacy). |
| `EN1_SAAS_GUARDS.md` | Módulos por organización. |
| `EN1_MODELS.md` | Mapa de modelos. |
| `FLUTTER_SYNC.md` | Sincronización app móvil. |

---

## Correcciones

### Correcciones de producto (incluidas en `deaf1df`)

| Área | Corrección |
|------|------------|
| **Taller** | Guardar orden de forma fiable; finalizar sin exigir fotos cuando no aplica; UI unificada. |
| **Pagos admin** | SWIFT/Banco General editables; guardado admin sin error 500; rollback en transacciones. |
| **Pagos admin** | Restauración de `payments_admin_bp` tras regresión. |
| **Checkout** | Org vía `resolve_current_organization`; instrucciones por método. |
| **Checkout** | Enlaces Yappy manual sin `url_for` que provocaban BuildError 500. |
| **Dashboard / carrito** | `CartItem` usa `unit_price` / `get_subtotal` (no `price`). |
| **Ventas** | DDL `contact_id` en cotizaciones al cargar API. |
| **Contabilidad** | DDL idempotente columnas `Invoice` en BD legacy. |
| **Analítica** | DDL de facturas/cotizaciones **antes** de KPIs (evita 500). |
| **Bootstrap** | Orden DDL: fiscal/CRM antes de cargar orgs en arranque. |
| **Admin usuarios** | Planes en modal «Asignar membresía» y POST `assign-membership`. |
| **Marketing email** | URLs absolutas de imágenes (`BASE_URL`). |
| **UI ERP** | Submenús laterales no ocultos por error con barra Odoo; reset drawer. |
| **Finanzas (menú)** | `{% endif %}` prematuro que sacaba Contabilidad/FE del bloque. |

---

### Correcciones operativas post-deploy (prod / staging)

Detectadas al actualizar silos con BD PostgreSQL **anteriores al modelo actual**. No borran datos de clientes; solo añaden columnas.

| Síntoma | Causa | Acción aplicada |
|---------|--------|-----------------|
| **500 en `/dashboard`** (usuario logueado) | Columna `payment.amount_received_cents` (y otras Yappy) inexistente; `UserStatusChecker` dejaba transacción abortada. | Scripts `migrate_yappy_manual_en1.py` + `migrate_yappy_manual_checkout_v3.py`. |
| **500 en cadena** (`InFailedSqlTransaction`) | Misma transacción tras error SQL en pagos pendientes. | Reinicio de servicio + migraciones anteriores. |
| **Consultas a facturas** | `invoices.amount_paid` faltante. | `ensure_invoices_model_columns` (bootstrap o script manual). |

**Prevención en código (pendiente de commit en `develop`):**

- `nodeone/services/payment_yappy_schema.py` + llamada en `bootstrap_nodeone_schema`.
- `user_status_checker.py`: `db_session.rollback()` si falla la verificación de estado.

**Procedimiento estándar tras cada deploy en silo:**

```bash
export EASYNODEONE_MIGRATE_PROD_CONFIRM=YES   # solo prod
sudo -E bash /opt/easynodeone/scripts/migrate-easynodeone-instance.sh <staging|prod>
sudo systemctl restart easynodeone-<silo>
# Verificar: login + dashboard + una pantalla del release
```

---

## Módulos SaaS nuevos o reforzados (catálogo)

| Código | Nombre corto |
|--------|----------------|
| `contacts` | Contactos maestro |
| `efactura` | Facturación electrónica |
| `workshop` | Taller + SLA |
| `security_matrix` | Matriz Odoo |
| `rbac_matrix` | Permisología EN1 |
| `qr_generator` | Generador QR |
| `analytics` | Analítica (con DDL asociado) |

Activación: **Admin plataforma → Organizaciones → Módulos** (o `saas_org_module` por tenant).

---

## Qué no está aún en prod (solo `develop` o local)

| Ítem | Estado |
|------|--------|
| Documentación EN1 viva (`2b3d585`) | En `origin/develop`; falta merge a `main`. |
| Bootstrap `payment_yappy_schema` + rollback en `user_status_checker` | Cambios locales sin commit. |
| `EN1_OPERACIONES_TALLER.md` | En `backend/docs/`; sin commit. |

---

## Checklist de validación post-actualización

- [ ] Login y **dashboard** (miembro y admin).
- [ ] Selector de empresa (si multitenant).
- [ ] **Contactos**: listar y crear tercero.
- [ ] **Ventas**: cotización con contacto.
- [ ] **Pagos**: config por org; Yappy manual en checkout (si aplica).
- [ ] **Taller**: nueva OT, cambio de estado, monitor SLA.
- [ ] **Eventos**: listado participantes / import (si módulo ON).
- [ ] **Analítica**: `/admin/analytics` sin 500.
- [ ] `journalctl` / `app_errors.log` sin `UndefinedColumn` tras reinicio.

---

## Referencias

| Documento | Uso |
|-----------|-----|
| [EN1_OPERACIONES_TALLER.md](./EN1_OPERACIONES_TALLER.md) | Operación módulo taller |
| [EN1_SAAS_GUARDS.md](./EN1_SAAS_GUARDS.md) | Activar módulos por org |
| [CHECKLIST_ACTUALIZACION_Y_CLIENTES.md](../../docs/CHECKLIST_ACTUALIZACION_Y_CLIENTES.md) | Deploy y comunicación a clientes |
| [REGLAS-DE-TRABAJO.md](../../REGLAS-DE-TRABAJO.md) | Solo `git pull` en staging/prod |

---

## Texto breve para cliente (plantilla)

```text
Actualizamos Easy NodeOne con un menú de trabajo más claro (comercial, operaciones y finanzas),
maestro de contactos, pagos manuales mejorados (incl. Yappy con comprobante), facturación
electrónica inicial, mejoras en eventos y certificados, y correcciones en taller y checkout.
Si notan algún error tras el cambio, indiquen hora, usuario y pantalla a soporte.
```

---

*Generado para release `deaf1df`. Actualizar este archivo en el siguiente merge a `main`.*
