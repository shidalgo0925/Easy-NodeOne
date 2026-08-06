# EIS-006 — Connector Manifest

| Campo | Valor |
|-------|--------|
| ID | **EIS-006** |
| Versión | **1.0.0** |
| Padre | EIS-000 |
| Estado | **Frozen / Approved** |

---

## 1. Propósito

Definir el **manifiesto obligatorio** de cada Connector: declaración estática descubrible.

Media-type sugerido: `application/vnd.ets.eis.manifest.v1+json`  
Path Discovery típico: `/.well-known/easyai-connector.json` o URL en Connector Catalog.

---

## 2. Schema (campos)

```json
{
  "eis_version": "1.0.0",
  "connector_id": "eposone",
  "connector_version": "1.0.0",
  "name": "EPosOne",
  "product": {
    "product_code": "eposone",
    "display_name": "EPosOne"
  },
  "description": "Operación POS y comercio.",
  "lifecycle": "ready",
  "environments": ["dev", "prod"],
  "base_url": "https://appprd.easynodeone.com",
  "auth": {
    "tenant_claim": "organization_id",
    "auth_methods": ["bearer_jwt"],
    "jwks_url": null
  },
  "capabilities": ["commerce.read", "commerce.events", "license.read"],
  "default_contexts": ["organization.current", "commerce.day_summary"],
  "contexts": [
    { "context_id": "commerce.day_summary", "capability": "commerce.read", "schema_version": "1.0" }
  ],
  "tools": [
    { "tool_id": "commerce.get_day_board", "capability": "commerce.read", "side_effect": "read" }
  ],
  "events": [
    { "event_type": "Commerce.CashShiftClosed", "capability": "commerce.events" }
  ],
  "event_aliases": {
    "eposone.order.created": "Commerce.OrderCreated"
  },
  "permissions": ["commerce.read", "license.read"],
  "dependencies": [],
  "contact": { "team": "CODITO", "email": null },
  "documentation_url": "https://…"
}
```

### Requeridos

`eis_version`, `connector_id`, `connector_version`, `name`, `product.product_code`, `lifecycle`, `capabilities`, `contexts`, `tools`, `events`, `auth.auth_methods`, `auth.tenant_claim`.

### Opcionales

`dependencies`, `event_aliases`, `default_contexts`, `jwks_url`, `documentation_url`, `contact`.

---

## 3. Dependencias

`dependencies[]`: otros `connector_id` o capabilities que deben estar ready (documental; no resolución automática obligatoria en V1).

---

## 4. Permisos

`permissions[]` declara el máximo que el Connector puede exigir.  
Tools individuales no pueden pedir permisos fuera de esta lista.

---

## 5. Validación de Manifest

Un Manifest es inválido si:

- Falta campo requerido.
- `tool_id` duplicado.
- `capability` no está en Capability Catalog (o en extensión registrada).
- `side_effect=write` sin capability `*.write` o equivalente.
- `eis_version` major > soportada por EasyAI.

---

## 6. Inmutabilidad publicada

El Manifest servido en un ambiente + `connector_version` no se muta en silencio. Cambio → nueva `connector_version`.
