# FASE 5 — Asignación de roles a usuarios (UI + auditoría)

**Proyecto:** membresia-relatic  
**Objetivo:** Permitir a administradores con permiso `roles.assign` asignar y quitar roles a usuarios, con validación exclusiva por permisos y auditoría obligatoria.

---

## 1. Alcance exacto

### ✅ Se implementa

- Asignar y quitar roles a usuarios.
- Validación exclusiva por permisos (`roles.assign`, `users.view`).
- Auditoría obligatoria de cada cambio (ASSIGN_ROLE, UNASSIGN_ROLE).
- UI administrativa controlada: `/admin/users`, `/admin/users/:id/roles`.
- SA oculto y protegido (no asignable ni visible en selectores).

### ❌ No se implementa en FASE 5

- Crear / eliminar roles.
- Crear / eliminar permisos.
- Editar permisos de roles.
- Cualquier cambio sobre rol SA desde la UI.

---

## 2. Permisos requeridos

| Código           | Uso                                      |
|------------------|------------------------------------------|
| `roles.assign`   | Asignar y quitar roles a usuarios        |
| `users.view`     | Ver listado de usuarios y detalle        |
| `audit.logs.view`| Consultar logs (ya existente)            |

**Regla dura:** `roles.assign` no se asigna a MI, ST, TE. SA siempre fuera de la UI (no se muestra en listas de roles asignables).

---

## 3. Backend — Endpoints

Todos los que modifican datos requieren `roles.assign`. Los de solo lectura requieren `users.view` (y `roles.assign` donde aplique para la pantalla de asignación).

| Método | Ruta | Descripción | Permiso |
|--------|------|-------------|---------|
| GET | `/api/admin/users` | Listado de usuarios (id, email, nombre, estado, roles) | `users.view` |
| GET | `/api/admin/users/<id>/roles` | Roles del usuario + roles disponibles para asignar (excl. SA) | `users.view` + `roles.assign` |
| POST | `/api/admin/users/<id>/roles` | Asignar rol al usuario. Body: `{ "role_id": N }` | `roles.assign` |
| DELETE | `/api/admin/users/<id>/roles/<role_id>` | Quitar rol al usuario | `roles.assign` |

### Validaciones

- **POST:** Usuario existe; rol existe; rol no es SA; usuario no tiene ya ese rol; `assigned_by_id` = `current_user.id`.
- **DELETE:** Usuario existe; rol existe; usuario tiene ese rol; no intentar quitar SA (rechazar si `role.code == 'SA'`).

---

## 4. Auditoría

Registrar en `ActivityLog`:

| Acción        | entity_type | entity_id | description (ejemplo)     |
|---------------|-------------|-----------|---------------------------|
| ASSIGN_ROLE   | user_role   | user_id   | role=AD user=12 assigned  |
| UNASSIGN_ROLE | user_role   | user_id   | role=ST user=12 removed  |

Incluir IP y User-Agent vía `request` en `log_activity`.

---

## 5. UI

- **Pantalla existente:** `/admin/users` — Añadir enlace "Gestionar roles" por fila (visible solo si `current_user.has_permission('roles.assign')`), que lleve a `/admin/users/<id>/roles`.
- **Pantalla nueva:** `/admin/users/<id>/roles`
  - Datos del usuario (nombre, email, estado).
  - Lista de roles actuales con botón "Quitar" (confirmación antes de enviar DELETE).
  - Selector para añadir rol (solo roles no-SA y que el usuario no tenga) + botón "Asignar" (confirmación opcional).
  - SA no aparece en el selector ni en la lista de "roles disponibles".

Stack: Flask + Jinja (alineado con el resto del admin). Confirmaciones con `confirm()` en JS o modal Bootstrap.

---

## 6. Rutas HTML (UI)

| Ruta | Descripción | Permiso |
|------|-------------|---------|
| `/admin/users` | Listado de usuarios (existente). Enlace "Gestionar roles" por fila si `roles.assign`. | `users.view` |
| `/admin/users/<id>/roles` | Pantalla de asignación: roles actuales (con Quitar) + selector para Asignar. SA oculto. | `roles.assign` |

Confirmación con `confirm()` en JS antes de asignar y antes de quitar.

---

## 7. Checklist de seguridad

- [x] Ningún endpoint valida por rol; solo por permiso (`@require_permission`).
- [x] SA no se lista como rol asignable en APIs ni en UI.
- [x] No se puede asignar SA por API (rechazo 403).
- [x] No se puede quitar SA por API (rechazo 403).
- [x] Toda asignación y desasignación queda registrada en ActivityLog (ASSIGN_ROLE, UNASSIGN_ROLE).
- [x] `assigned_by_id` se persiste en `user_role` en cada asignación.
- [x] La pantalla de asignación solo es accesible con `roles.assign`.
- [x] No hay lógica de seguridad en frontend (ocultar botones es UX; el backend rechaza sin permiso).
