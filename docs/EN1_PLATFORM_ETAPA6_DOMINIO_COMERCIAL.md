# Etapa 6 — Dominio Comercial (EPosOne / POS)

**Prioridad actual — V3 Etapa 6.** Cerrar el modelo de negocio comercial **antes** de implementar inventario, reportes, reembolsos, hardware, FE Panamá o piloto.

| Campo | Valor |
|-------|--------|
| Versión doc | **1.2** |
| Estado | **Modelado v1.2 — pendiente aprobación responsable** (sin código hasta cierre) |
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

### Principio rector (decisión 6.3)

> **El centro del sistema es el Pedido (`CommercialOrder`), no la Factura.**

La factura es un **documento derivado** del pedido, emitido según reglas fiscales (6.8). Cotización, KDS, entrega, pagos y movimientos de caja **cuelgan del pedido**.

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

**Estado:** borrador decisión v1 — pendiente aprobación.

#### Decisión v1 — jerarquía

```text
SaasOrganization (Empresa / tenant)
    └── OrgUnit [branch]           Sucursal — obligatoria si hay POS físico
            └── OrgUnit [area]     Área operativa (salón, cocina, bodega, mostrador)
            └── OrgUnit [pos]      Punto de venta lógico (mostrador 1, barra, delivery hub)
            └── OrgUnit [register] Caja lógica (cajón / cuenta de efectivo)
            └── OrgUnit [warehouse] Bodega / depósito (inventario — 6.5)
    └── PosTerminal                Dispositivo o sesión de captura (tablet, PC, handheld mesero)
    └── CashShift                  Turno de caja (apertura → cierre)
```

| Entidad | Definición v1 | Tabla / contrato |
|---------|---------------|------------------|
| **Empresa** | `SaasOrganization` — un tenant = una empresa fiscal operativa | `saas_organization` |
| **Sucursal** | Local con dirección, FE y stock propios (si aplica) | `org_unit.type = branch` |
| **Área** | Zona dentro de la sucursal (no vende sola; enruta a KDS/bodega) | `org_unit.type = area` |
| **POS** | Punto lógico donde se originan pedidos (config, lista de precios, impresora) | `org_unit.type = pos` |
| **Caja (register)** | Cuenta lógica de efectivo; N por sucursal | `org_unit.type = register` |
| **Terminal** | Dispositivo que ejecuta la app; 1..N por POS o sucursal | `core_pos_terminal` |
| **Turno** | Sesión de operación de un cajero sobre una caja | `core_cash_shift` |

#### Reglas de cardinalidad v1

| Regla | Decisión |
|-------|----------|
| ¿Multi-sucursal? | Sí — catálogo maestro a nivel empresa; precios/stock configurables por sucursal (6.5) |
| ¿Varias cajas abiertas en una sucursal? | **Sí** — una por `register`; cada una con su turno |
| ¿Un turno abierto por caja? | **Sí** — máximo un `CashShift` en `open` por `register_id` |
| ¿Terminal sin turno puede cobrar efectivo? | **No** — cobro efectivo requiere turno abierto en la caja vinculada |
| ¿Terminal sin turno puede tomar pedido? | **Sí** — terminal handheld (mesero) en modo `order_only` |
| ¿POS móvil vs fijo? | Misma entidad `PosTerminal`; perfil `fixed` \| `handheld` |
| ¿Pedido obliga sucursal? | **Sí** — `branch_id` requerido en todo pedido POS |

#### Glosario

| Término | Significado |
|---------|-------------|
| **Sucursal** | Local físico o punto fiscal |
| **POS** | Configuración lógica de venta (no el dispositivo) |
| **Terminal** | Dispositivo o sesión que corre EPosOne |
| **Caja** | Registro lógico de dinero (no el cajón físico, aunque se mapea 1:1) |
| **Turno** | Intervalo en que un cajero opera una caja |

#### Preguntas diferidas (no bloquean 6.3)

- [ ] ¿`warehouse` es `org_unit` hermano de `branch` o hijo? → decidir en **6.5 Inventario**
- [ ] ¿Terminal puede cambiar de caja mid-shift? → **No** en v1

#### Criterio de cierre 6.1

| Ítem | Estado |
|------|--------|
| Diagrama jerárquico | Hecho (borrador v1) |
| Glosario | Hecho |
| Reglas cardinalidad | Hecho (borrador v1) |
| Aprobación responsable | Pendiente |

---

### 6.2 — Personas y roles comerciales

**Objetivo:** separar **identidad de acceso** (`User`) de **rol operativo en el POS** (asignación de turno/sesión).

**Estado:** borrador decisión v1 — pendiente aprobación.

#### Decisión v1 — dos capas

| Capa | Entidad | Uso |
|------|---------|-----|
| **Acceso plataforma** | `User` + RBAC | Permisos de app, menús, configuración |
| **Operación POS** | `User` + `operational_role` en sesión/turno | Acciones en piso y caja |

`Contact` = cliente del pedido (opcional en mostrador). **No** confundir con rol operativo.

