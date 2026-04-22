# Instalación del módulo de registro de hoja de vida (CV) — guía para administradores

Esta guía sirve para **una instalación nueva** o un entorno donde aún no exista el servicio de catálogo `CV_REGISTRATION`. Si ya tenéis usuario admin y el servicio creado a mano, **no es obligatorio ejecutar nada**; guardad este documento para la próxima vez.

## Qué hace el módulo (resumen)

- **Tipo de servicio:** `CV_REGISTRATION` (valor fijo en el sistema).
- **Clave estable en catálogo:** `program_slug` (ej. `iius_cv_registration`) — permite volver a ejecutar el seed sin duplicar filas.
- **Público:** formulario en `/cv/registro?service=<id>` (el `id` sale del catálogo).
- **Admin:** listado en `/admin/cv-applications` (permiso `services.view`).

## Requisitos previos

1. Código del módulo CV desplegado (rutas, plantillas, modelo).
2. Tabla **`cv_application`** creada (arranque con `bootstrap_nodeone.py` o el proceso habitual de DDL de vuestra instalación).
3. Ruta a la base **SQLite** correcta (por defecto `instance/NodeOne.db` bajo la raíz del proyecto).

## Paso 1 — Archivo de configuración

1. Copiar el ejemplo:
   - De: `config/seed_cv_registration_service.example.json`
   - A: `config/seed_cv_registration_service.json`
2. Editar **como mínimo**:
   - `organization_id` — ID de la organización SaaS (suele ser `1` en IIUS).
   - `program_slug` — no cambiar salvo que sepáis que creáis otro producto CV distinto.
   - Dentro de `service`: `name`, `description`, `base_price`, `display_order`, `is_active`, etc.

El JSON **no contiene contraseñas**; puede versionarse en Git si lo deseáis (o mantener solo el `.example` en repo y el `.json` local).

## Paso 2 — Simulación (recomendado)

Desde el directorio `backend` del proyecto:

```bash
cd /ruta/al/proyecto/backend
../.venv/bin/python scripts/seed_cv_registration_service.py --dry-run
```

Debe mostrar `UPDATE` o `INSERT` y los valores finales. Si la ruta a la BD no es la por defecto:

```bash
../.venv/bin/python scripts/seed_cv_registration_service.py --dry-run --db /ruta/completa/NodeOne.db
```

O variable de entorno:

```bash
export NODEONE_DATABASE_PATH=/ruta/completa/NodeOne.db
../.venv/bin/python scripts/seed_cv_registration_service.py --dry-run
```

## Paso 3 — Aplicar en la base de datos

Quitar `--dry-run`:

```bash
../.venv/bin/python scripts/seed_cv_registration_service.py
```

Es **idempotente**: misma `organization_id` + mismo `program_slug` → actualiza la misma fila.

**Casos especiales:**

- Si ya existía **un solo** servicio `CV_REGISTRATION` sin `program_slug`, el script lo **reutiliza** y le asigna el `program_slug` del JSON.
- Si hay **varios** `CV_REGISTRATION` sin slug, el script se detiene con error; hay que limpiar o asignar slugs a mano.

## Paso 4 — Comprobaciones

1. **Admin → Catálogo de servicios:** el servicio aparece con tipo `CV_REGISTRATION` y el nombre configurado.
2. **Página pública de servicios:** el botón lleva a `/cv/registro?service=<id>`.
3. **Envío de prueba** del formulario y revisión en `/admin/cv-applications`.

## Usuario administrador

La creación del **usuario admin** y permisos RBAC **no** forma parte de este seed: seguid vuestro procedimiento habitual (invitación, SA, etc.). Este documento solo automatiza el **producto de catálogo** para no repetir campos a mano en cada instalación.

## Soporte

- Script: `backend/scripts/seed_cv_registration_service.py`
- Plantilla de datos: `config/seed_cv_registration_service.example.json`
