# FASE 2 — Modelo de datos RBAC (roles y permisos)

**Proyecto:** app.example.com (nodeone)  
**Objetivo:** Base de datos para autorización por permisos (RBAC), neutral al framework.  
**Regla clave:** El backend valida siempre por **permiso**, nunca por rol.

---

## 1. Modelo lógico

### 1.1 Entidades

| Entidad | Descripción |
|---------|-------------|
| **user** | Ya existe. Se mantiene `id` (PK). Se añade relación N:M con **role** vía **user_role**. |
| **role** | Rol del sistema (SA, AD, ST, TE, MI, IN). Código único, nombre, descripción. |
| **permission** | Permiso granular (ej. `users.create`, `payments.manage`). Código único. |
| **role_permission** | Tabla asociación: qué permisos tiene cada rol (N:M). |
| **user_role** | Tabla asociación: qué roles tiene cada usuario (N:M). Un usuario puede tener varios roles. |

### 1.2 Diagrama relacional (resumen)

```
user (existente)     user_role        role
    id (PK) -------- user_id    role_id -------- id (PK)
                      role_id                     code (UNIQUE)
                                                  name
                     role_permission    permission
                      role_id --------- role_id
                      permission_id --- id (PK)
                                        code (UNIQUE)
```

### 1.3 Convenciones

- **Códigos de rol:** SA, AD, ST, TE, MI, IN (mayúsculas, fijos).
- **Códigos de permiso:** `recurso.accion` en minúsculas, snake_case (ej. `users.create`, `payments.manage`).
- **Asignación de roles:**
  - SA (SuperAdministrador) no se asigna desde la UI; solo por base de datos o bootstrap.
  - Un usuario puede tener varios roles; los permisos son la unión de todos sus roles.
  - Si un usuario no tiene ningún rol, se considera sin permisos administrativos (equivalente a MI/IN según contexto).

---

## 2. Modelo físico (tablas)

### 2.1 Tabla `role`

| Columna | Tipo | Restricciones |
|---------|------|---------------|
| id | INTEGER | PK, autoincrement |
| code | VARCHAR(20) | UNIQUE, NOT NULL |
| name | VARCHAR(100) | NOT NULL |
| description | TEXT | opcional |
| created_at | DATETIME | default now |

### 2.2 Tabla `permission`

| Columna | Tipo | Restricciones |
|---------|------|---------------|
| id | INTEGER | PK, autoincrement |
| code | VARCHAR(80) | UNIQUE, NOT NULL |
| name | VARCHAR(120) | NOT NULL |
| description | TEXT | opcional |
| created_at | DATETIME | default now |

### 2.3 Tabla `role_permission`

| Columna | Tipo | Restricciones |
|---------|------|---------------|
| role_id | INTEGER | PK, FK → role.id, ON DELETE CASCADE |
| permission_id | INTEGER | PK, FK → permission.id, ON DELETE CASCADE |

Clave primaria compuesta (role_id, permission_id).

### 2.4 Tabla `user_role`

| Columna | Tipo | Restricciones |
|---------|------|---------------|
| user_id | INTEGER | PK, FK → user.id, ON DELETE CASCADE |
| role_id | INTEGER | PK, FK → role.id, ON DELETE CASCADE |
| assigned_at | DATETIME | default now |
| assigned_by_id | INTEGER | nullable (referencia lógica a user.id; FK no creada en migración para independencia del metadata). |

Clave primaria compuesta (user_id, role_id). Opcional: assigned_by_id para auditoría. La migración `migrate_rbac_tables.py` no crea FK a `user` para ser autocontenida; en FASE 3 los modelos ORM pueden definir la relación.

---

## 3. Catálogo de permisos (semilla)

Permisos normalizados a insertar en `permission`:

**Usuarios:** `users.view`, `users.create`, `users.update`, `users.delete`, `users.assign_roles`, `users.suspend`  
**Roles y permisos:** `roles.view`, `roles.create`, `roles.update`, `roles.delete`, `permissions.view`  
**Servicios y membresías:** `services.view`, `services.create`, `services.update`, `services.delete`, `memberships.view`, `memberships.assign`, `memberships.suspend`  
**Pagos:** `payments.view`, `payments.manage`, `payments.refund`  
**Reportes:** `reports.view`, `reports.export`  
**Integraciones:** `integrations.view`, `integrations.manage`, `api.keys.create`, `api.keys.revoke`  
**Sistema:** `system.settings.view`, `system.settings.update`, `audit.logs.view`

---

## 4. Roles (semilla)

| code | name |
|------|------|
| SA | SuperAdministrador |
| AD | Administrador |
| ST | Staff / Operaciones |
| TE | Técnico / Integraciones |
| MI | Miembro |
| IN | Invitado |

SA tiene todos los permisos (asignación por script o “wildcard”). El resto según matriz roles–permisos (ver documento de matriz entregado).

---

## 5. Reglas de asignación

1. **SA:** No asignable desde UI. Solo por script/DB. Tiene todos los permisos (insertar todos los role_permission para SA o tratar SA como bypass en código).
2. **AD:** No puede recibir permiso equivalente a SA. No puede `users.delete` ni `roles.delete` ni `system.settings.update` si se sigue la matriz estricta.
3. **user_role:** Al asignar un rol a un usuario, registrar opcionalmente `assigned_by_id` y `assigned_at`.
4. **Compatibilidad con estado actual:** Hasta que FASE 3 esté desplegada, se puede mantener `user.is_admin` y considerar “si is_admin y no tiene roles RBAC, tratar como AD” para no romper producción. Luego migrar a “solo RBAC”.

---

## 6. SQL de referencia (SQLite)

Ver script `backend/migrate_rbac_tables.py` que crea las tablas e inserta roles y permisos. El SQL equivalente se puede extraer de ese script o generarse con las herramientas del proyecto.

---

## 7. Próximo paso (FASE 3)

- Añadir modelos SQLAlchemy `Role`, `Permission`, `RolePermission`, `UserRole` en `app.py` (o módulo compartido).
- Implementar `current_user.has_permission('permiso.code')` (carga de permisos desde roles del usuario).
- Sustituir `@admin_required` por `@require_permission('permiso')` en rutas críticas.
- Mantener `is_admin` solo como compatibilidad o eliminarlo cuando todo use permisos.
