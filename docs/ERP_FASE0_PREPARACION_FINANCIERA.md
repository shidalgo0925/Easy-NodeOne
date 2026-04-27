# ERP Easy NodeOne — Fase 0 (preparación)

## Tablas existentes reutilizadas
- `saas_organization`: separación multiempresa (`organization_id` en todo movimiento).
- `user`: terceros/usuarios (campo `partner_id` inicial en líneas contables).
- `invoices`, `invoice_lines`, `taxes` (módulos actuales de ventas/impuestos).
- `payment`, `cart`, `cart_item` (flujo actual de pagos/checkouts).

## Tablas nuevas (Fase 1)
- `account`: plan de cuentas.
- `journal`: diarios contables.
- `journal_entry`: cabecera de asiento.
- `journal_item`: líneas débito/crédito.

## Tablas a modificar
- Ninguna tabla legacy fue alterada estructuralmente en esta fase.
- Se añade integración modular (registro de blueprint) en `nodeone/core/features.py`.

## Riesgos detectados
- Convivencia entre contabilidad legacy (`/invoices`, `sales/accounting`) y el nuevo núcleo contable ERP.
- Entornos sin dependencias instaladas impiden ejecutar tests automáticos de integración.
- Si no se aplica migración de Fase 1 (`migrate_accounting_core_phase1.py`), rutas nuevas no tendrán tablas disponibles.

## Alcance protegido (qué no tocar)
- No borrar ni cambiar semántica de `DIPLOMADOS_IIUS`, pagos o rutas legacy existentes.
- No mover estados legacy de factura/pagos fuera de sus módulos actuales.
- No mezclar asientos ERP en tablas de factura legacy: se mantiene separación por módulo.