Vínculo futuro: `User.linked_contact_id` cuando el empleado también es tercero fiscal (Etapa 10).

#### Roles operativos v1

| Rol | Descripción | Contexto típico |
|-----|-------------|-----------------|
| **Mesero** | Toma y modifica pedidos; no cobra ni abre turno | Restaurante, handheld |
| **Vendedor** | Crea pedidos y cobra (sin obligación de turno de caja en retail simple) | Retail, ferretería |
| **Cajero** | Opera turno de caja; cobra, arquea, cierra | Caja fija |
| **Supervisor** | Autoriza excepciones (descuento, anulación, reembolso) | Todos |
| **Gerente** | Config, reportes, cierre de día, override supervisor | Back office |

Un `User` **puede** tener varios roles operativos; al iniciar sesión en terminal elige rol (o se infiere por tipo de terminal).

#### Matriz rol × acción v1

| Acción | Mesero | Vendedor | Cajero | Supervisor | Gerente |
|--------|:------:|:--------:|:------:|:----------:|:-------:|
| Crear pedido `draft` | ✓ | ✓ | ✓ | ✓ | ✓ |
| Editar pedido `draft` | ✓ | ✓ | ✓ | ✓ | ✓ |
| Confirmar / enviar a cocina | ✓ | ✓ | ✓ | ✓ | ✓ |
| Aplicar descuento | — | límite % | límite % | ✓ | ✓ |
| Capturar pago | — | ✓ | ✓ | ✓ | ✓ |
| Cobro efectivo | — | ✓* | ✓ | ✓ | ✓ |
| Abrir / cerrar turno | — | — | ✓ | ✓ | ✓ |
| Transferir pedido a otra caja | — | — | ✓ | ✓ | ✓ |
| Anular pedido (`cancelled`) | — | — | PIN | ✓ | ✓ |
| Reembolso (`refunded`) | — | — | PIN | ✓ | ✓ |
| Ver reportes de caja | — | — | propio turno | sucursal | todo |

\* Vendedor en retail puede cobrar efectivo **sin** turno formal si la org tiene `retail_simple_mode=true`; en restaurante el cobro es siempre en caja (mesero no cobra).

#### Reglas de autorización v1

| Situación | Regla |
|-----------|-------|
| Descuento sobre límite | `Supervisor` autoriza con PIN o credencial |
| Anulación post-confirmación | Supervisor + motivo obligatorio + auditoría |
| Mesero cobra | **Prohibido** en restaurante — transferir a caja |
| Vendedor = Cajero | Misma persona puede alternar roles; turno de caja sigue siendo explícito |

#### Eventos de auditoría

Toda acción de supervisor (override) publica `commerce.authorization.applied` con `user_id`, `action`, `order_id`, `reason`.

#### Criterio de cierre 6.2

| Ítem | Estado |
|------|--------|
| Matriz rol × acción | Hecho (borrador v1) |
| Reglas mesero vs cajero vs vendedor | Hecho |
| Aprobación responsable | Pendiente |

---

### 6.3 — Documento maestro

**Objetivo:** fijar el **agregado raíz** del dominio comercial.

**Estado:** **cerrado v1** (decisiones documentadas — pendiente firma responsable).

#### Decisión principal

| Opción | Estado |
|--------|--------|
| **A — Pedido como agregado raíz** | **Adoptada** |
| B — Factura como centro | Rechazada |
| C — Híbrido factura obligatoria inmediata | Rechazada |

#### Modelo de documentos

```text
Cotización (Quotation)     — opcional, pre-venta B2B
        │
        ▼ convertir (1:1 o 1:N líneas)
Pedido (CommercialOrder)  — AGREGADO RAÍZ ★
        │
        ├── Líneas (OrderLine) — productos, cantidades, precios
        ├── Pagos (Payment) — N pagos por pedido
        ├── Entrega (Delivery) — 0..1 por pedido (6.4)
        ├── Ticket KDS — derivado al confirmar (restaurante)
        ├── Factura (Invoice) — 0..N documentos fiscales derivados (6.8)
        └── Nota de crédito — revierte factura; referencia pedido origen
```

| Documento | ¿Centro? | Relación con pedido |
|-----------|----------|---------------------|
| **Pedido** | **Sí** | Raíz |
| **Cotización** | No | Se convierte en pedido; no se factura directamente |
| **Factura** | No | Se emite **desde** pedido(s) cobrado(s) o entregado(s) |
| **Nota de crédito** | No | Referencia factura + pedido |
| **Ticket KDS** | No | Vista operativa de líneas a preparar |

#### Estructura del pedido v1

| Campo conceptual | Regla |
|------------------|-------|
| `parent_order_id` | Opcional — cuenta padre (mesa) con sub-pedidos (comandas por persona o ronda) |
| `contact_id` | Opcional en mostrador; obligatorio en crédito, delivery y factura nominativa |
| `branch_id` | Obligatorio |
| `pos_id` | Obligatorio — punto lógico de origen |
| `terminal_id` | Obligatorio — dispositivo que creó el pedido |
| `cashier_user_id` | Quien cobró (puede diferir de quien creó) |
| `operational_status` | Ciclo operativo (cocina, entrega) |
| `payment_status` | `unpaid` \| `partial` \| `paid` \| `overpaid` — **eje independiente** |
| `fiscal_status` | `not_required` \| `pending` \| `invoiced` \| `cancelled` — **eje independiente** |

