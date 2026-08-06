# EIS-010 — Versionado y Compatibilidad

| Campo | Valor |
|-------|--------|
| ID | **EIS-010** |
| Versión | **1.0.0** |
| Estado | **Frozen / Approved** |
| Padre | EIS-000 |

---

## 1. Tres relojes de versión

| Artefacto | Campo | Quién sube |
|-----------|-------|------------|
| Norma EIS | `eis_version` (SemVer) | CODITO + ADR |
| Connector | `connector_version` | Owner del producto |
| Schemas Context/Tool/Event | `schema_version` | Owner en Manifest |

---

## 2. SemVer EIS

- **MAJOR** — ruptura (Connectors 1.x pueden dejar de ser válidos sin adaptación).
- **MINOR** — adiciones compatibles (campos opcionales, nuevas capabilities canónicas).
- **PATCH** — clarificaciones editoriales.

**v1.0.0** está Frozen. Siguiente ruptura = **2.0.0**.

---

## 3. Compatibilidad EasyAI ↔ Connector

| EasyAI Core soporta | Acepta Connectors |
|---------------------|-------------------|
| EIS 1.x | `eis_version` 1.x |
| EIS 2.x | Debe documentar ventana de deprecación 1.x |

Reglas:

1. Campos nuevos **opcionales** en MINOR: Connectors viejos ignoran; EasyAI no los exige.
2. Renombrar `tool_id` / `context_id` / `event_type` = breaking → Connector MAJOR + alias en Manifest (`event_aliases` / tool aliases si se añaden).
3. EasyAI puede pinnear `connector_version` mínima por ambiente.

---

## 4. Compatibilidad entre Connectors

Los Connectors no dependen entre sí en runtime v1.  
`dependencies[]` en Manifest es **documental** (orden de readiness), no resolución automática obligatoria.

---

## 5. Política de deprecación

1. Marcar `lifecycle: deprecated` + fecha ISO de retiro.
2. Mantener comportamiento hasta la fecha.
3. Pasar a `retired`; EasyAI deja de despachar Tools.

---

## 6. Pruebas de conformidad de versión

Checklist incluye: Manifest declara `eis_version` compatible; schemas versionados; no uso de campos removed en MAJOR anterior.
