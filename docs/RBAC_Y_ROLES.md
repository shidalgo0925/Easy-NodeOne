# RBAC, roles y administración (Easy NodeOne)

## Ideas clave

1. **Permiso, no rol en código de negocio**  
   En backend se comprueba `user.has_permission('users.view')`, no “si es SA”. Los roles solo agrupan permisos en BD.

2. **`is_admin` (legacy)**  
   Sigue existiendo. Si `is_admin=True` y el usuario **no tiene ninguna fila en `user_role`**, la app le trata como con acceso amplio (compatibilidad). En cuanto tiene roles RBAC, **mandan los permisos** de esos roles.

3. **Roles del sistema** (semilla en `migrate_rbac_tables.py`)

   | Código | Nombre | Uso típico |
   |--------|--------|------------|
   | **SA** | SuperAdministrador | Plataforma: todos los permisos; gestión de roles (excepto asignar SA por API). |
   | **AD** | Administrador | Admin de tenant: casi todo salvo algunos borrados y `system.settings.update`. |
   | **ST** | Staff / Operaciones | Usuarios, servicios vista, membresías, pagos vista, informes. |
   | **TE** | Técnico / Integraciones | Integraciones, API keys, auditoría. |
   | **MI** / **IN** | Miembro / Invitado | Portal miembro (según lo que implementéis encima). |

4. **Dónde se definen permisos por rol**  
   Tablas `role`, `permission`, `role_permission`. Cambiar la matriz implica migración o script SQL/ORM; la semilla inicial está en `backend/migrate_rbac_tables.py`.

---

## Cómo “aplicar” roles en la práctica

### Superadmin SA de plataforma (`shidalgo@easytech.services`)

- **En cada arranque** (bootstrap antes de Gunicorn) se ejecuta `ensure_platform_sa_user` (`nodeone/services/platform_sa_seed.py`):
  - Garantiza semilla RBAC si hace falta.
  - Si **ya existe** el usuario con el correo configurado → `is_admin=True`, activo, email verificado, rol **SA**.
  - Si **aún no existe** el usuario → solo se registra un mensaje en log; hay que crearlo una vez (registro, `create_admin_user.py` o `seed_initial_admin.py`); **al siguiente reinicio** quedará con SA.

**Variables de entorno**

- `PLATFORM_SA_EMAIL`  
  - *No definida* → se usa `shidalgo@easytech.services`.  
  - *Definida y vacía* → se **deshabilita** esta semilla (útil si no queréis correo fijo en código).  
  - *Definida con correo* → ese es el superadmin de plataforma a asegurar.

- El rol **SA no se puede asignar** desde la API `/api/admin/users/.../roles` (respuesta 403); es a propósito.

- Para otros correos o reaplicar a mano:  
  `cd backend && ../venv/bin/python3 promote_superuser.py otro@correo.com`

### Administradores y roles del resto de usuarios

1. Entrar con un usuario que tenga **`roles.assign`** (SA o AD con ese permiso).
2. **Administración → Usuarios** (`/admin/users`).
3. En cada fila, botón **escudo** “Gestionar roles” → pantalla de asignación (o `templates/admin/users/roles.html`).
4. Ahí se añaden o quitan roles **AD, ST, TE, …** (no SA).

Sin filas en `user_role`, aunque `is_admin=True`, el menú puede ocultar cosas que dependen de `has_permission('roles.view')`, etc. Por eso conviene **asignar al menos AD** a admins de empresa además del flag `is_admin` (script histórico: `assign_role_ad_to_admin_users.py`).

### Usuarios normales / miembros

- **No** suelen tener roles `SA`/`AD`/`ST`/`TE`; acceden al portal según membresía y `organization_id`.
- Dar **admin** a alguien de una org: marcar `is_admin` en usuario + rol **AD** (o el que defináis) desde el panel.

---

## Scripts útiles (backend/)

| Script | Función |
|--------|---------|
| `migrate_rbac_tables.py` | Crea tablas RBAC y semilla roles/permisos si faltan. |
| `promote_superuser.py` | Marca un usuario existente como `is_admin` + rol SA. |
| `create_admin_user.py` | Crea admin con contraseña; opción `--force` si el email ya existe. |
| `assign_role_ad_to_admin_users.py` | Añade rol AD a todos los `is_admin=True` que no lo tengan. |

---

## Resumen operativo

- **Tu cuenta SA** queda **reconciliada en cada deploy/restart** si el correo coincide con `PLATFORM_SA_EMAIL` (por defecto `shidalgo@easytech.services`) y el usuario ya existe en BD.
- **Quién es admin de cada empresa** lo definís en **Usuarios** + **roles** (y `is_admin` donde aplique).
- **Permisos finos** = matriz rol ↔ permiso en BD; ampliar = nueva fila en `permission` + `role_permission` (y código que llame `has_permission`).
