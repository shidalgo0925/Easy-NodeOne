# Gap Analysis EN1-POS V7 — Matriz de capacidades

| Campo | Valor |
|-------|--------|
| Estado | **Borrador Release 0** — revisado Prog1 19 jul 2026 |
| Método | Por **capacidad de negocio** (no por tablas) |
| DoD | [`EN1_POS_DEFINITION_OF_DONE_V1.md`](EN1_POS_DEFINITION_OF_DONE_V1.md) |
| Dominio | [`EN1_POS_DOMAIN_MODEL_V1.md`](EN1_POS_DOMAIN_MODEL_V1.md) |
| Evidencia | Dev EN1 `/opt/easynodeone/dev/app` · rama `develop` · 19 jul 2026 |
| **Prog1 (B-R0-05)** | **OK** — 0 filas en Completa; estados endurecidos abajo |

**Estados:** Completa · Parcial · Stub · Inexistente · Duplicada · Requiere rediseño

Ninguna fila puede marcarse **Completa** sin DoD 11/11. La mayoría del producto actual es **Parcial** o inferior.

---

## 1. Organización y dispositivos

| ID | Capacidad | Dominio | Estado | Evidencia breve | DoD faltante típico |
|----|-----------|---------|--------|-----------------|---------------------|
| C-ORG-01 | Crear/administrar empresa (datos legales, TZ, moneda) | Organización | Parcial | `saas_organization`, TZ Fase 1 | Legal FE, consecutivos, DoD reportes/E2E |
| C-ORG-02 | Sucursales | Organización | Parcial | BO `branches` | Permisos por sucursal, sync ownership formal |
| C-ORG-03 | Puntos de venta (POS) | Organización | Parcial | BO `pos-points` | Idem |
| C-ORG-04 | Cajas (registers) | Organización | Parcial | BO `registers` | Consecutivos, preferencias caja |
| C-ORG-05 | Provisioning dispositivo | Dispositivos | Parcial | codes + bootstrap Hito 1/2 | Diagnóstico remoto, storage, revoke E2E |
| C-ORG-06 | Bootstrap versionado (catálogo/políticas/cajeros) | Dispositivos | Parcial | `build_bootstrap_for_terminal`, `policies_version` | Pull incremental completo, tombstones |
| C-ORG-07 | Heartbeat / última conexión / versión APK | Dispositivos | Parcial | terminal fields | Panel soporte, alertas |
| C-ORG-08 | Licencia por caja (trial, grace, snapshot) | Licenciamiento | Parcial | `register_license_service` | Auditoría uso, suspensión UX, E2E offline |

---

## 2. Empleados y seguridad

| ID | Capacidad | Dominio | Estado | Evidencia breve | DoD faltante típico |
|----|-----------|---------|--------|-----------------|---------------------|
| C-HR-01 | CRUD cajeros + PIN hash | Empleados | Parcial | Hito 2.5 EN1 | Flutter login local E2E, auth supervisor |
| C-HR-02 | Bootstrap cajeros | Empleados | Parcial | `cashiers` en bootstrap | E2E APK + DoD Flutter |
| C-HR-03 | Atribución cajero en turno/pedido/pago | Empleados | Parcial | sync `cashier_contact_id` | Reportes por empleado |
| C-HR-04 | Roles operativos (mesero, supervisor, cocina) | Empleados | Inexistente | — | Todo |
| C-HR-05 | Permisos granulares por módulo/sucursal/POS | Seguridad | Parcial | RBAC plataforma genérico | Matriz EPosOne específica |
| C-HR-06 | Usuarios admin EN1 multi-org | Seguridad | Parcial | SaaS users | MFA, sesiones |

---

## 3. Catálogo

