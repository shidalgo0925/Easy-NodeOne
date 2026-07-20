# Backlog único EN1-POS V7

| Campo | Valor |
|-------|--------|
| Estado | **Activo** — Prog1 R0 OK · E2E 2.5 + Hito 2.6 añadidos 19 jul 2026 |
| Origen | [`EN1_POS_CAPABILITY_GAP_V7.md`](EN1_POS_CAPABILITY_GAP_V7.md) |
| DoD | [`EN1_POS_DEFINITION_OF_DONE_V1.md`](EN1_POS_DEFINITION_OF_DONE_V1.md) |
| E2E | [`EN1_EPOSONE_E2E_CHECKLIST_V1.md`](EN1_EPOSONE_E2E_CHECKLIST_V1.md) |
| Hito 2.6 | [`EN1_EPOSONE_HITO2_6_OBSERVABILITY.md`](EN1_EPOSONE_HITO2_6_OBSERVABILITY.md) |
| Regla | No Motor V6 algoritmos sin E2E 2.5 + 2.6 mínimo · No R2/R3 hasta cadena R1 Completa |

---

## Leyenda

| Campo | Valores |
|-------|---------|
| Prioridad | P0 (bloquea R1) · P1 · P2 |
| Release | 0 · 1 · 2 · 3 |
| Responsable | Prog1 · Prog2 · Analista · Ambos |
| Estado ítem | Todo · Doing · Done |

---

## Release 0 — Constitución (sin código de features)

| ID | Dominio | Capacidad / entregable | Depende | Resp. | Prioridad | Criterio de aceptación | Prueba E2E | Estado |
|----|---------|------------------------|---------|-------|-----------|------------------------|------------|--------|
| B-R0-01 | Producto | Constitución V1 aprobada | — | Analista | P0 | Firmas Analista+P1+P2 | N/A doc | P1 OK · falta A+P2 |
| B-R0-02 | Producto | Domain Model V1 aprobado | B-R0-01 | Analista | P0 | Pedido≠Venta≠Recibo≠FE explícito | N/A | P1 OK · falta A+P2 |
| B-R0-03 | Producto | Ownership Matrix V1 aprobada | B-R0-02 | Ambos | P0 | Conflicto por entidad R1 | N/A | P1 OK · falta A+P2 |
| B-R0-04 | Producto | DoD V1 aprobado | B-R0-01 | Analista | P0 | Checklist 11 puntos en uso | N/A | P1 OK · falta A+P2 |
| B-R0-05 | Producto | Gap capacidades V7 revisado | B-R0-02 | Prog1 | P0 | Matriz acordada sin “Completa” falsa | N/A | **Done Prog1** |
| B-R0-06 | Producto | Backlog priorizado R1 | B-R0-05 | Analista | P0 | Orden cadena operativa + FE | N/A | P1 respalda orden · falta A |
| B-R0-07 | Producto | Arquitectura V7 alineada | B-R0-02 | Ambos | P0 | Dual Mode + sync + FE | N/A | P1 OK · falta A+P2 |
| B-R0-08 | Producto | V6 contratos: aprobar o mapear a B-R1 | B-R0-02 | Analista | P0 | T1 propinas resuelto o diferido con dueño | N/A | **Pendiente Analista** |

**Estado R0 docs:** borradores · **Prog1 firmó 19 jul 2026** · faltan Analista + Prog2.

---

## Gates pre–Motor V6 (Analista)

| ID | Dominio | Capacidad | Depende | Resp. | Pri | Criterio | Estado |
|----|---------|-----------|---------|-------|-----|----------|--------|
| B-H25-E2E | Cajeros | Cerrar Hito 2.5 con E2E A–E | Código 2.5 | Ambos | **P0** | Checklist oficial ✅ + acta | Todo |
| B-H26-01 | Observabilidad | Diagnóstico APK (2.6-A) | — | Prog2 | **P0** | Pantalla campos mínimos | Todo |
| B-H26-02 | Observabilidad | Panel técnico EN1 (2.6-B) | — | Prog1 | **P0** | Devices/sync/licencia/errores sin SSH | Todo |
| B-H26-03 | Observabilidad | E2E error→visible→retry | B-H26-01/02 | Ambos | **P0** | 1 incidente simulado cerrado | Todo |