**Regla:** operación, pago y fiscal **no** se mezclan en un solo campo `status` (el scaffold actual `status` único se refactoriza en Etapa 7).

#### Estados operativos del pedido v1

```text
draft ──► confirmed ──► in_progress ──► ready ──► delivered
  │            │              │             │
  └────────────┴──────────────┴─────────────┴──► cancelled
  │
  └── (desde delivered + pago revertido) ──► refunded
```

| Estado | Significado | Editable |
|--------|-------------|----------|
| `draft` | Carrito / comanda abierta | Sí — líneas y cantidades |
| `confirmed` | Comprometido — enviado a cocina o listo para cobrar | Solo con supervisor |
| `in_progress` | En preparación (KDS) | No líneas; sí notas |
| `ready` | Listo para entregar o cobrar | No |
| `delivered` | Entregado al cliente / cerrado operativamente | No |
| `cancelled` | Anulado antes de completar — sin efecto fiscal | Terminal |
| `refunded` | Devolución post-venta | Terminal |

Transiciones válidas = mismas que scaffold `ORDER_STATUS_TRANSITIONS` (alineado). El scaffold **no** modela aún `payment_status` ni `fiscal_status` separados.

#### Estados de línea v1 (independientes del pedido)

Cada `OrderLine` tiene `line_status`:

| `line_status` | Uso |
|---------------|-----|
| `pending` | Esperando preparación |
| `in_progress` | En cocina |
| `ready` | Lista |
| `served` | Entregada al cliente |
| `cancelled` | Línea anulada |

**Regla:** en restaurante el KDS opera sobre **líneas**; el pedido pasa a `ready` cuando todas las líneas activas están `ready` o `served`.

#### Pedido anónimo vs identificado

| Modo | `contact_id` | Factura nominativa |
|------|--------------|-------------------|
| Mostrador / consumo rápido | Opcional | Consumidor final |
| Retail con programa fidelidad | Recomendado | Opcional |
| Crédito / mayorista / delivery | **Obligatorio** | Según RUC |

#### Definiciones operativas (glosario 6.3)

| Término | Definición |
|---------|------------|
| **Cancelar** | Anular pedido **antes** de completar venta — sin movimiento de caja de reembolso |
| **Reembolsar** | Devolver dinero **después** de cobro — pedido pasa a `refunded` |
| **Anular factura** | Acto fiscal sobre documento emitido — no sustituye reembolso de caja |

#### Eventos de dominio v1 (pedido)

| Evento | Cuándo |
|--------|--------|
| `commerce.order.created` | Pedido `draft` creado |
| `commerce.order.confirmed` | Pasa a `confirmed` |
| `commerce.order.status_changed` | Cualquier cambio operativo |
| `commerce.order.payment_status_changed` | Cambio en eje de pago |
| `commerce.order.cancelled` | `cancelled` |
| `commerce.order.refunded` | `refunded` |
| `commerce.order.line_status_changed` | Cambio en línea (KDS) |

#### Alineación con scaffold EN1

| Scaffold actual | Acción Etapa 7 |
|-----------------|----------------|
| `status` único en `core_commercial_order` | Dividir en `operational_status` + `payment_status` + `fiscal_status` |
| `amount_paid` vs `grand_total` | Mantener — alimenta `payment_status` |
| Pago fuerza `confirmed` | Revisar — en restaurante confirm ≠ pagado |

#### Criterio de cierre 6.3

| Ítem | Estado |
|------|--------|
| Agregado raíz = Pedido | **Hecho** |
| Diagrama documentos derivados | **Hecho** |
| Máquina de estados operativos v1 | **Hecho** |
| Estados de línea | **Hecho** |
| Ejes payment / fiscal separados | **Hecho** (decisión) |
| Aprobación responsable | Pendiente |

---

### 6.4 — Flujos comerciales (escenarios)

**Objetivo:** validar el modelo 6.3 contra verticales reales.

**Estado:** borrador v1 — secuencias documentadas; pendiente validación operaciones.

#### Definiciones transversales v1

| Concepto | Definición |
|----------|------------|
| **Transferencia a caja** | Pedido creado por mesero (`handheld`) se asocia a terminal/caja fija para cobro; mismo pedido, cambia `terminal_id` de cobro |
| **Split bill** | Pedido padre → N sub-pedidos por `parent_order_id`; cada uno cobra independiente |
| **Suspender** | Pedido permanece en `draft` con `suspended_at`; retomable mismo día |
| **Unir mesas** | Varios pedidos `draft` de mesas fusionadas → un pedido padre |

#### Restaurante — secuencia v1