| ID | Capacidad | Dominio | Estado | Evidencia breve | DoD faltante típico |
|----|-----------|---------|--------|-----------------|---------------------|
| C-CAT-01 | CRUD productos (precio, SKU, imagen, activo) | Catálogo | Parcial | BO products + API | Import CSV, precio por sucursal |
| C-CAT-02 | Categoría comercial como entidad | Catálogo | **Requiere rediseño** | Campo texto `category` mayormente vacío | Entidad, sync, reportes |
| C-CAT-03 | Categoría fiscal ITBMS en producto | Fiscal/Catálogo | Parcial | `fiscal_category` + seed PA | Motor totales, recibo, FE |
| C-CAT-04 | Variantes / modificadores / combos | Catálogo | Inexistente | — | Todo |
| C-CAT-05 | Disponibilidad/precio por sucursal | Catálogo | Inexistente | — | Todo |
| C-CAT-06 | Import/export CSV/XLSX | Catálogo | Inexistente | — | Todo |

---

## 4. Comercial (políticas y totales)

| ID | Capacidad | Dominio | Estado | Evidencia breve | DoD faltante típico |
|----|-----------|---------|--------|-----------------|---------------------|
| C-COM-01 | Store políticas versionadas + lifecycle | Comercial | Parcial | `commercial_policy_service` | BO admin políticas, DoD Flutter N/A ok |
| C-COM-02 | Bootstrap/sync incremental políticas | Comercial | Parcial | `policies_version` | Tombstones, E2E |
| C-COM-03 | Motor de totales único | Comercial | **Stub** | `order_calculation_engine` `not_implemented` | Todo cálculo |
| C-COM-04 | Impuestos multi-tasa en línea | Fiscal | Parcial | `fiscal_categories` + tax en línea | Unificar con motor + FE |
| C-COM-05 | Propinas por política | Comercial | **Stub** | tip ad-hoc en pago; sin política versionada | T1 + política + motor + recibo |
| C-COM-06 | Promociones en motor comercial | Comercial | **Duplicada / Parcial** | `promotion_service` UI vs policy engine | Un solo camino DoD |
| C-COM-07 | Descuentos línea/global auditables | Comercial | Inexistente | — | Todo |

---

## 5. Pedido, venta, pago, recibo, FE

| ID | Capacidad | Dominio | Estado | Evidencia breve | DoD faltante típico |
|----|-----------|---------|--------|-----------------|---------------------|
| C-ORD-01 | Ciclo de vida pedido | Operación | Parcial | Order Domain v1 + BO | Estados restaurante completos |
| C-ORD-02 | Cobro multi-pago (mixto) | Pago | Parcial | OrderPaymentService 3C | E2E APK cola/reintento |
| C-ORD-03 | Catálogo métodos de pago | Pago | Parcial | `eposone_payment_method` | Política versionada unificada |
| C-ORD-04 | Reembolso total/parcial | Pago | Parcial | `PaymentService.refund` | BO UX, NC fiscal, inventario, E2E |
| C-ORD-05 | **Venta** como entidad financiera distinta | Venta | **Requiere rediseño** | Pedido absorbe rol financiero | Separar dominio + persistencia |
| C-ORD-06 | Recibo trazable (ítems, impuestos, pagos, cajero, device, políticas) | Recibo | **Inexistente** | Solo docs V6 + UI pedido (no entidad recibo) | Entidad + impresión + audit |
| C-ORD-07 | Emitir factura electrónica Panamá | Fiscal | **Stub** | Hooks `commerce/fiscal.py` / `emit_fiscal`; sin FE Panamá DoD | PAC, estados, contingencia, E2E |
| C-ORD-08 | Nota de crédito / débito | Fiscal | **Stub** | Hooks credit note en fiscal; sin flujo Panamá DoD | NC/ND completo |
| C-ORD-09 | Contingencia FE sin bloquear venta | Fiscal | Inexistente | — | Todo |

---

## 6. Caja y turnos

| ID | Capacidad | Dominio | Estado | Evidencia breve | DoD faltante típico |
|----|-----------|---------|--------|-----------------|---------------------|
| C-CASH-01 | Abrir turno | Caja | Parcial | sync `open_cash_shift` + BO | E2E desde APK |
| C-CASH-02 | Cerrar turno / arqueo | Caja | Parcial | `close` / `reconcile` · **ADR-009** | Reporte cierre completo + esperado solo efectivo + conciliación electrónica (B-R1-05b/c) |
| C-CASH-03 | Movimientos manuales caja | Caja | Parcial | `manual_cash_movement` | Motivos, evidencias, auth |
| C-CASH-04 | Diferencia esperado vs contado | Caja | Parcial | campos shift | Reporte + auth reapertura |

