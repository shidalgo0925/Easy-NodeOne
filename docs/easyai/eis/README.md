# Easy Integration Specification (EIS) v1.0 — Índice Frozen

| Campo | Valor |
|-------|--------|
| Nombre normativo | **Easy Integration Specification (EIS)** |
| Nombre comercial del conjunto de contratos | **Connector SDK** (definido *por* el EIS — no es norma aparte) |
| Versión | **1.0.0** |
| Estado | **Frozen / Approved** — [`FROZEN.md`](FROZEN.md) |
| ADR | [`ADR-026`](../../ADR-026-EASY-INTEGRATION-SPECIFICATION-V1.md) |
| Fecha | 5 ago 2026 |
| Artefactos | Solo documentación (sin código CODITO) |

---

## Norma única

```text
EIS v1.0
 ├── define → Connector SDK (contratos)
├── Contexts
├── Tools
├── Events
├── Sessions
├── Discovery
├── Capabilities
├── Security (+ Authentication)
├── Versionado & Compatibilidad
├── Errors
├── Manifest
└── Checklist de conformidad
```

**No existen** como normas separadas: “Connector SDK SPEC”, “AI SDK”, ni forks por producto.

---

## Documentos normativos

| ID | Título | Archivo |
|----|--------|---------|
| **EIS-000** | Easy Integration Specification (raíz) | [`EIS-000-INTEGRATION-STANDARD.md`](EIS-000-INTEGRATION-STANDARD.md) |
| **EIS-001** | Connector SDK Specification | [`EIS-001-CONNECTOR-SPECIFICATION.md`](EIS-001-CONNECTOR-SPECIFICATION.md) |
| **EIS-002** | Contexts | [`EIS-002-CONTEXT-CONTRACT.md`](EIS-002-CONTEXT-CONTRACT.md) |
| **EIS-003** | Tools | [`EIS-003-TOOL-CONTRACT.md`](EIS-003-TOOL-CONTRACT.md) |
| **EIS-004** | Events | [`EIS-004-EVENT-CONTRACT.md`](EIS-004-EVENT-CONTRACT.md) |
| **EIS-005** | Authentication | [`EIS-005-AUTHENTICATION.md`](EIS-005-AUTHENTICATION.md) |
| **EIS-006** | Connector Manifest | [`EIS-006-CONNECTOR-MANIFEST.md`](EIS-006-CONNECTOR-MANIFEST.md) |
| **EIS-007** | Discovery | [`EIS-007-DISCOVERY-PROTOCOL.md`](EIS-007-DISCOVERY-PROTOCOL.md) |
| **EIS-008** | Errors | [`EIS-008-ERROR-CONTRACT.md`](EIS-008-ERROR-CONTRACT.md) |
| **EIS-009** | Sessions | [`EIS-009-SESSIONS.md`](EIS-009-SESSIONS.md) |
| **EIS-010** | Versionado y Compatibilidad | [`EIS-010-VERSIONING-COMPATIBILITY.md`](EIS-010-VERSIONING-COMPATIBILITY.md) |
| **EIS-011** | Security | [`EIS-011-SECURITY.md`](EIS-011-SECURITY.md) |

---

## Catálogos

| Catálogo | Archivo |
|----------|---------|
| Connectors | [`catalogs/CONNECTOR_CATALOG.md`](catalogs/CONNECTOR_CATALOG.md) |
| Contexts | [`catalogs/CONTEXT_CATALOG.md`](catalogs/CONTEXT_CATALOG.md) |
| Tools | [`catalogs/TOOL_CATALOG.md`](catalogs/TOOL_CATALOG.md) |
| Events | [`catalogs/EVENT_CATALOG.md`](catalogs/EVENT_CATALOG.md) |
| Capabilities | [`catalogs/CAPABILITY_CATALOG.md`](catalogs/CAPABILITY_CATALOG.md) |

---

## Conformidad y validación

| Artefacto | Archivo |
|-----------|---------|
| Checklist de conformidad | [`CONFORMITY-CHECKLIST.md`](CONFORMITY-CHECKLIST.md) |
| Validación cruzada ARP–CODITO–LOCAL | [`VALIDATION-CROSS-ARP-CODITO-LOCAL.md`](VALIDATION-CROSS-ARP-CODITO-LOCAL.md) |
| Validación productos (histórica S1) | [`VALIDATION-ETS-PRODUCTS.md`](VALIDATION-ETS-PRODUCTS.md) |

---

## Diagramas

| Diagrama | Archivo |
|----------|---------|
| Overview integración | [`diagrams/EIS-INTEGRATION-OVERVIEW.md`](diagrams/EIS-INTEGRATION-OVERVIEW.md) |
| Reparto roles | [`diagrams/EIS-ROLES-ARP-CODITO-LOCAL.md`](diagrams/EIS-ROLES-ARP-CODITO-LOCAL.md) |
| Session + invoke | [`diagrams/EIS-SESSION-INVOKE.md`](diagrams/EIS-SESSION-INVOKE.md) |

---

## Reparto post-freeze

| Rol | Hace | No hace |
|-----|------|---------|
| **CODITO** | Mantiene EIS (cambios versionados) | Runtime IA, Connectors producto, código EN1 |
| **ARP** | EasyAI Core runtime (Gateway, Context Builder, Tool Dispatcher, Memory, Conversation) | Redefinir contratos EIS |
| **LOCAL** | EPOSOne Operations Connector | Modificar EIS |

---

## Histórico no normativo

- Borrador EN1 `docs/easyai/*.md` (pre-EIS) y `backend/nodeone/core/easyai/` = **draft de implementación EN1**, no norma.
- Roadmap S1: [`ROADMAP-S1.md`](ROADMAP-S1.md) (cerrado documentalmente).