```text
Mesero (handheld)                Cocina (KDS)              Caja (fixed)
      │                               │                         │
      ├─ crear draft                  │                         │
      ├─ confirm ────────────────────►│ ticket líneas           │
      │                               ├─ in_progress            │
      │                               ├─ ready                  │
      ├─ transferir a caja ────────────────────────────────────►│
      │                                                         ├─ capturar pago
      │                                                         ├─ payment_status=paid
      │◄────────────────────────────────────────────────────────┤ delivered (opcional)
```

| Paso | Estado pedido | `payment_status` | Evento |
|------|---------------|------------------|--------|
| Tomar orden | `draft` | `unpaid` | `commerce.order.created` |
| Enviar cocina | `confirmed` → `in_progress` | `unpaid` | `commerce.order.confirmed` |
| Plato listo | `ready` | `unpaid` | `eposone.kds.ticket.ready` |
| Cobrar en caja | `ready` o `delivered` | `paid` | `commerce.payment.captured` |
| Cerrar | `delivered` | `paid` | `commerce.order.status_changed` |

**Propina:** línea especial `tip` o pago `payment_type=tip` — decisión final en **6.7**.

#### Retail — secuencia v1

```text
Vendedor (fixed o handheld)
      ├─ crear draft (escaneo)
      ├─ confirm (inmediato — sin KDS)
      ├─ capturar pago (mismo rol)
      ├─ payment_status=paid
      ├─ fiscal_status=pending → invoiced (6.8)
      └─ delivered (entrega mostrador)
```

| Paso | Estado | Notas |
|------|--------|-------|
| Venta mostrador | `draft` → `confirmed` → `delivered` | Sin `in_progress` si no hay fulfillment |
| Devolución | `refunded` | Requiere supervisor; reingreso stock (6.5) |

#### Ferretería — secuencia v1

```text
Vendedor → pedido grande (crédito o contado)
      ├─ contact obligatorio
      ├─ confirm
      ├─ si contado: pago → delivered
      ├─ si crédito: payment_status=unpaid, delivered desde bodega
      └─ factura al despachar o al cobrar (config org — 6.8)
```

#### Mayorista — secuencia v1

```text
Cotización → convertir a pedido
      ├─ confirm
      ├─ entregas parciales (Delivery partial — 6.5/6.4)
      ├─ N pagos parciales permitidos
      └─ factura consolidada o por entrega (6.8)
```

#### Delivery — secuencia v1

```text
Canal: menú QR / call center / marketplace
      ├─ crear pedido (branch + contact obligatorio)
      ├─ confirm
      ├─ in_progress → ready (cocina)
      ├─ Delivery creado al `ready`
      ├─ pago anticipado O contra entrega (6.7)
      └─ delivered al completar entrega
```

| Pago | Momento |
|------|---------|
| Anticipado | Antes de `in_progress` |
| Contra entrega | Al `delivered` por repartidor |

#### Matriz vertical × fases del pedido

| Vertical | KDS | Turno caja | Pago antes de `delivered` | Factura |
|----------|:---:|:----------:|:-------------------------:|:-------:|
| Restaurante | ✓ | ✓ | Opcional (caja) | Post-cobro |
| Retail | — | opcional | ✓ | Post-cobro |
| Ferretería | — | ✓ | Según crédito | Configurable |
| Mayorista | — | — | Parcial | Por entrega |
| Delivery | ✓ | — | Anticipado o final | Post-cobro |

#### Criterio de cierre 6.4

| Ítem | Estado |
|------|--------|
| Secuencia restaurante | Hecho (borrador v1) |
| Secuencia retail | Hecho (borrador v1) |
| Secuencia ferretería / mayorista / delivery | Hecho (borrador v1) |
| Definiciones transversales | Hecho (borrador v1) |
| Validación con operaciones reales | Pendiente |

---

### 6.5 — Inventario (solo modelado)

**Objetivo:** reglas de stock **sin implementar** tablas ni UI.

**Estado:** borrador decisión v1.

#### Principios v1

| Principio | Decisión |
|-----------|----------|
| Catálogo | `core_product` (Etapa 10) — EPosOne **no** duplica catálogo |
| Ubicación stock | `org_unit.type = warehouse` bajo sucursal |
| ¿Todo producto tiene stock? | **No** — flag `tracks_inventory` por producto |
| Restaurante (insumos / recetas) | **Fuera de v1 POS** — solo productos terminados con stock opcional |
| Precios / promociones | Dominio comercial (listas por sucursal/POS); no inventario |

#### Modelo conceptual

```text
core_product (tracks_inventory?)
    └── StockBalance (warehouse_id + product_id → quantity_on_hand, quantity_reserved)
            └── StockMovement (ledger inmutable: reserve, release, deduct, return, adjust, transfer)
```

#### Tabla momento × acción v1

