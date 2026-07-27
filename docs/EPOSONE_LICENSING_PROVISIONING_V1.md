# EN1 / EPosOne — Licenciamiento y Provisioning V1.0 (congelado)

## Decisión

| Concepto | Unidad | Pregunta |
|----------|--------|----------|
| **Licencia** | **Caja** | ¿Puede operar comercialmente? |
| **Provisioning** | Dispositivo ↔ Caja | ¿Qué tablet pertenece a esta caja? |
| Usuario/cajero | Permisos | Nunca consume licencia |
| Tablet | Reemplazable | Nunca consume licencia adicional |

Jerarquía: `Empresa → Sucursal → POS → Caja → (Licencia + Dispositivo)`.

## Provisioning

- Código **temporal**, **un solo uso**, pertenece a **una Caja**.
- TTL configurable (`eposone_settings.provisioning_code_ttl_minutes`, default 30).
- Al usarse → estado `used`; al vencer → `expired`.
- No crea cajas, no inicia ni reinicia trial por sí solo (salvo política de trial al primer vínculo).
- Reemplazo de tablet = nuevo código; la Caja y su licencia se mantienen.

## Licencia

Persistencia: `eposone_register_license` (1 fila por org + `register_ref`).

Tipos: `trial`, `subscription`, `courtesy`, `promotion`, `demo`, `perpetual`, `suspended`, `unlicensed`.

Campos anti-abuso de trial: `trial_used`, `trial_started_at`, `trial_expires_at`.

Política org (`eposone_settings`):

- `trial_days_default` (default 45, **configurable**)
- `trial_start_policy`: `on_create` | `on_activate` | `on_first_provision` (default)
- `offline_grace_days` (default 7)

Admin BO: menú en Cajas → Activar trial / Extender / Cortesía / Permanente  
(`POST /admin/eposone/registers/<register_ref>/license`).

## Códigos comerciales

Tabla `eposone_commercial_code` (scaffold). **Distintos** del provisioning.  
Sirven para regalar/activar días o planes; no vinculan tablets.

## APK

`GET config` incluye bloque `license` con `can_operate`, fechas y `days_remaining`.  
La decisión la toma **EN1**; el APK no calcula 45 días fijos.

## Pantalla Cajas

Dos columnas independientes:

1. **Estado técnico**: Sin dispositivo / Código generado / Asignada / Desconectada / Turno…
2. **Estado comercial**: Sin licencia / Trial / Activa / Cortesía / Vencida…

## No mezclar

Reinstalar APK ≠ nuevos 45 días.  
Provisioning ≠ licencia.  
Vender por **caja activa**, no por usuario ni por tablet.
