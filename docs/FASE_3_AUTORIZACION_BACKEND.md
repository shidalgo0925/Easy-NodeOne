# FASE 3 — Autorización por permiso (backend)

**Proyecto:** app.example.com (nodeone)  
**Objetivo:** Cumplir la regla clave: **el backend valida siempre por permiso, nunca por rol.**

---

## 1. Entregables implementados

### 1.1 Modelos RBAC en `app.py`

- **Role:** `id`, `code`, `name`, `description`, `created_at`. Relación N:M con Permission vía `role_permission`.
- **Permission:** `id`, `code`, `name`, `description`, `created_at`. Relación N:M con Role.
- **User:** relación `roles` vía tabla `user_role` (secondary='user_role').

Las tablas `role`, `permission`, `role_permission`, `user_role` se crean con `backend/migrate_rbac_tables.py` (FASE 2).

### 1.2 Helper `User.has_permission(perm_code)`

- **Ubicación:** método en `User` (app.py).
- **Lógica:**
  1. Si el usuario tiene `is_admin` y **no** tiene filas en `user_role`, se considera con acceso total (compatibilidad con estado actual).
  2. Si no, se consulta si existe algún permiso con código `perm_code` en los roles del usuario (`user_role` → `role_permission` → `permission`).
- **Uso:** `current_user.has_permission('users.create')`, `current_user.has_permission('payments.manage')`, etc.

### 1.3 Decorador `require_permission(perm_code)`

- **Ubicación:** app.py (junto a `admin_required`).
- **Comportamiento:**
  - Aplica `@login_required`.
  - Si `current_user.has_permission(perm_code)` es False: responde 403 JSON si la petición es API, o redirect a dashboard con flash de error si es HTML.
- **Uso en rutas:**

```python
from app import require_permission

@app.route('/admin/users')
@require_permission('users.view')
def admin_users():
    ...
```

### 1.4 Compatibilidad `admin_required`

- **admin_required** sigue existiendo y se usa en la mayoría de rutas `/admin/*` y `/api/admin/*`.
- **Cambio:** ahora permite acceso si `current_user.is_admin` **o** si el usuario tiene al menos un rol RBAC con algún permiso (`_user_has_any_admin_permission`).
- Así, usuarios con solo `is_admin` (sin roles en RBAC) siguen entrando al panel; usuarios con solo roles RBAC (sin `is_admin`) también.

### 1.5 Rutas refactorizadas a @require_permission

- `GET /admin/users` → `users.view`
- `POST /admin/users/create` → `users.create`
- `POST /admin/users/<id>/update` → `users.update`
- `POST /admin/users/<id>/delete` → `users.delete` (AD no tiene este permiso en la matriz)
- `GET /admin/memberships` → `memberships.view`
- `GET /admin/services` → `services.view`

### 1.6 Asignación de rol AD a administradores existentes

- Script: `backend/assign_role_ad_to_admin_users.py`
- Asigna el rol AD a todos los usuarios con `is_admin=True` para que tengan permisos RBAC.
- Ejecutar una vez tras la migración RBAC: `python3 backend/assign_role_ad_to_admin_users.py`

---

## 2. Mapeo sugerido ruta → permiso

Para sustituir gradualmente `@admin_required` por `@require_permission(...)`:

| Recurso / ruta | Permiso sugerido |
|----------------|-------------------|
| /admin/users, /admin/users/create, update, delete | users.view, users.create, users.update, users.delete |
| /admin/memberships | memberships.view, memberships.assign |
| /admin/services, /api/admin/services/* | services.view, services.create, services.update, services.delete |
| /admin/payments, /api/admin/payments/* | payments.view, payments.manage |
| /admin/messaging, /admin/email, /api/admin/email/* | integrations.view o permisos específicos |
| /admin/notifications, /api/admin/notifications/* | system.settings.view o roles.update |
| /admin/reports, /api/admin/history/* | reports.view, reports.export |
| /admin/backup | system.settings.update (restringido) |
| /admin/discount-codes, /admin/membership-discounts | payments.manage o permisos de descuentos |
| Eventos admin (event_routes) | roles.view + eventos (o permiso dedicado) |
| Citas admin (appointment_routes) | services.view, services.manage |

Los blueprints `event_routes` y `appointment_routes` definen su propio `admin_required`; para unificar, se puede importar `require_permission` desde app y usarlo en las rutas críticas.

---

## 3. Uso en controladores

```python
# Comprobar permiso en lógica de negocio
if not current_user.has_permission('users.delete'):
    flash('No puedes eliminar usuarios.', 'error')
    return redirect(url_for('admin_users'))

# Decorar vista
@require_permission('payments.manage')
def admin_payments_review():
    ...
```

---

## 4. Próximos pasos

1. Asignar roles RBAC a usuarios (p. ej. insertar en `user_role` para administradores actuales con rol AD).
2. Sustituir más rutas de `@admin_required` por `@require_permission(permiso)` según la matriz roles–permisos.
3. Opcional: consola de asignación de roles (solo SuperAdmin) y auditoría de cambios en `user_role`.
