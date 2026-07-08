# Etapa 6 — Dominio Comercial (EPosOne / POS)

**Prioridad actual — V3 Etapa 6.** Cerrar el modelo de negocio comercial **antes** de implementar inventario, reportes, reembolsos, hardware, FE Panamá o piloto.

| Campo | Valor |
|-------|--------|
| Versión doc | **1.0** (borrador estructural — decisiones pendientes de aprobación) |
| Estado | **En definición** — sin código nuevo hasta cierre |
| Alcance edición | Solo Dev EN1 (`develop`) |
| Master plan | [`EN1_PLATFORM_MASTER_PLAN.md`](EN1_PLATFORM_MASTER_PLAN.md) v3.1 |
| Modelo maestro Core | [`EN1_PLATFORM_ETAPA10_MODELO_MAESTRO.md`](EN1_PLATFORM_ETAPA10_MODELO_MAESTRO.md) |
| Scaffold técnico (referencia) | `nodeone/core/commerce/`, EPosOne Etapas EN1 12–17 |

---

## Objetivo

Definir **de forma explícita y aprobada** el dominio comercial de EPosOne: entidades, roles, estados, flujos, eventos y reglas de sincronización.

**No es desarrollo.** Es modelado y decisiones de negocio.

### Lección de EN1

No construir funcionalidades antes de cerrar el dominio. EN1, IIUS, Relatic y EPayRoll demostraron que implementar primero y definir después obliga a rehacer inventario, reportes, caja y facturación.

### Relación con otras etapas

| Etapa | Rol |
|-------|-----|
| **V3 Etapa 3** (EN1 Etapa 10) | Maestro transversal: Contact, catálogo, org_unit, direcciones |
| **V3 Etapa 6** (este doc) | Dominio comercial POS: pedido, caja, pagos, inventario (reglas), facturación |
| **V3 Etapa 7** | Construcción funcional sobre dominio congelado |
| **Scaffold EN1 12–17** | Borrador técnico de validación — **no** contrato aprobado |

### Principio rector (propuesto)

> **El centro del sistema es el Pedido, no la Factura.**

La factura es un **documento derivado** del pedido (o de un conjunto de pedidos), emitido según reglas fiscales y de negocio acordadas en 6.8.

---

## Regla de congelamiento (vigente desde aprobación V3.1)

Hasta que este documento cierre con **criterio de cierre Etapa 6** cumplido:

| Permitido | Prohibido |
|-----------|-----------|
| Editar este documento y diagramas | Nuevas features POS (inventario, reportes, reembolsos) |
| Mantener scaffold existente (bugs críticos, tests) | Ampliar contratos `commerce/` con suposiciones no documentadas |
| Workshops de decisión por bloque 6.1–6.9 | FE Panamá, hardware, piloto comercial |

---

## Estructura de la etapa (6.1 – 6.9)

Cada sub-etapa cierra con: **decisión explícita**, **entidades/relaciones**, **estados y transiciones**, **eventos de dominio**, **preguntas abiertas = 0** (o diferidas con justificación).

---

### 6.1 — Organización Comercial

**Objetivo:** jerarquía operativa única bajo el tenant.

#### Entidades a definir

| Entidad | Pregunta clave | Notas / deuda actual |
|---------|----------------|----------------------|
| **Empresa** | ¿Es `SaasOrganization` o sub-entidad? | Hoy: tenant = org |
| **Sucursal** | ¿Obligatoria para todo POS? | Etapa 10: `org_unit` tipo `branch` |
| **Área** | ¿Salón, cocina, depósito, mostrador? | No modelado |
| **POS** | ¿Punto lógico de venta vs terminal física? | UI placeholder `branches` |
| **Terminal** | ¿Dispositivo, sesión, o ambos? | `core_pos_terminal` scaffold |
| **Caja** | ¿Caja física, lógica, o turno? | Confusión caja vs turno |
| **Turno** | ¿Por cajero, por terminal, por sucursal? | `core_cash_shift` scaffold |

#### Decisiones pendientes

