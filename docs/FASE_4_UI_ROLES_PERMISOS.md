# FASE 4 — Consola administrativa de Roles y Permisos (UI)

**Proyecto:** miembros.relatic.org (membresia-relatic)  
**Objetivo:** Dar visibilidad y control al sistema RBAC existente sin romper seguridad. Solo lectura en esta fase.

---

## 1. Permisos necesarios

- **roles.view** — Acceso a listado de roles, detalle de rol y listado de permisos. Ya existía en el catálogo RBAC.
- **roles.assign** — (Fase futura) Para modificar asignación de roles a usuarios.
- **roles.manage** — (Opcional, futuro) Para editar permisos de roles.

**Regla:** Solo usuarios con `roles.view` pueden acceder a `/admin/roles` y APIs de roles/permisos. Solo SA o AD con `roles.assign` podrán modificar en FASE 5.

---

## 2. Rutas backend (solo lectura)

### 2.1 Roles

| Método | Ruta | Descripción | Protección |
|--------|------|-------------|------------|
| GET | `/admin/roles` | Listado de roles (HTML) | @require_permission('roles.view') |
| GET | `/admin/roles/<id>` | Detalle de un rol (HTML) | @require_permission('roles.view') |
| GET | `/api/admin/roles` | Listado de roles (JSON) con cantidad de permisos | @require_permission('roles.view') |
| GET | `/api/admin/roles/<id>` | Detalle de un rol (JSON) con lista de permisos | @require_permission('roles.view') |
| GET | `/api/admin/roles/<id>/users` | Usuarios que tienen este rol (JSON) | @require_permission('roles.view') |

### 2.2 Permisos

| Método | Ruta | Descripción | Protección |
|--------|------|-------------|------------|
| GET | `/api/admin/permissions` | Listado de permisos (JSON) | @require_permission('roles.view') |

---

## 3. Pantallas UI (MVP, solo lectura)

### 3.1 Listado de roles (`/admin/roles`)

- Tabla: **Código** (SA, AD, …), **Nombre**, **Cantidad de permisos**, **Acciones** (botón "Ver").
- No editable en esta fase.
- Enlace desde menú lateral (solo si el usuario tiene `roles.view`) y desde Panel Admin → "Roles y Permisos".

### 3.2 Detalle de rol (`/admin/roles/<id>`)

- Muestra: código, nombre, descripción (si existe).
- Lista de **permisos asociados** (solo lectura).
- Badges: **Sistema** para permisos `system.*` / `audit.*`; **Crítico** para permisos con `delete` o `revoke`.
- Sección "Usuarios con este rol": botón "Cargar usuarios" que llama a `GET /api/admin/roles/<id>/users` y muestra la lista.

### 3.3 Usuario → Roles (en admin usuarios)

- En la lista de usuarios (`/admin/users`) se añadió la columna **Roles**.
- Muestra los códigos de rol asignados a cada usuario (badges). Solo lectura.

---

## 4. Auditoría

Cada acceso a:

- `/admin/roles` (listado)
- `/admin/roles/<id>` (detalle)
- `/api/admin/roles`
- `/api/admin/roles/<id>`
- `/api/admin/permissions`

registra en **ActivityLog**:

- **action:** `VIEW_ROLES`
- **entity_type:** `roles` o `permissions`
- **entity_id:** id del rol (si aplica) o None
- **description:** texto descriptivo (ej. "Acceso al listado de roles", "API: detalle rol AD")
- **user_id, ip_address, user_agent, created_at** (según modelo ActivityLog)

---

## 5. Qué NO se hace en FASE 4 (muy importante)

- No editar permisos desde la UI.
- No crear ni eliminar roles desde la UI.
- No modificar el rol SA desde la UI.
- No asignar permisos a roles manualmente desde la UI.

Todo lo anterior se deja para FASE 5 cuando exista auditoría visual y flujos controlados.

---

## 6. Archivos tocados

- **Backend:** `backend/app.py` — rutas `/admin/roles`, `/admin/roles/<id>`, `/api/admin/roles`, `/api/admin/roles/<id>`, `/api/admin/permissions`, `/api/admin/roles/<id>/users`; uso de `ActivityLog.log_activity` para VIEW_ROLES.
- **Templates:** `templates/admin/roles/list.html`, `templates/admin/roles/detail.html`; columna Roles en `templates/admin/users.html`.
- **Navegación:** `templates/base.html` — enlace "Roles y Permisos" en menú admin (solo si `current_user.has_permission('roles.view')`); `templates/admin/dashboard.html` — botón "Roles y Permisos" en Acciones Rápidas (mismo permiso).

---

## 7. Próximos pasos (FASE 5)

- Asignación/desasignación de roles a usuarios (requiere `roles.assign`).
- Auditoría visual de cambios en roles/permisos.
- Posible edición controlada de permisos por rol (solo SA, con confirmación).
