# EIS-008 — Error Contract

| Campo | Valor |
|-------|--------|
| ID | **EIS-008** |
| Versión | **1.0.0** |
| Padre | EIS-000 |
| Estado | **Frozen / Approved** |

---

## 1. Propósito

Unificar respuestas de error entre Connectors y EasyAI Core.

---

## 2. Forma canónica

```json
{
  "ok": false,
  "error": {
    "code": "validation_error",
    "message": "day_local must be YYYY-MM-DD",
    "details": { "field": "day_local" },
    "retryable": false,
    "request_id": "req_…"
  }
}
```

HTTP mapping (cuando haya transporte HTTP):

| code | HTTP sugerido |
|------|---------------|
| `unauthorized` | 401 |
| `forbidden` | 403 |
| `not_found` | 404 |
| `validation_error` | 400 |
| `business_error` | 409 o 422 |
| `timeout` | 504 |
| `unavailable` | 503 |
| `rate_limited` | 429 |
| `internal_error` | 500 |
| `not_implemented` | 501 |

---

## 3. Códigos estándar

| code | Significado |
|------|-------------|
| `unauthorized` | Auth ausente/inválida |
| `forbidden` | Auth OK, scope/permiso insuficiente |
| `not_found` | tool/context/recurso inexistente |
| `validation_error` | Args/schema inválidos |
| `business_error` | Regla de negocio del producto (caja cerrada, stock, etc.) |
| `timeout` | Tiempo de espera excedido |
| `unavailable` | Connector o dependencia caídos |
| `rate_limited` | Cuota |
| `conflict` | Conflicto de estado / idempotencia |
| `internal_error` | Error no clasificado del producto |
| `not_implemented` | Declarado en Manifest pero no listo |

---

## 4. Reglas

1. `message` seguro para logs; sin secretos.
2. `retryable=true` solo si un retry puede ayudar (`timeout`, `unavailable`, `rate_limited`).
3. `business_error` no es retryable por defecto.
4. Mismo `code` en in-process y HTTP.
5. EasyAI traduce errores a experiencia de usuario; no reexpone stack traces del producto.