---

## 7. Inventario, clientes, restaurante (fuera del núcleo R1 pleno)

| ID | Capacidad | Dominio | Estado | Evidencia | Release |
|----|-----------|---------|--------|-----------|---------|
| C-INV-01 | Stock por sucursal / ajuste | Inventario | Parcial | `core_stock_*`, inventory BO | R1 básico / R2 |
| C-INV-02 | Kardex completo auditable | Inventario | **Requiere rediseño** | movimientos parciales ≠ libro auditable | R2 |
| C-INV-03 | Compras / proveedores / OC | Compras | Inexistente | — | R2 |
| C-CRM-01 | Clientes básicos | Clientes | Parcial | contacts | R1 |
| C-CRM-02 | Crédito / fidelización | Clientes | Inexistente | — | R2 |
| C-REST-01 | KDS estaciones | Restaurante | Parcial | kds BO | R3 |
| C-REST-02 | Delivery / menú digital | Restaurante | Parcial | delivery, digital_menu | R3 |

---

## 8. Sync, reportes, migración, observabilidad

| ID | Capacidad | Dominio | Estado | Evidencia | DoD faltante |
|----|-----------|---------|--------|-----------|--------------|
| C-SYNC-01 | Sync Up operaciones caja/pedido/pago | Sync | Parcial | `sync_handlers` | DLQ, replay UI, demostrabilidad |
| C-SYNC-02 | Pull incremental multi-entidad | Sync | Parcial | policies; resto incompleto | Catálogo/cajeros pull formal |
| C-SYNC-03 | Política de conflictos por entidad | Sync | Stub | Ownership borrador | Implementación + tests |
| C-REP-01 | Reportes operativos ventas/pagos/caja | Reportes | **Stub** | `analytics.html` mínimo + `commerce/reports` sin DoD | DoD completo |
| C-MIG-01 | Asistente Vincular Standalone→EN1 | Migración | Parcial | ADR-004 + link docs/código dominio | E2E producto cerrado |
| C-OBS-01 | Panel soporte dispositivos/errores sync | Observabilidad | **Inexistente** | Solo logs/SSH | Panel BO |

---

## 9. Lectura ejecutiva

| Pregunta | Respuesta |
|----------|-----------|
| ¿Hay Back Office navegable? | Sí (parcial). |
| ¿Hay cadena R1 cerrada con DoD? | **No.** |
| ¿Bloqueador conceptual #1? | **Venta ≠ Pedido** + **Recibo** + **Motor totales**. |
| ¿Bloqueador Panamá #2? | **FE + NC** dentro de R1 (no diferir a R2). |
| ¿Mayor riesgo de parche? | Promos UI vs policy engine; ITBMS en producto sin motor/recibo/FE. |
| ¿Siguiente código? | **Ninguno** hasta aprobar Release 0 (faltan Analista + Prog2). |

Detalle de trabajo: [`EN1_POS_BACKLOG_V7.md`](EN1_POS_BACKLOG_V7.md).

---

## 10. Revisión Prog1 (B-R0-05) — 19 jul 2026

| Chequeo | Resultado |
|---------|-----------|
| ¿Alguna capacidad en **Completa**? | **No** (0) |
| ¿Estados ambiguos (X/Y) eliminados? | Sí — tip, recibo, FE, NC, reportes, obs, kardex |
| ¿Evidencia re-chequeada en `develop`? | Sí — stub motor, order sin entidad Venta/Recibo, fiscal hooks ≠ FE DoD |
| ¿Riesgo de sobreestimar EN1? | Mitigado: C-HR-02 / C-ORD-02 siguen Parcial (falta Flutter E2E) |

**Firma Prog1 (EN1):** acepto esta matriz como base del backlog R1.  
**Pendiente:** Analista (producto) · Prog2 (impacto APK).
