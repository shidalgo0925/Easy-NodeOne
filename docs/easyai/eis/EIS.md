# EIS — Easy Integration Specification v1.0.0 Frozen

| Campo | Valor |
|-------|--------|
| Norma | **Easy Integration Specification (EIS)** |
| Versión | **1.0.0** |
| Estado | **Frozen / Approved** |
| ADR | [`ADR-026`](../../ADR-026-EASY-INTEGRATION-SPECIFICATION-V1.md) |
| Índice | [`README.md`](README.md) |
| Sello | [`FROZEN.md`](FROZEN.md) |
| Handoff ARP/LOCAL | [`HANDOFF-ARP-LOCAL.md`](HANDOFF-ARP-LOCAL.md) |
| Checklist | [`CONFORMITY-CHECKLIST.md`](CONFORMITY-CHECKLIST.md) |

Este archivo es el **punto de entrada** del paquete oficial para Gate 0 (LOCAL / ARP).  
No redefine contratos: remite al pack normativo bajo `docs/easyai/eis/`.

## SPECs (normativos)

| ID | Archivo |
|----|---------|
| EIS-000 | [`EIS-000-INTEGRATION-STANDARD.md`](EIS-000-INTEGRATION-STANDARD.md) |
| EIS-001 | [`EIS-001-CONNECTOR-SPECIFICATION.md`](EIS-001-CONNECTOR-SPECIFICATION.md) |
| EIS-002 | [`EIS-002-CONTEXT-CONTRACT.md`](EIS-002-CONTEXT-CONTRACT.md) |
| EIS-003 | [`EIS-003-TOOL-CONTRACT.md`](EIS-003-TOOL-CONTRACT.md) |
| EIS-004 | [`EIS-004-EVENT-CONTRACT.md`](EIS-004-EVENT-CONTRACT.md) |
| EIS-005 | [`EIS-005-AUTHENTICATION.md`](EIS-005-AUTHENTICATION.md) |
| EIS-006 | [`EIS-006-CONNECTOR-MANIFEST.md`](EIS-006-CONNECTOR-MANIFEST.md) |
| EIS-007 | [`EIS-007-DISCOVERY-PROTOCOL.md`](EIS-007-DISCOVERY-PROTOCOL.md) |
| EIS-008 | [`EIS-008-ERROR-CONTRACT.md`](EIS-008-ERROR-CONTRACT.md) |
| EIS-009 | [`EIS-009-SESSIONS.md`](EIS-009-SESSIONS.md) |
| EIS-010 | [`EIS-010-VERSIONING-COMPATIBILITY.md`](EIS-010-VERSIONING-COMPATIBILITY.md) |
| EIS-011 | [`EIS-011-SECURITY.md`](EIS-011-SECURITY.md) |

## Regla

Una sola norma. **Connector SDK** = nombre comercial de estos contratos.  
LOCAL / ARP **consumen**; no inventan contratos paralelos.
