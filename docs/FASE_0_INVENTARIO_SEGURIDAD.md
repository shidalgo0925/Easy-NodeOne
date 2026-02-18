# FASE 0 — Inventario y análisis de seguridad

**Proyecto:** miembros.relatic.org (membresia-relatic)  
**Objetivo:** Conocer el estado actual antes de implementar RBAC por permisos.  
**Fecha de inventario:** 2025-01-31

---

## 1. Modelos actuales

### 1.1 Usuario e identidad

| Modelo | Ubicación | Descripción |
|--------|-----------|-------------|
| **User** | `backend/app.py` | `User(UserMixin, db.Model)`. PK: `id` (Integer). Campos relevantes: `email`, `password_hash`, `first_name`, `last_name`, `is_active`, **`is_admin`** (Boolean), **`is_advisor`** (Boolean), `email_verified`, tokens de verificación y reset. **No existe modelo Role ni Permission.** |
| **SocialAuth** | `backend/app.py` | Vinculación OAuth (Google, Facebook, LinkedIn) por `user_id`. |

- **Identidad:** Un usuario por email; `id` es Integer (no UUID).
- **Control de acceso administrativo:** Un único booleano `User.is_admin`. No hay roles ni permisos granulares.

### 1.2 Otros modelos (sin rol/permiso)

Entre otros: Membership, Benefit, Payment, Subscription, Event, EventImage, Discount, EventDiscount, DiscountCode, EmailLog, EmailConfig, PaymentConfig, MediaConfig, EmailTemplate, NotificationSettings, Advisor, AppointmentType, Appointment, Service, ServiceCategory, ServicePricingRule, MembershipDiscount, Cart, CartItem, ActivityLog, HistoryTransaction, Notification, etc. Ninguno implementa RBAC; la autorización se basa en `current_user.is_admin` en rutas admin.

---

## 2. Sistema de autenticación

### 2.1 Mecanismo

| Aspecto | Estado actual |
|---------|----------------|
| **Biblioteca** | Flask-Login |
| **Sesión** | Cookie de sesión (servidor); no se usa JWT para sesión web. |
| **Secret** | `app.config['SECRET_KEY']` (en código: `secrets.token_hex(16)`; en producción debe venir de env). |
| **Contraseñas** | Werkzeug `generate_password_hash` / `check_password_hash` (por defecto pbkdf2). No bcrypt/argon2 explícito en el inventario. |
| **OAuth** | Login social: `/auth/<provider>`, `/auth/<provider>/callback` (Google, Facebook, LinkedIn). |

No hay JWT access/refresh ni rotación de tokens en la aplicación web actual.

### 2.2 Guards / decoradores

| Decorador | Ubicación | Comportamiento |
|-----------|------------|----------------|
| **@login_required** | Flask-Login | Redirige a login si no autenticado. |
| **@admin_required** | `app.py` (y réplica en `event_routes.py`, `appointment_routes.py`) | Aplica `@login_required` y luego comprueba **`current_user.is_admin`**. Si no es admin: flash de error y redirect a `dashboard`. |

**Regla actual:** Toda la “autorización” administrativa se hace por **rol implícito** (un solo rol: admin) mediante el booleano `is_admin`. No existe comprobación por permiso (ej. `users.create`, `payments.manage`).

---

## 3. Rutas: protegidas vs públicas

### 3.1 Públicas (sin login)

- `/` (index)
- `/promocion`
- `/register`, `/login`
- `/verify-email/<token>`
- `/forgot-password`, `/reset-password`
- `/auth/<provider>`, `/auth/<provider>/callback`
- **POST** `/stripe-webhook` (webhook Stripe; sin auth; validación por firma Stripe)
- **GET** API eventos: `events_api_bp` `/` y `/<slug>` (listado y detalle de eventos publicados)

### 3.2 Autenticadas (@login_required)

- `/logout`, `/dashboard`, `/profile`, `/membership`, `/services`, `/benefits`, `/cart`, `/checkout`, `/notifications`, `/help`, `/settings`, `/office365`, `/foros`, `/grupos`
- Rutas de citas: `/appointments/`, book/cancel, advisor dashboard/slots/queue
- APIs de usuario: `/api/user/status`, `/api/user/dashboard`, `/api/history`, `/api/notifications/*`, `/api/cart/*`, etc.
- Pagos: `/create-payment-intent`, `/create-payment-intent-legacy` (con `@email_verified_required`), `/payment-success`, `/payment/paypal/return|cancel`, `/payment-cancel`
- Servicios: `/services/<id>/request-appointment` (GET/POST)
- Calendario: `/api/appointments/calendar/<advisor_id>`, `/api/services/<service_id>/calendar`

### 3.3 Administrativas (@admin_required)

