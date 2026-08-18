# ADR-EN1-EP1 — Cierre Operativo Las Terrazas

| Campo | Valor |
|-------|--------|
| ID | ADR-EN1-EP1 |
| Estado | **PROPOSED** → implementación **DEV** (no PROD sin GO) |
| Origen | Instalación real Las Terrazas VIP 507 (org 8) |
| Sistemas | EN1 (CODITO) + EPosOne / EP1 (LOCAL) |
| Relacionados | [ADR-036](ADR-036-CASH-OPERATION-MODES-CHAIN-OF-CUSTODY.md) (handover de **cajero/cajón**, distinto) · [ADR-003 Sync](ADR-003-EPOSONE-SYNC.md) · [ADR-009 Caja](ADR-009-EN1-CAJA-CENTRO-COBRO.md) · [ADR-021 Installation](ADR-021-EPOSONE-INSTALLATION-LIFECYCLE.md) |

## Distinción crítica con ADR-036

| ADR-036 `cash_operation_mode` | Este ADR `money_handoff_mode` |
|-------------------------------|--------------------------------|
| Custodio del **cajón** mid-turno (offer → accept) | Entrega de **efectivo cobrado** mesera → Caja Central |
| SIMPLE / CHAIN_OF_CUSTODY del drawer | SIMPLE / CHAIN_OF_CUSTODY del dinero de venta |
| `core_cash_custody_handover` | `eposone_money_handoff` |

**COBRADO ≠ RECIBIDO POR CAJA CENTRAL.**

## Decisiones (resumen)

- D1 Pedidos: org + autoría (`user_ref` / created_by); UI Mis / Todos → EP1. EN1 lista `mine`.
- D2 Custodia dinero: SIMPLE vs CHAIN_OF_CUSTODY (`money_handoff_mode`).
- D3 Confirmación recepción en EN1 (admin Caja Central) + auditoría inmutable.
- D4 Arqueo: pendiente de entregar ≠ faltante de Caja Central.
- D5 Catálogo: INACTIVE vía sync; DELETE físico solo sin movimientos.
- D6 Lifecycle: PROVISIONING → TEST → OPERATIONAL; transacciones TEST con `is_test` / `test_session_id`.
- D7 Cierre TEST: «Preparar para operación real»; no botón ordinario OPERATIONAL→TEST.

El texto operativo completo (criterios E2E, responsabilidades EN1/EP1) está en el hallazgo de instalación. Este archivo ancla el contrato en el repo.