- [ ] ¿Una sucursal puede tener múltiples cajas abiertas simultáneamente?
- [ ] ¿Terminal sin turno puede cobrar?
- [ ] ¿POS móvil (mesero) vs POS fijo (caja) — misma entidad o distinta?
- [ ] ¿Multi-sucursal: catálogo e inventario por sucursal o centralizado?
- [ ] Mapa definitivo `org_unit` tipos: `company` \| `branch` \| `area` \| `pos` \| `terminal` \| `warehouse`

#### Criterio de cierre 6.1

Diagrama jerárquico aprobado + glosario de términos + reglas de cardinalidad (1:N, N:M).

---

### 6.2 — Personas y roles comerciales

**Objetivo:** separar **identidad de acceso** (`User`) de **rol operativo en el POS** (`Contact` + rol de turno).

#### Roles a definir

| Rol | Pregunta | ¿Puede…? |
|-----|----------|----------|
| **Cajero** | ¿Quién abre turno y cobra? | Pendiente |
| **Vendedor** | ¿Distinto del cajero en retail? | Pendiente |
| **Mesero** | ¿Toma pedido sin cobrar? | Pendiente |
| **Supervisor** | ¿Anulaciones, descuentos, arqueo? | Pendiente |
| **Gerente** | ¿Reportes, cierre de día, config? | Pendiente |

#### Decisiones pendientes

- [ ] ¿Un `User` puede ser cajero y mesero el mismo día?
- [ ] ¿Vendedor vs cajero: misma persona, dos roles, o dos personas obligatorias?
- [ ] ¿Mesero “posee” el pedido hasta transferencia a caja?
- [ ] ¿Supervisor requiere autorización por PIN, rol RBAC, o ambos?
- [ ] Vínculo `User` ↔ `Contact` ↔ rol operativo del turno

#### Criterio de cierre 6.2

Matriz rol × acción permitida + reglas de autorización y auditoría.

---

### 6.3 — Documento maestro

**Objetivo:** fijar el **agregado raíz** del dominio comercial.

#### Opciones (decisión requerida)

| Opción | Descripción | Implicaciones |
|--------|-------------|---------------|
| **A — Pedido** (recomendación proyecto) | Todo flujo comienza y termina en pedido | Factura, entrega, KDS cuelgan del pedido |
| B — Factura | Venta = documento fiscal | Pedido como borrador previo |
| C — Híbrido | Pedido operativo + factura obligatoria inmediata | Complejidad retail vs restaurante |

#### Decisiones pendientes

- [ ] Confirmar **Opción A** (Pedido como centro) o documentar alternativa
- [ ] ¿Pedido único vs pedido padre + sub-pedidos (mesas, comandas)?
- [ ] ¿Estados del pedido vs estados de línea independientes?
- [ ] ¿Pedido anónimo (mostrador) vs pedido con `Contact` obligatorio?
- [ ] Relación pedido ↔ cotización ↔ factura ↔ nota de crédito

#### Criterio de cierre 6.3

Agregado raíz declarado + diagrama de documentos derivados + máquina de estados del pedido v1.

---

### 6.4 — Flujos comerciales (escenarios)

**Objetivo:** validar el modelo contra verticales reales — **casos de prueba del dominio**, no features.

#### Escenarios obligatorios

| Escenario | Preguntas a resolver |
|-----------|---------------------|
| **Restaurante** | Mesa, comanda, cocina (KDS), cobro en mesa o caja, propina |
| **Retail** | Mostrador, escaneo, devolución en tienda, cambio |
| **Ferretería** | Precio por cantidad, crédito cliente, despacho desde bodega |
| **Mayorista** | Pedido grande, factura posterior, múltiples entregas parciales |
| **Delivery** | Pedido remoto, pago anticipado vs contra entrega, repartidor |

#### Flujos transversales

- [ ] Transferencia de pedido (mesero → caja, sucursal → sucursal)
- [ ] Pedido suspendido / retomado
- [ ] División de cuenta (split bill)
- [ ] Unión de mesas / pedidos
- [ ] Cancelación vs anulación vs reembolso — definiciones distintas

#### Criterio de cierre 6.4