Detalle: [E2E](EN1_EPOSONE_E2E_CHECKLIST_V1.md) · [Hito 2.6](EN1_EPOSONE_HITO2_6_OBSERVABILITY.md).

**Orden:** B-H25-E2E → (solape OK) B-H26-* → freeze V6 → B-R1-08 motor.

---

## Release 1 — Cadena operativa comercial (incluye FE)

Orden de ejecución obligatorio (no paralelizar inventando features fuera de cadena):

```text
Núcleo org/dispositivo → Cajero/turno → Catálogo mínimo → Motor totales
→ Pedido → Venta → Pago → Recibo → FE/NC → Sync demostrable → Reporte básico
→ Licencia/obs mínima → Vincular (cierre)
```

| ID | Dominio | Capacidad | Gap ref | Depende | Resp. | Pri | Criterio de aceptación (resumen) | E2E |
|----|---------|-----------|---------|---------|-------|-----|----------------------------------|-----|
| B-R1-01 | Organización | Completar núcleo Empresa→Caja usable | C-ORG-01…04 | R0 | Prog1 | P0 | Alta cliente demo en BO sin SQL | Checklist org |

**B-R1-01 avance 19 jul (Prog1):** panel Empresa (legal/TZ/moneda), edit/desactivar Sucursal y Caja (API+BO), validación jerarquía Sucursal→POS→Caja. Aún **no DoD completo** (E2E checklist, consecutivos).

| ID | Dominio | Capacidad | Gap ref | Depende | Resp. | Pri | Criterio de aceptación (resumen) | E2E |
|----|---------|-----------|---------|---------|-------|-----|----------------------------------|-----|
| B-R1-02 | Dispositivos | Provisioning+bootstrap+revoke DoD | C-ORG-05…07 | B-R1-01 | Ambos | P0 | Device opera con versiones visibles | APK+EN1 |
| B-R1-03 | Licencia | Plan/trial/grace/heartbeat DoD mínimo | C-ORG-08 | B-R1-02 | Ambos | P1 | Caja bloqueada/reactivada auditable | Offline grace |
| B-R1-04 | Empleados | Cajero PIN + atribución DoD | C-HR-01…03 | B-R1-02 | Ambos | P0 | Venta atribuida a cajero | Login+turno+venta |
| B-R1-05 | Caja | Abrir/cerrar turno + diferencia | C-CASH-01…04 | B-R1-04 | Ambos | P0 | Cierre explica efectivo | Turno completo |
| B-R1-06 | Catálogo | Producto + categoría comercial entidad mínima | C-CAT-01…02 | B-R1-01 | Prog1 | P0 | Filtro categorías real; sync down | Catálogo APK |
| B-R1-07 | Fiscal catálogo | ITBMS en producto → política | C-CAT-03 | B-R1-06 | Prog1 | P0 | Alcohol 10% coherente | Línea impuesto |
| B-R1-08 | Comercial | Motor totales único (EN1+Dart) | C-COM-03…05 | B-R0-08, B-R1-07 | Ambos | P0 | Mismo desglose en 4 superficies | Paridad totales |
| B-R1-09 | Comercial | Unificar promos → política (eliminar duplicado) | C-COM-06 | B-R1-08 | Prog1 | P1 | Un solo camino | Promo aplicada |
| B-R1-10 | Operación | Pedido ciclo R1 | C-ORD-01 | B-R1-05,08 | Ambos | P0 | Estados R1 + sync | Pedido E2E |
| B-R1-11 | Venta | Entidad Venta separada del Pedido | C-ORD-05 | B-R1-10 | Ambos | P0 | Venta inmutable post-cierre | Pedido→Venta |
| B-R1-12 | Pago | Mixto + reembolso parcial DoD | C-ORD-02…04 | B-R1-11 | Ambos | P0 | Saldo, tip, refund | Cobro+refund |
| B-R1-13 | Recibo | Recibo trazable + reimpresión | C-ORD-06 | B-R1-12 | Ambos | P0 | Incluye políticas/versiones/cajero/device | Print/reprint |
| B-R1-14 | Fiscal | FE Panamá + contingencia | C-ORD-07,09 | B-R1-13 | Ambos | P0 | Venta cierra; FE estado auditable | Emisión/consulta |
| B-R1-15 | Fiscal | Nota de crédito ligada a venta/FE | C-ORD-08 | B-R1-14 | Ambos | P0 | NC por refund | Refund→NC |
| B-R1-16 | Sync | Demostrar recepción (device, tiempo, resultado) | C-SYNC-01…03 | B-R1-12 · B-H26-02 | Ambos | P0 | Panel o API soporte mínimo | Replay 1 evento |
| B-R1-17 | Reportes | Operativo: ventas, impuestos, pagos, caja | C-REP-01 | B-R1-14 | Prog1 | P0 | Cuadra con venta/FE del día | Reporte vs detalle |
| B-R1-18 | Migración | Vincular Standalone→Integrado cerrado | C-MIG-01 | B-R1-16 | Ambos | P1 | Informe migración + SoT EN1 | Vincular E2E |
| B-R1-19 | Observabilidad | Errores sync + versiones device | C-OBS-01 | **= B-H26-02** | Prog1 | **P0** | Cubierto por Hito 2.6 | Ver 2.6 |