| Momento | Acción inventario | Evento | Retail | Restaurante (plato con stock) |
|---------|-------------------|--------|:------:|:-----------------------------:|
| `draft` | — | — | — | — |
| `confirmed` | **Reservar** cantidad | `commerce.inventory.reserved` | ✓ | Opcional* |
| `cancelled` | **Liberar** reserva | `commerce.inventory.released` | ✓ | ✓ |
| `payment_status=paid` | **Descontar** (si política `deduct_on_paid`) | `commerce.inventory.deducted` | ✓** | — |
| `delivered` | **Descontar** (si política `deduct_on_delivered`) | `commerce.inventory.deducted` | Config | ✓ |
| `refunded` | **Devolver** a stock | `commerce.inventory.returned` | ✓ | ✓ |
| Ajuste manual | **Adjust** ± | `commerce.inventory.adjusted` | Supervisor | Supervisor |

\* Restaurante v1: la mayoría de platos **no** llevan stock; excepción botellas/bebidas empaquetadas.

\*\* Retail por defecto: `deduct_on_paid` — el cliente se lleva el producto al pagar.

#### Política por producto v1 (`inventory_policy`)

| Política | Reserva en `confirmed` | Descuento en |
|----------|:------------------------:|--------------|
| `none` | — | — (servicios, platos cocinados) |
| `retail_standard` | ✓ | `paid` |
| `dispatch_required` | ✓ | `delivered` (ferretería, bodega) |
| `consignment` | — | `delivered` + factura |

Configurable a nivel org con override por `core_product`.

#### Devoluciones v1

| Tipo | Stock | Regla |
|------|-------|-------|
| Devolución íntegra | Reingreso automático a `warehouse` de venta | Con pedido `refunded` |
| Producto dañado | **No** reingresa — movimiento `waste` | Supervisor + motivo |
| Cambio por otro producto | Devolución + nueva venta (nuevo pedido o línea) | Retail |

#### Stock negativo v1

| Regla | Valor |
|-------|-------|
| Por defecto | **Prohibido** |
| Con permiso supervisor | Permitido si `org.allow_negative_stock=true` |
| Auditoría | Todo negativo genera alerta + `commerce.inventory.negative` |

#### Multi-sucursal y transferencias v1

| Operación | Regla |
|-----------|-------|
| Stock | Por `warehouse_id` (cada sucursal ≥ 1 bodega) |
| Venta | Descuenta bodega de la **sucursal del pedido** |
| Transferencia entre bodegas | Documento `StockTransfer` (fuera del pedido) — supervisor |
| Transferencia entre sucursales | Igual — no implícita en pedido |

#### Kits / combos v1

- Producto `type=kit` con componentes (`kit_lines`).
- Al **descontar**: explosión a componentes según cantidad vendida.
- Reserva: sobre componentes si todos `tracks_inventory`.

#### Relación con pedido (6.3)

- El pedido **no** es documento de inventario; dispara movimientos vía eventos.
- Línea cancelada libera reserva de esa línea solamente.

#### Criterio de cierre 6.5

| Ítem | Estado |
|------|--------|
| Tabla momento × acción | Hecho (borrador v1) |
| Políticas por vertical | Hecho (borrador v1) |
| Kits y multi-sucursal | Hecho (borrador v1) |
| Aprobación responsable | Pendiente |

---

### 6.6 — Caja (solo modelado)

**Objetivo:** ciclo de vida del dinero en efectivo y medios en caja.

**Estado:** borrador decisión v1.

#### Ciclo del turno v1

```text
open ──► (cobros / reembolsos / retiros) ──► reconciling ──► closed
```

| Estado turno | Significado |
|--------------|-------------|
| `open` | Cajero operando; acepta cobros efectivo |
| `reconciling` | Arqueo en curso — no nuevos cobros |
| `closed` | Turno cerrado; totales congelados |

#### Decisiones v1

| Pregunta | Decisión |
|----------|----------|
| ¿Apertura con fondo fijo obligatorio? | **Sí** — `opening_balance` ≥ 0; puede ser 0 |
| ¿Cobro efectivo sin turno? | **No** |
| ¿Cobro tarjeta sin turno? | **Sí** en `retail_simple_mode`; **No** en restaurante |
| ¿Reembolso en turno distinto al cobro? | **No** en v1 — mismo turno o supervisor |
| ¿Arqueo? | **Ciego** — cajero ingresa conteo; sistema muestra diferencia al supervisor |
| ¿Un cajero, un turno activo? | **Sí** — un `User` no puede tener dos turnos `open` |
| ¿Ventas a crédito en caja? | Registran **compromiso** de pago; no incrementan efectivo en turno hasta cobro |

#### Movimientos de caja v1

| Tipo | Efecto |
|------|--------|
| `sale_cash` | + efectivo por pago capturado |
| `refund_cash` | − efectivo por reembolso |
| `cash_in` | Ingreso manual (fondo adicional) — supervisor |
| `cash_out` | Retiro (depósito banco) — supervisor |
| `tip_cash` | Propina en efectivo (si no va como línea de pedido) |

Eventos: `commerce.cash_shift.opened`, `.movement_recorded`, `.reconciling`, `.closed`.

#### Criterio de cierre 6.6

| Ítem | Estado |
|------|--------|
| Máquina de estados turno | Hecho (borrador v1) |
| Reglas arqueo y reembolso | Hecho (borrador v1) |
| Aprobación responsable | Pendiente |

---

### 6.7 — Pagos (solo modelado)