Un diagrama de secuencia por escenario + tabla “evento disparado en cada paso”.

---

### 6.5 — Inventario (solo modelado)

**Objetivo:** reglas de stock **sin implementar** tablas ni UI.

#### Preguntas

| Momento | Opciones | Decisión |
|---------|----------|----------|
| **Reserva** | Al confirmar pedido / al pagar / al despachar | Pendiente |
| **Descuento** | Al pagar / al entregar / al facturar | Pendiente |
| **Devolución** | Reingreso automático / inspección / merma | Pendiente |
| **Negativo** | ¿Permitido? ¿Solo con permiso supervisor? | Pendiente |
| **Multi-sucursal** | Stock por sucursal, transferencias entre bodegas | Pendiente |
| **Kit / combo** | Descuento por componentes | Pendiente |

#### Relación con catálogo

- Inventario consume `core_product` (Etapa 10) — no catálogo paralelo en EPosOne.
- Reglas de precio (lista, promoción) — ¿dominio comercial o app extension?

#### Criterio de cierre 6.5

Tabla momento × acción × evento + excepciones por vertical (restaurante sin stock estricto vs retail).

---

### 6.6 — Caja (solo modelado)

**Objetivo:** ciclo de vida del dinero en efectivo y medios en caja.

#### Ciclo

```text
Apertura → Cobros → Reembolsos / retiros → Arqueo → Cierre
```

#### Decisiones pendientes

- [ ] ¿Apertura con fondo fijo obligatorio?
- [ ] ¿Cobro sin turno abierto — permitido o bloqueado?
- [ ] ¿Reembolso total vs parcial — impacto en turno y pedido?
- [ ] ¿Arqueo ciego vs arqueo con detalle esperado?
- [ ] ¿Un cajero, un turno, una terminal — regla de unicidad?
- [ ] ¿Ventas a crédito pasan por caja o solo por cuenta por cobrar?

#### Criterio de cierre 6.6

Máquina de estados del turno + reglas de arqueo + eventos `commerce.cash_shift.*`.

---

### 6.7 — Pagos (solo modelado)

**Objetivo:** medios de pago y combinaciones.

#### Medios

| Medio | Preguntas |
|-------|-----------|
| Efectivo | Cambio, redondeo, multi-moneda |
| Tarjeta | Integración terminal vs registro manual |
| Mixto | Orden de aplicación, un pago o varios por pedido |
| Yappy / transferencia | Confirmación manual vs automática |
| Crédito | Límite, cuenta corriente, vencimiento |

#### Decisiones pendientes

- [ ] ¿Un pedido, N pagos — siempre permitido?
- [ ] ¿Pago parcial deja pedido en estado intermedio?
- [ ] ¿Propina — línea de pedido, pago aparte, o ajuste de caja?
- [ ] ¿Pagos offline se encolan y reconcilian al sync?

#### Criterio de cierre 6.7

Catálogo de `payment_method` + estados de pago + reglas mixtas + eventos `commerce.payment.*`.

---

### 6.8 — Facturación

**Objetivo:** cuándo y cómo nace el documento fiscal sin convertirlo en el centro del sistema.

#### Decisiones pendientes

- [ ] ¿Factura al cobrar, al entregar, o bajo demanda?
- [ ] ¿Un pedido = una factura siempre?
- [ ] ¿Factura consolidada (varios pedidos del día)?
- [ ] **Sin Internet:** cola local, numeración contingencia, reenvío FE
- [ ] **FE Panamá:** punto de emisión por sucursal, PAC, anulación
- [ ] Nota de crédito / débito — trigger y relación con pedido original
- [ ] Integración con módulo `efactura` existente vs emisión unificada Core

#### Criterio de cierre 6.8

Diagrama pedido → factura + reglas offline + handoff a Etapa V3 10 (FE Panamá implementación).

---

### 6.9 — Sincronización y offline

**Objetivo:** qué se sincroniza, en qué orden, y cómo se resuelven conflictos.

#### Temas

