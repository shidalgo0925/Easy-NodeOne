# EPosOne ↔ EN1 — Contrato oficial License Engine V1.0

| Campo | Valor |
|-------|--------|
| Estado | **IMPLEMENTADO EN DEV** — en `develop` (License Engine V1) |
| Versión | **License schema_version = 1** |
| Unidad comercial | **Caja** (`register_ref`) — ADR-007 |
| Canal | Bootstrap `GET /api/v1/devices/bootstrap` (+ sync autorizado) |
| Auth | `Authorization: Bearer <DeviceToken>` |
| Audiencia | **Prog2** — consumir `license` sin inventar Trial ni deducir features del plan |

Cambios = **v1.1+** + GO. No reinterpretar.

---

## 1. Ownership

EN1 es la única fuente de verdad. Crea, renueva, suspende, revoca, cambia permisos/límites, calcula fechas y **estado efectivo**.

La APK: descarga → persiste → valida local → aplica features. **Nunca** inventa Trial comercial local.

---

## 2. Bloque obligatorio `license`

```json
{
  "license": {
    "schema_version": 1,
    "license_id": "lic_123",
    "license_type": "TRIAL",
    "status": "ACTIVE",
    "plan_code": "trial",
    "activation_method": "EN1",
    "issued_at": "2026-07-24T14:00:00-05:00",
    "starts_at": "2026-07-24T14:00:00-05:00",
    "expires_at": "2026-08-08T23:59:59-05:00",
    "grace_until": null,
    "last_validation": "2026-07-24T14:00:00-05:00",
    "features": [
      "sales",
      "payments",
      "cash_shifts",
      "customers",
      "reports"
    ],
    "limits": {
      "max_devices": 1,
      "max_cashiers": null,
      "max_products": null
    },
    "updated_at": "2026-07-24T14:00:00-05:00"
  }
}
```

### Campos

| Campo | Tipo | Notas |
|-------|------|--------|
| `schema_version` | int | Siempre `1` en V1 |
| `license_id` | string | `lic_{id}` EN1 |
| `license_type` | enum | `TRIAL` `MONTHLY` `ANNUAL` `PERPETUAL` `PARTNER` `OEM` `INTERNAL` `EDUCATIONAL` |
| `status` | enum | `PENDING` `ACTIVE` `GRACE` `EXPIRED` `SUSPENDED` `REVOKED` |
| `plan_code` | string | Etiqueta comercial; **no** usar para gates |
| `activation_method` | enum | V1: `EN1` (otros reservados) |
| Fechas | ISO-8601 + TZ org | `expires_at`/`grace_until` null si no aplican |
| `features` | string[] | Capacidades efectivas |
| `limits` | object | Cupos; `null` = sin tope |
| `last_validation` | ISO | Actualizado en cada bootstrap/serve |

---

## 3. Trial (EN1)

Al **primer** device provisionado sobre una Caja elegible sin Trial previo:

- `license_type=TRIAL`, `status=ACTIVE`, **15 días**, `activation_method=EN1`
- `trial_used=true` en la fila de la **Caja**

No reinicia por: reinstalar APK, borrar datos, reprovisionar, rotar token, otra tablet en la misma Caja.

---

## 4. Estados y operación

| Status | APK |
|--------|-----|
| `ACTIVE` | Opera |
| `GRACE` | Opera + advertencia |
| `EXPIRED` / `SUSPENDED` / `REVOKED` / `PENDING` | No opera (según FeatureManager Prog2) |

EN1 calcula el status **antes** de emitir. Grace: Trial = **0 días**; mensual/anual = `offline_grace_days` de org (configurable; **no** hardcode 30).

---

## 5. Features

La APK consulta `features.contains("reports")`, **nunca** `plan_code == Professional`.

Defaults Trial V1: `sales`, `payments`, `cash_shifts`, `customers`, `reports`.

---

## 6. Sync / heartbeat

Cada bootstrap (y futuro sync que reutilice el mismo serve) llama `RegisterLicenseService.serve_for_device` → recalcula, toca `last_validation`, emite snapshot.

Evento: `license.bootstrap_served`.

---

## 7. Auditoría

`license.created` · `license.renewed` · `license.updated` · `license.suspended` · `license.reactivated` · `license.expired` · `license.revoked` · `license.bootstrap_served` · `license.validation_failed`

---

## 8. Fuera de alcance V1

Portal · pagos · activation code · archivo firmado · marketplace módulos.

---

## 9. Código EN1

| Pieza | Path |
|-------|------|
| Servicio | `backend/nodeone/modules/eposone/register_license_service.py` |
| Modelo | `backend/models/eposone_register_license.py` |
| Bootstrap | `device_provisioning._license_block_for_register` |
| DDL | `eposone_register_license_schema.py` |

BO: acciones `suspend` / `reactivate` en POST licencia de caja.

---

## 10. Changelog

| Versión | Fecha | Cambio |
|---------|-------|--------|
| **v1.0** | 2026-07-24 | Contrato bootstrap License Engine; Trial 15d; features/limits; GRACE; audit |

Tag previsto (cuando se cierre): `eposone-license-engine-v1.0`
