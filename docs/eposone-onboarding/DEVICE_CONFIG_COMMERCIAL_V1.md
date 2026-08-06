# Device Config — bloque `commercial` (Gate 1)

| Campo | Valor |
|-------|--------|
| Estado | **Implementado EN1** — 6 ago 2026 |
| ADR | ADR-027 |
| Superficies | `GET /api/v1/devices/config` · respuesta register · bootstrap `config.commercial` |

## Payload

```json
{
  "commercial": {
    "schema_version": 1,
    "product_code": "eposone",
    "plan_code": "standalone",
    "plan_name": "Standalone",
    "modality": "standalone",
    "operating_modality": "standalone",
    "sync_cloud": false
  }
}
```

| Campo | Valores |
|-------|---------|
| `modality` / `operating_modality` | `standalone` \| `connected` |
| `sync_cloud` | `false` si Standalone; `true` si Connected |
| `plan_code` | Comercial (`standalone`, `starter`, …) — **distinto** de `license.plan_code` (trial/caja) |

SoT: entitlement `plan_code` → catálogo (`local` se mapea a `standalone` hacia la APK).

## Fuera de este Gate

- Portal instalación UI  
- Login onboarding HTTP (contrato lógico sigue en LOGIN_CONTRACT_V1)  
