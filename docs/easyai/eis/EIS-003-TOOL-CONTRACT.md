# EIS-003 — Tool Contract

| Campo | Valor |
|-------|--------|
| ID | **EIS-003** |
| Versión | **1.0.0** |
| Padre | EIS-000 |
| Estado | **Frozen / Approved** |

---

## 1. Propósito

Definir cómo un producto publica **Herramientas** invocables por EasyAI Core.

---

## 2. Descriptor canónico

```json
{
  "tool_id": "commerce.get_day_board",
  "connector_id": "eposone",
  "name": "Tablero del día",
  "description": "Resumen operacional de cajas y ventas del día de negocio.",
  "capability": "commerce.read",
  "side_effect": "read",
  "parameters_schema": { "$schema": "https://json-schema.org/draft/2020-12/schema", "type": "object", "properties": {}, "additionalProperties": false },
  "response_schema": { "type": "object" },
  "permissions": ["commerce.read"],
  "audit": { "level": "metadata", "include_args": false },
  "timeout_ms": 10000,
  "idempotent": true
}
```

| Campo | Requerido | Descripción |
|-------|-----------|-------------|
| `tool_id` | sí | `{domain}.{action}` estable |
| `name` / `description` | sí | Para descubrimiento y UX |
| `capability` | sí | Capability Catalog |
| `side_effect` | sí | `read` \| `write` \| `admin` |
| `parameters_schema` | sí | JSON Schema |
| `response_schema` | sí | JSON Schema |
| `permissions` | sí | Lista de permisos/scopes |
| `audit` | sí | Política de auditoría |
| `timeout_ms` | no | Default 10000 |
| `idempotent` | no | Default true si read |

---

## 3. Familias de acción (semántica)

| Familia | Verbos tipicos | `side_effect` típico |
|---------|----------------|----------------------|
| Consultar | get, list, search, verify | read |
| Crear | create, register, open | write |
| Actualizar | update, patch, assign | write |
| Eliminar | delete, void (soft) | write/admin |
| Publicar | publish, release | write |
| Procesar | process, close, reconcile | write |
| Analizar | summarize, rank (datos del producto) | read |
| Autorizar | approve, authorize | admin |
| Cancelar | cancel, revoke | write |

El verbo no implica LLM: “analizar” = agregación/reglas del **producto**.

---

## 4. Invocación

```text
invoke(tool_id, arguments, auth) → ToolResult
```

`ToolResult` (éxito):

```json
{
  "ok": true,
  "tool_id": "commerce.get_day_board",
  "data": { },
  "request_id": "…"
}
```

Fallo: EIS-008.

---

## 5. Permisos

1. EasyAI presenta scopes del caller (EIS-005).
2. Connector verifica `permissions` ⊆ grants.
3. Además aplica RBAC interno del producto si existe.
4. Tools `admin` / `write` requieren justificación en Manifest y revisión de seguridad.

---

## 6. Auditoría

| `audit.level` | Qué se registra |
|---------------|-----------------|
| `none` | Solo métricas agregadas (excepcional) |
| `metadata` | tool_id, actor, tenant, ok/error, duración |
| `full` | + args/respuesta redactados (PII policy) |

Default V1: `metadata` para read; `full` o `metadata`+hash para write.

El producto escribe en **su** audit trail; EasyAI puede duplicar metadata.

---

## 7. Prohibiciones

- Tools que acepten SQL libre del modelo.
- Tools que devuelvan dumps completos de tablas.
- Tools sin `description` usable.
- Side effect real marcado como `read`.