**Objetivo:** medios de pago y combinaciones.

**Estado:** borrador decisión v1.

#### Catálogo `payment_type` v1

| Tipo | Código | Turno caja | Offline |
|------|--------|:----------:|:-------:|
| Efectivo | `cash` | Requerido | ✓ |
| Tarjeta | `card` | Recomendado | Cola* |
| Transferencia | `transfer` | No | Cola |
| Yappy / wallet | `wallet` | No | Cola |
| Crédito / cuenta | `credit` | No | ✓ |
| Otro | `other` | Configurable | ✓ |

\* Tarjeta offline: registrar intención; capturar al reconectar o forzar efectivo alternativo.

#### Reglas v1

| Pregunta | Decisión |
|----------|----------|
| ¿Un pedido, N pagos? | **Sí** — pagos parciales permitidos |
| ¿Pago parcial? | `payment_status=partial` hasta cubrir `grand_total` |
| ¿Propina? | Línea `OrderLine` con `product_ref=TIP` (preferencia v1) — no pago separado |
| ¿Pago > total? | `overpaid` — diferencia registrada como propina o cambio según medio |
| ¿Mixto? | Varios `Payment` en secuencia; orden libre |
| ¿Reembolso? | `Payment` con `status=refunded` vinculado al original; supervisor |

#### Estados de pago v1

`pending` → `authorized` (opcional tarjeta) → `captured` → `refunded` \| `partial_refund` \| `failed`

**Regla:** `payment_status` del pedido se calcula de la suma de pagos `captured` vs `grand_total`.

Eventos: `commerce.payment.initiated`, `.captured`, `.failed`, `.refunded`.

#### Criterio de cierre 6.7

| Ítem | Estado |
|------|--------|
| Catálogo medios | Hecho (borrador v1) |
| Reglas mixtas y parciales | Hecho (borrador v1) |
| Propina | Hecho — línea `TIP` (v1) |
| Aprobación responsable | Pendiente |

---

### 6.8 — Facturación

**Objetivo:** cuándo y cómo nace el documento fiscal sin convertirlo en el centro del sistema.

**Estado:** borrador decisión v1.

#### Principios v1

| Principio | Decisión |
|-----------|----------|
| Centro del flujo | **Pedido** (6.3) — factura es derivada |
| Emisión | **Bajo demanda automática** según regla org, no manual obligatoria en POS |
| Módulo FE Panamá | App **`efactura`** existente — EPosOne invoca `InvoiceService` → delega a `efactura` |
| Contabilidad | Tabla `invoices` legacy sigue como destino contable; vínculo `order_id` |

#### Cuándo nace la factura v1

| Trigger org (`fiscal_emit_on`) | Cuándo | Vertical típica |
|-------------------------------|--------|-----------------|
| `on_paid` | `payment_status` → `paid` | Retail, restaurante consumidor final |
| `on_delivered` | `operational_status` → `delivered` | Ferretería despacho, mayorista |
| `manual` | Usuario solicita desde back office | B2B, consolidados |
| `never` | Solo ticket interno | Org sin obligación FE |

**Default v1:** `on_paid` para POS; configurable por sucursal.

#### Relación pedido ↔ factura v1

```text
CommercialOrder (1) ──► (0..N) CommercialInvoice
                              │
                              ├── kind: fiscal | non_fiscal | proforma
                              ├── status: draft → posted → (paid) → cancelled
                              └── external: ElectronicInvoiceDocument (efactura)
```

| Pregunta | Decisión v1 |
|----------|-------------|
| ¿1 pedido = 1 factura? | **Default sí** — excepción: consolidación B2B manual |
| ¿Factura sin pedido? | **No** en EPosOne — excepciones solo back office contable |
| ¿Factura antes de cobrar? | **Solo** crédito autorizado (`payment_type=credit`) + config |
| ¿Proforma? | Cotización o pedido `draft`/`confirmed` — **no** sustituye factura fiscal |

#### Eje `fiscal_status` del pedido (6.3)

| Valor | Significado |
|-------|-------------|
| `not_required` | Org/sucursal sin FE obligatoria para esta venta |
| `pending` | Cobrado/entregado — factura pendiente de emisión |
| `invoiced` | Al menos una factura `posted` vinculada |
| `cancelled` | Factura anulada fiscalmente |

#### Sin Internet v1

```text
Pedido cobrado offline
    ├─ fiscal_status = pending
    ├─ Cola local: FiscalOutbox (idempotency_key)
    ├─ Ticket no fiscal / pre-factura impreso (config)
    └─ Al reconectar: emisión FE + actualización fiscal_status
```

| Regla | Decisión |
|-------|----------|
| Numeración contingencia | Secuencia local `contingency_*` por sucursal — reemplazada al sincronizar |
| Reintentos | Misma cola que sync (6.9) — dominio `fiscal` |
| Fallo PAC | Pedido queda `paid`; `fiscal_status=pending` — reintento manual |

#### FE Panamá v1 (handoff V3 Etapa 10)