| Tema | Preguntas |
|------|-----------|
| **Eventos** | ¿Qué publica el cliente offline vs el servidor? |
| **Prioridad** | Pedido > pago > inventario > reportes |
| **Conflictos** | Última escritura, versión, o regla de negocio |
| **Idempotencia** | Claves por operación (ya scaffold `platform_sync_operation`) |
| **Alcance offline** | ¿Solo cobro o también catálogo, stock, turnos? |
| **Multi-terminal** | Dos terminales offline misma sucursal |

#### Relación con scaffold

- Bus: `platform_domain_event` (EN1 Etapa 8)
- Sync: `nodeone/core/sync/` (EN1 Etapa 13)
- Handlers EPosOne: `eposone/sync_handlers.py`

**Regla:** la implementación (V3 Etapa 8) sigue al modelo aprobado aquí.

#### Criterio de cierre 6.9

Lista priorizada de entidades offline + matriz de conflictos + catálogo eventos `commerce.*` y `eposone.*` v2.

---

## Mapa de código scaffold → dominio (referencia)

El código en dev **implementa suposiciones no aprobadas**. Tras cierre Etapa 6, alinear o refactorizar en V3 Etapa 7.

| Área scaffold | Ubicación | Revisar en |
|---------------|-----------|------------|
| Contratos comerciales | `nodeone/core/commerce/` | 6.3, 6.6, 6.7 |
| Pedidos / pagos | `models/commercial_core.py` | 6.3, 6.7 |
| Turnos / terminales | `core_cash_shift`, `core_pos_terminal` | 6.1, 6.6 |
| KDS | `eposone_kds_*` | 6.4 (restaurante) |
| Delivery | `eposone_delivery` | 6.4 (delivery) |
| Menú digital | `eposone_digital_menu_*` | 6.4 |
| Sync handlers | `eposone/sync_handlers.py` | 6.9 |

---

## Criterio de cierre — Etapa 6 (dominio comercial)

| # | Criterio | Estado |
|---|----------|--------|
| 1 | 6.1 Organización comercial — diagrama y glosario aprobados | Pendiente |
| 2 | 6.2 Personas y roles — matriz rol × acción | Pendiente |
| 3 | 6.3 Documento maestro — **Pedido** confirmado como agregado raíz | Pendiente |
| 4 | 6.4 Flujos — 5 escenarios con secuencias y eventos | Pendiente |
| 5 | 6.5 Inventario — reglas momento × acción (sin código) | Pendiente |
| 6 | 6.6 Caja — ciclo turno completo modelado | Pendiente |
| 7 | 6.7 Pagos — medios y reglas mixtas | Pendiente |
| 8 | 6.8 Facturación — nacimiento documento + offline | Pendiente |
| 9 | 6.9 Sincronización — prioridades y conflictos | Pendiente |
| 10 | Master Plan V3.1 actualizado y referenciado | Hecho |
| 11 | Aprobación explícita responsable del proyecto | Pendiente |

**Siguiente fase tras cierre:** **V3 Etapa 7 — Construcción del dominio** (inventario, caja, pedidos, reportes, reembolsos).

---

## Orden de trabajo recomendado

```text
6.3 Documento maestro (Pedido)
    → 6.1 Organización
    → 6.2 Personas
    → 6.4 Flujos (validar con escenarios)
    → 6.7 Pagos → 6.6 Caja → 6.5 Inventario
    → 6.8 Facturación → 6.9 Sincronización
    → Revisión integral → Aprobación → Etapa 7
```

6.3 primero porque condiciona todo lo demás.

---

## Workshops sugeridos (sin código)

| Sesión | Bloques | Participantes sugeridos |
|--------|---------|-------------------------|
| 1 | 6.3 + 6.1 | Producto + arquitectura |
| 2 | 6.2 + 6.4 restaurante/retail | Operaciones + producto |
| 3 | 6.5 + 6.6 + 6.7 | Finanzas + operaciones |
| 4 | 6.8 + 6.9 | Fiscal + arquitectura |
| 5 | Cierre y checklist | Responsable proyecto |

---

*Etapa 6 dominio comercial — 2026-07-08. Cambios requieren actualizar este doc y acuerdo del responsable. Sin GO explícito: no implementación funcional nueva.*
