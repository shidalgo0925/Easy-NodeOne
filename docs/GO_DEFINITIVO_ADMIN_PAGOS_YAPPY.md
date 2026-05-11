# GO definitivo — Admin → Pagos / Yappy manual (appdev y despliegues)

Trabajo autorizado solo en `/opt/easynodeone/dev/app` (rama `develop`); staging/prod solo con `git pull` según `REGLAS-DE-TRABAJO.md`.

## 1. Confirmar entorno (en el servidor del silo)

En el host donde corre la app:

- **Dominio del navegador**: debe coincidir con el vhost de **dev** (no staging/prod).
- **Servicio systemd**: `systemctl status easynodeone-dev` (o el nombre real del silo; listar con `systemctl list-units 'easynodeone*'`).
- **Código en ejecución**: en la unidad, revisar `WorkingDirectory` y `ExecStart`; o `readlink -f /proc/<pid>/cwd` del proceso gunicorn/uwsgi.
- **Rama y commit**: `cd /opt/easynodeone/dev/app && git branch --show-current && git log -1 --oneline`.

## 2. Migración obligatoria

Desde el directorio del backend con el mismo Python/venv que usa el servicio:

```bash
cd /opt/easynodeone/dev/app/backend
# Ejemplo si el venv está en la raíz del repo:
../venv/bin/python migrate_yappy_manual_checkout_v3.py
```

El script **añade** columnas en `payment_config` y `payment`. No introduce nombres genéricos tipo `yappy_enabled` o `bank_transfer_enabled`; en el modelo/repo se usan otros nombres (ver tabla abajo).

**Validación MySQL** (ajustar base y usuario):

```sql
SHOW COLUMNS FROM payment_config LIKE 'yappy%';
SHOW COLUMNS FROM payment LIKE 'receipt%';
SHOW COLUMNS FROM payment LIKE 'organization_id';
```

### Nombres checklist → repo

| Checklist / producto (genérico) | En este repo (`payment_config` / API) |
|---------------------------------|----------------------------------------|
| yappy_enabled (toggle manual)   | `yappy_manual_enabled`                 |
| bank_transfer_enabled           | Depende de campos banco/transfer ya existentes en el modelo; no los añade solo v3 |
| international_transfer_enabled| `intl_wire_enabled`                    |
| yappy_directory_name, QR, etc.  | Igual en modelo si ya existían migraciones previas |

Columnas que **sí** añade `migrate_yappy_manual_checkout_v3.py` en `payment_config` (entre otras): `yappy_display_name`, `yappy_phone_or_identifier`, `yappy_instructions`, `yappy_requires_receipt`, `yappy_admin_validation_required`. En `payment`: `organization_id`, `payment_user_reference`, `receipt_uploaded_at`, `receipt_disk_path`, `rejection_reason`.

`yappy_phone_or_identifier` es **VARCHAR(120)** en modelo; backend sanea y devuelve **400 JSON** si el dato excede límites tras commit.

## 3. Reinicio del servicio

Tras `git pull` y migración:

```bash
sudo systemctl restart easynodeone-dev
```

(Usar la unidad real del silo.)

## 4. Contrato API (implementado)

- **PUT** `/api/admin/payments/config`: éxito `success`, `message` «Configuración guardada correctamente», `config`. Error longitud: `success: false`, `message` corto (Yappy 120), `error` con más contexto; esquema: **503** con `schema_migration_required`.
- **GET** mismo endpoint: `success`, `config`, `no_active_row` (plantilla vacía si no hay fila activa, sin forzar `success: false` solo por eso).

## 5. Frontend `admin/payments.html`

Validación previa de longitud (Yappy teléfono 120, nombre visible 200, directorio 100); mensaje de éxito usa `data.message` del backend.

## 6. Pruebas manuales (Casos A–D)

Después de migración + reinicio: crear config sin fila, editar fila existente, texto largo bloqueado sin 500, checkout con Yappy manual y comprobante según flujo ya cableado en checkout.