| Tema | Decisión |
|------|----------|
| Punto de emisión | Por **sucursal** (`branch_id`) — alineado con `efactura` config |
| RUC cliente | `Contact` fiscal del pedido |
| Anulación | Nota de crédito vía `efactura`; pedido mantiene historial |
| Implementación | **V3 Etapa 10** — aquí solo contrato de dominio |

#### Nota de crédito / reembolso v1

| Situación | Acción |
|-----------|--------|
| Reembolso con factura `posted` | Emitir **nota de crédito** referenciando factura + pedido |
| Reembolso sin factura emitida | Cancelar pedido; **no** nota de crédito |
| Anulación fiscal | Proceso `efactura`; `fiscal_status=cancelled` en pedido |

Eventos: `commerce.invoice.requested`, `.posted`, `.failed`, `.cancelled`.

#### Criterio de cierre 6.8

| Ítem | Estado |
|------|--------|
| Triggers de emisión | Hecho (borrador v1) |
| Relación pedido-factura | Hecho (borrador v1) |
| Reglas offline / contingencia | Hecho (borrador v1) |
| Handoff efactura + Etapa 10 | Hecho |
| Aprobación responsable | Pendiente |

---

### 6.9 — Sincronización y offline

**Objetivo:** qué se sincroniza, en qué orden, y cómo se resuelven conflictos.

**Estado:** borrador decisión v1.

#### Principios v1

| Principio | Decisión |
|-----------|----------|
| Fuente de verdad | **Servidor** — cliente offline es caché + cola de escritura |
| Transporte | Eventos + operaciones idempotentes — **no** sync de tablas entre apps |
| Identificador offline | `idempotency_key` por operación (UUID generado en terminal) |
| Versión | Campo `version` en pedido — optimistic locking |

#### Alcance offline v1

| Dominio | Lectura offline | Escritura offline |
|---------|:---------------:|:-----------------:|
| Catálogo / precios | ✓ pull incremental | — |
| Pedidos (`draft`–`delivered`) | ✓ últimos N | ✓ crear, confirmar, cambiar estado |
| Pagos | — | ✓ capturar (cola) |
| Turno caja | Estado último conocido | ✓ abrir/cerrar (cola) |
| Inventario | Saldo cacheado | — (solo lectura en v1) |
| Factura FE | — | ✓ encolar emisión (6.8) |
| Reportes | — | — |

#### Prioridad de sincronización v1

```text
1. Pagos capturados        (dinero — crítico)
2. Pedidos / cambios estado
3. Turnos de caja
4. Cola fiscal (FE)
5. Catálogo (pull)
6. Ajustes inventario (push supervisor)
```

#### Dominios sync (alineado scaffold)

| Dominio | Código | Contenido |
|---------|--------|-----------|
| Eventos | `events` | Pull `platform_domain_event` desde cursor |
| Pedidos | `orders` | Push operaciones `create_order`, `capture_payment`, `transition_order` |
| Catálogo | `catalog` | Pull productos/precios desde cursor |

#### Operaciones encoladas v1

| `operation_type` | Idempotente | Handler |
|------------------|:-----------:|---------|
| `create_order` | ✓ | `eposone/sync_handlers` |
| `capture_payment` | ✓ | idem |
| `transition_order` | ✓ | idem |
| `open_cash_shift` | ✓ | futuro Etapa 7 |
| `close_cash_shift` | ✓ | futuro Etapa 7 |
| `emit_fiscal` | ✓ | delega 6.8 |

#### Resolución de conflictos v1

| Entidad | Estrategia | Regla |
|---------|------------|-------|
| Catálogo / precios | `server_wins` | Cliente actualiza cache |
| Pedido en `draft` | `version_mismatch` → manual | Mesero y caja editando mismo pedido |
| Pedido post-`confirmed` | **Reglas de negocio** | No merge automático — supervisor |
| Pago duplicado | Rechazar por `idempotency_key` | Segundo submit ignorado |
| Stock | `server_wins` | Reserva fallida → alerta en terminal |

Matriz detallada:

| Conflicto | Detección | Resolución |
|-----------|-----------|------------|
| Versión pedido | `base_version != server.version` | UI: recargar o forzar con supervisor |
| Doble cobro | Misma `idempotency_key` | Ignorar segundo — respuesta original |
| Stock insuficiente al sync | Reserva rechazada | Pedido queda `confirmed` con alerta; supervisor ajusta |
| Turno ya cerrado en servidor | Operación rechazada | Reabrir turno o transferir a otro |

#### Multi-terminal offline misma sucursal v1

| Regla | Valor |
|-------|-------|
| Pedidos | Cada terminal crea con `terminal_id` propio |
| Mismo pedido dos terminales | Servidor serializa por `version` |
| Cobro offline mismo pedido | Primera `idempotency_key` gana |
| Catálogo | Pull compartido; mismo cursor por sucursal |

#### Reintentos v1

| Cola | Backoff | Max reintentos |
|------|---------|----------------|
| `platform_sync_operation` | Exponencial desde 30s | 5 (config `NODEONE_EVENT_BUS_MAX_RETRIES`) |
| Eventos bus | `next_retry_at` en `platform_domain_event` | idem |
| FE / PAC | Independiente — no bloquea pedido `paid` | manual tras max |

