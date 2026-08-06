# EIS-002 — Context Contract

| Campo | Valor |
|-------|--------|
| ID | **EIS-002** |
| Versión | **1.0.0** |
| Padre | EIS-000 |
| Estado | **Frozen / Approved** |

---

## 1. Propósito

Definir cómo un producto **publica Contextos**: hechos de negocio serializables que EasyAI usa para grounding (no como dump de BD).

---

## 2. Forma canónica

```json
{
  "context_id": "organization.current",
  "connector_id": "en1-platform",
  "capability": "tenant.read",
  "title": "Organización activa",
  "schema_version": "1.0",
  "freshness": "request",
  "as_of": "2026-08-05T08:00:00Z",
  "payload": { }
}
```

| Campo | Requerido | Descripción |
|-------|-----------|-------------|
| `context_id` | sí | Id estable dotted |
| `connector_id` | sí | Dueño |
| `capability` | sí | Del Capability Catalog |
| `title` | sí | Humano, corto |
| `schema_version` | sí | Versión del shape de `payload` |
| `freshness` | sí | `request` \| `short_cache` \| `snapshot` |
| `as_of` | no | Instantánea UTC |
| `payload` | sí | Objeto JSON (DTO) |

---

## 3. Reglas

1. `payload` solo tipos JSON (object/array/string/number/bool/null).
2. **Prohibido:** filas ORM, conexiones DB, SQL, binarios grandes (> umbral de producto; default sugerido 256 KiB por context).
3. PII: marcar campos sensibles en descripción del catálogo; EasyAI aplica políticas de redaction propias.
4. Un Context describe **un recorte**; no “toda la empresa en un JSON”.
5. Ids de negocio estables (`organization_id`, `customer_ref`, …) — no PKs internas opacas sin mapear si el producto ya tiene refs públicas.

---

## 4. Familias de contexto (catálogo)

Ver [`catalogs/CONTEXT_CATALOG.md`](catalogs/CONTEXT_CATALOG.md). Familias mínimas del ecosistema:

| Familia | Ejemplos de `context_id` |
|---------|--------------------------|
| Organization / Tenant | `organization.current` |
| User | `user.actor` |
| Product (ETS product surface) | `product.surface` |
| Customer | `customer.summary` |
| CRM | `crm.pipeline_summary` |
| Membership | `membership.scope` |
| License | `license.summary` |
| Payment | `payment.mix_period` |
| Commerce | `commerce.day_summary` |
| Analytics | `analytics.kpi_snapshot` |
| Dashboard | `dashboard.operational` |

Un producto solo publica los que soporta; el resto no se inventan.

---

## 5. Obtención

Contrato lógico:

```text
resolve_contexts(auth, selector?) → Context[]
```

- `selector` opcional: lista de `context_id` o `capability`.
- Sin selector: conjunto **default** declarado en Manifest (`default_contexts`).

---

## 6. Versionado de payload

Cambios breaking en `payload` → subir `schema_version` MAJOR y, si afecta consumidores, Connector MAJOR.  
Campos nuevos opcionales → MINOR de `schema_version`.