---

## Release 2 — Control del negocio

| ID | Dominio | Capacidad | Gap ref | Pri |
|----|---------|-----------|---------|-----|
| B-R2-01 | Inventario | Kardex + existencias avanzadas | C-INV-01…02 | P0 R2 |
| B-R2-02 | Compras | Proveedores + OC + recepción | C-INV-03 | P0 R2 |
| B-R2-03 | Costos | Margen / rentabilidad | — | P1 R2 |
| B-R2-04 | Clientes | Crédito + estado de cuenta | C-CRM-02 | P0 R2 |
| B-R2-05 | Clientes | Fidelización | C-CRM-02 | P1 R2 |
| B-R2-06 | Reportes | Gerenciales / exportación | — | P1 R2 |
| B-R2-07 | Catálogo | Variantes, modificadores, import masivo | C-CAT-04…06 | P1 R2 |

---

## Release 3 — Restaurante y ecosistema

| ID | Dominio | Capacidad | Gap ref | Pri |
|----|---------|-----------|---------|-----|
| B-R3-01 | Restaurante | Mesas/áreas + flujo | — | P0 R3 |
| B-R3-02 | Restaurante | KDS DoD | C-REST-01 | P0 R3 |
| B-R3-03 | Canales | Delivery / QR / menú | C-REST-02 | P1 R3 |
| B-R3-04 | Plataforma | API pública OpenAPI + webhooks | — | P0 R3 |
| B-R3-05 | Plataforma | Integraciones / marketplace | — | P2 R3 |

---

## WIP Prog2 paralelo (no abre R2)

**Prioridad ahora:**

1. Ejecutar [`EN1_EPOSONE_E2E_CHECKLIST_V1.md`](EN1_EPOSONE_E2E_CHECKLIST_V1.md) (cierra 2.5)
2. Pantalla diagnóstico Hito 2.6-A
3. Firmar Ownership / Arquitectura R0

También permitido: Hito 4 login Keystore / cola tip-reference — sin dominio nuevo.

Cualquier feature comercial V6 → rechazo hasta gates E2E+2.6 + freeze contratos.