Todas las rutas bajo `/admin/*` y APIs bajo `/api/admin/*` están protegidas únicamente por `@admin_required` (es decir, por `current_user.is_admin`), sin distinción de permisos. Incluyen, entre otras:

- `/admin`, `/admin/users`, `/admin/memberships`, `/admin/messaging`, `/admin/email`, `/admin/media`, `/admin/payments`, `/admin/backup`, `/admin/notifications`, `/admin/discount-codes`, `/admin/services`, `/admin/service-categories`, `/admin/membership-discounts`, `/admin/master-discount`, `/admin/announcements` (si aplica)
- Blueprints: `admin_events_bp` (eventos, descuentos, registros), `admin_appointments_bp` (calendario, disponibilidad, tipos, asesores)
- APIs: `/api/admin/history`, `/api/admin/messaging/*`, `/api/admin/email/*`, `/api/admin/media/*`, `/api/admin/payments/*`, `/api/admin/services/*`, `/api/admin/service-categories/*`, `/api/admin/membership-discounts/*`, etc.

---

## 4. Validaciones por rol (a eliminar / refactorizar)

- **`admin_required`:** Comprueba solo `current_user.is_admin`. Debe sustituirse por comprobación por **permiso** (ej. permiso asociado al recurso).
- **`User.get_active_membership()`:** Si `user.is_admin`, devuelve una “membresía virtual” con acceso total. Lógica de negocio aceptable, pero el criterio sigue siendo el rol (admin), no un permiso.
- **Filtros y notificaciones:** Varios usos de `User.query.filter_by(is_admin=True)` para notificaciones y visibilidad (ej. historial con `include_sensitive`, notificaciones a admins). Habrá que reemplazar por “usuarios con permiso X”.
- **event_routes:** En `event_registrations` se comprueba acceso con `event.administrator_id == current_user.id` o `current_user.is_admin`. Es mezcla de “dueño del recurso” y “rol admin”; en RBAC debería ser “tiene permiso sobre este recurso/evento”.

No se encontraron modelos `Role` ni `Permission` ni tablas `role_permission` o `user_role`.

---

## 5. Endpoints críticos sin protección adecuada

| Endpoint | Protección actual | Observación |
|----------|-------------------|-------------|
| **POST /stripe-webhook** | Ninguna (por diseño) | Debe validarse firma Stripe; no debe confiarse en cabeceras sin verificación. |
| **GET /api/events/** | Público | Listado/detalle de eventos publicados; aceptable si solo se exponen eventos con `publish_status=published`. Revisar que no se filtren datos sensibles. |
| **POST /create-payment-intent** | `@email_verified_required` | Requiere usuario logueado y email verificado; no distingue permisos admin. |
| Rutas **/admin/** | Solo `@admin_required` | Cualquier usuario con `is_admin=True` tiene acceso a todo el panel (usuarios, pagos, backup, configuración, etc.). Sin principio de mínimo privilegio. |

No se detectaron endpoints admin que estén abiertos sin `@admin_required`; el riesgo principal es la falta de granularidad (todo o nada para un solo “rol” booleano).

---

## 6. Gap analysis vs plan RBAC por permisos

| Requisito del plan | Estado actual | Gap |
|--------------------|---------------|-----|
| Roles (SA, AD, ST, TE, MI, IN) | No existen; solo `is_admin` (y `is_advisor`) | Implementar modelo **Role** y asignación **user_role**. |
| Catálogo de permisos | No existe | Implementar modelo **Permission** y tabla **role_permission**. |
| Backend valida por **permiso** | Backend valida solo por `is_admin` | Introducir middleware/decorador `@require_permission('permiso')` y sustituir `@admin_required` por comprobaciones por permiso. |
| Helper `hasPermission()` | No existe | Añadir en User o en contexto (ej. `current_user.has_permission('users.create')`). |
| Auditoría de acciones críticas | Existe `ActivityLog` / `HistoryTransaction` | Revisar que todas las acciones sensibles (asignación de roles, cambios de permisos, pagos, backup) queden registradas. |
| JWT access/refresh | No usado en web actual | Opcional para APIs externas; sesión cookie es válida para la web actual. |
| MFA / brute force | No identificado en inventario | Fase posterior. |

---

## 7. Resumen y próximos pasos

- **Modelos:** Hay **User** con `is_admin` e `is_advisor`. **No hay** Role, Permission, role_permission ni user_role.
- **Auth:** Sesiones con Flask-Login; autorización admin por **rol único** (booleano), no por permisos.
- **Rutas:** Públicas bien delimitadas; admin todo bajo `@admin_required` sin granularidad.
- **Riesgo principal:** Un solo rol “admin” con acceso total; no se cumple mínimo privilegio ni matriz roles/permisos.

**Siguiente fase recomendada:** FASE 2 — Diseño del modelo de datos (roles y permisos) y creación de tablas/migraciones, para después implementar en FASE 3 la autorización por permiso en el backend.