#### Eventos sync v1

`platform.sync.operation.enqueued`, `.applied`, `.conflict`, `.failed`

**Regla:** catálogo completo `commerce.*` y `eposone.*` v2 se publica al cerrar implementación Etapa 7; aquí quedan definidas prioridades y estrategias.

#### Criterio de cierre 6.9

| Ítem | Estado |
|------|--------|
| Alcance offline | Hecho (borrador v1) |
| Prioridades | Hecho (borrador v1) |
| Matriz conflictos | Hecho (borrador v1) |
| Operaciones idempotentes | Hecho (borrador v1) |
| Aprobación responsable | Pendiente |

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
| 1 | 6.1 Organización comercial — diagrama y glosario aprobados | Borrador v1 |
| 2 | 6.2 Personas y roles — matriz rol × acción | Borrador v1 |
| 3 | 6.3 Documento maestro — **Pedido** confirmado como agregado raíz | **Cerrado v1** |
| 4 | 6.4 Flujos — 5 escenarios con secuencias y eventos | Borrador v1 |
| 5 | 6.5 Inventario — reglas momento × acción (sin código) | Borrador v1 |
| 6 | 6.6 Caja — ciclo turno completo modelado | Borrador v1 |
| 7 | 6.7 Pagos — medios y reglas mixtas | Borrador v1 |
| 8 | 6.8 Facturación — nacimiento documento + offline | Borrador v1 |
| 9 | 6.9 Sincronización — prioridades y conflictos | Borrador v1 |
| 10 | Master Plan V3.1 actualizado y referenciado | Hecho |
| 11 | Aprobación explícita responsable del proyecto | Pendiente |

**Progreso:** **9/9 bloques** modelados (6.3 cerrado v1; 6.1–6.2, 6.4–6.9 borrador v1).

**Siguiente paso:** revisión integral + **aprobación responsable** → desbloquea **V3 Etapa 7 — Construcción**.

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

## Guía de aprobación — cierre Etapa 6

**Una sesión.** Objetivo: validar decisiones v1.2 y firmar cierre. **No es implementación.**

### Decisiones críticas (validar sí / no / ajuste)

| # | Bloque | Pregunta de cierre | Doc |
|---|--------|-------------------|-----|
| 1 | 6.3 | ¿**Pedido** es el agregado raíz y la factura es derivada? | §6.3 |
| 2 | 6.3 | ¿Tres ejes separados: operación, pago, fiscal? | §6.3 |
| 3 | 6.1 | ¿Jerarquía empresa → sucursal → POS → caja → turno? | §6.1 |
| 4 | 6.2 | ¿Mesero no cobra en restaurante; cajero abre turno? | §6.2 |
| 5 | 6.4 | ¿Restaurante: confirmar cocina **antes** de pagar? | §6.4 |
| 6 | 6.5 | ¿Retail descuenta en `paid`; despacho en `delivered`? | §6.5 |
| 7 | 6.6 | ¿Arqueo ciego; efectivo solo con turno abierto? | §6.6 |
| 8 | 6.7 | ¿N pagos por pedido; propina como línea `TIP`? | §6.7 |
| 9 | 6.8 | ¿FE vía app `efactura`; emisión default `on_paid`? | §6.8 |
| 10 | 6.9 | ¿Servidor fuente de verdad; conflictos pedido = manual? | §6.9 |

### Checklist por bloque

| Bloque | Modelado | Aprobado | Observaciones |
|--------|:--------:|:--------:|---------------|
| 6.1 Organización | ✓ | ☐ | |
| 6.2 Personas / roles | ✓ | ☐ | |
| 6.3 Documento maestro | ✓ | ☐ | |
| 6.4 Flujos verticales | ✓ | ☐ | |
| 6.5 Inventario | ✓ | ☐ | |
| 6.6 Caja | ✓ | ☐ | |
| 6.7 Pagos | ✓ | ☐ | |
| 6.8 Facturación | ✓ | ☐ | |
| 6.9 Sincronización | ✓ | ☐ | |

### Cierre formal

| Campo | Valor |
|-------|--------|
| Documento | `EN1_PLATFORM_ETAPA6_DOMINIO_COMERCIAL.md` v1.2 |
| Resultado | ☐ **Aprobado** · ☐ Aprobado con cambios · ☐ Rechazado |
| Responsable | _________________________ Fecha: _________ |
| Cambios acordados | (si aplica) |

**Tras aprobación:** actualizar estado a **Cerrada** en este doc y en Master Plan; **recién entonces** se autoriza planificar V3 Etapa 7 (con GO explícito en chat nuevo).

**Hasta entonces:** Regla 7 vigente — congelar features POS nuevas; scaffold solo mantenimiento.

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

*Etapa 6 dominio comercial — 2026-07-08 (v1.2: bloques 6.1–6.9 modelados). Cambios requieren actualizar este doc y acuerdo del responsable. Sin GO explícito: no implementación funcional nueva.*
