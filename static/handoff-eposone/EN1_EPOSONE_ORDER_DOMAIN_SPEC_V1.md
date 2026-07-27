# Order Domain Specification v1.0

| Campo | Valor |
|-------|--------|
| Estado | **CONGELADA** — 14 jul 2026 |
| Versión | **v1.0** (fuente de verdad Hito 3 / contrato Hito 4) |
| Roadmap | [`EN1_PLATFORM_EPOSONE_V5_ROADMAP.md`](EN1_PLATFORM_EPOSONE_V5_ROADMAP.md) |
| Spec funcional | [`EN1_EPOSONE_HITO3_SPEC_FUNCIONAL_V1.md`](EN1_EPOSONE_HITO3_SPEC_FUNCIONAL_V1.md) |
| ADR | [`ADR-006-EPOSONE-OPERATION-VS-ADMIN.md`](ADR-006-EPOSONE-OPERATION-VS-ADMIN.md) |
| Código | **Implementado en Dev** · tag `eposone-order-domain-v1.0` (`36a0eb1`) · Spec **CONGELADA** (cambios = v1.1+) |
| Handoff APK | Carpeta [`handoff-eposone/`](handoff-eposone/) · contrato HTTP Hito 3B |

Este documento es la **única fuente de verdad** del dominio Pedido. P1 implementa EN1 según él; P2 consume el contrato sin inventar reglas. Cambios solo con nueva versión (v1.1+) y GO de arquitectura.


---

## 1. Propósito

Definir entidades, ownership, acciones→eventos, pagos, cancelaciones y APIs del Pedido **sin** inventario, FE ni mini-ERP.

---

## 2. Principios (cerrados)

| # | Regla |
|---|--------|
| 1 | Un solo tipo de **Pedido** |
| 2 | Dueño en operación = **EPosOne** (offline); tras sync fuente oficial = **EN1** |
| 3 | Usuario **nunca** edita estados; solo **acciones** |
| 4 | Comunicación = **eventos**, no tablas |
| 5 | **Ownership** elimina conflictos de edición concurrente |

### Cadena de negocio

```text
Pedido → Operación → Pago → Venta → Inventario → Caja → Factura
```

(Hitos 5–7 implementan eslabones posteriores; el dominio Pedido solo emite los eventos necesarios.)

---

## 3. Ownership (cerrado)

| Situación | Regla |
|-----------|--------|
| Pedido **abierto** (editable) | Dueño = **POS que lo creó**. Otros dispositivos/BO: **lectura**. No modificación. |
| Etapa de **cobro** | Puede cobrarse desde **otro POS** o **BackOffice** (cajas/dispositivos autorizados). |
| Conflictos | No se aplican merges de edición: quien no es owner no escribe líneas/acciones de edición. |
| **Dividir pedido** | El pedido hijo **hereda** `owner_pos` / `owner_device` del pedido **origen**. Transferencia de ownership = acción explícita futura (fuera de Hito 3 mínimo). |

---

## 4. Entidades (P1 — Hito 3)

| Entidad | Rol |
|---------|-----|
| **Order** | Pedido |
| **OrderItem** | Línea |
| **OrderPayment** | Pago / abono / parcial |
| **OrderEvent** | Historial append-only (auditoría + sync) |
| **OrderCancellation** | Anulación (post-preparación) |
| **OrderReturn** | Devolución (post-entrega) |

### Relaciones

```text
Order
  ├── OrderItem (1..n)
  ├── OrderEvent (1..n)
  ├── OrderPayment (0..n)
  ├── OrderCancellation (0..n)
  └── OrderReturn (0..n)
```

### Order — campos mínimos

- `local_number` (POS)  
- `en1_number` (asignado al sync / create en EN1)  
- `organization_id`  
- `branch_ref` · `pos_ref` · `register_ref`  
- `owner_device_uuid` / `owner_pos_ref`  
- `user_ref` (cajero actual; **puede cambiar**)  
- `customer_ref` (opcional; **obligatorio** si hay abono/parcial → CxC)  
- Ancla de servicio: `table_ref` **o** alternativa (§5)  
- `opened_at` · `updated_at` · `status` (derivado)  
- Totales: `subtotal`, `tax`, `discount`, `tip`, `total`  
- `notes`  

### OrderItem — campos mínimos

- `product_ref` · `qty` · `unit_price` · `tax` · `discount` · `notes`  
- `line_status` (independiente por línea — cocina)  
- Identificador de línea estable (`line_id` / `line_ref`)  

### OrderEvent

- `event_id` (idempotente)  
- `type` (ver §7)  
- `occurred_at` · `actor_user_ref` · `actor_device_uuid`  
- `payload` (JSON del cambio)  
- `sequence` / `causal` según diseño EN1  

### OrderPayment

- Monto · método · mixto (varias filas) · abono / parcial  
- Un **cierre financiero** del pedido (flag / evento `pedido.cobrado` cuando saldo = 0 según reglas §6)  

### OrderCancellation / OrderReturn

- Motivo · usuario · fecha/hora · (auth si política)  
- Nunca llamar “cancelación” a una devolución post-entrega  

---

## 5. Ancla de agrupación (mesa / sin mesa) — cerrado

| Regla | Valor |
|-------|--------|
| Un pedido abierto por mesa | Sí |
| Nueva orden misma mesa | Se **agrega** al mismo Pedido |
| Fusionar | No |
| Dividir | Sí (hijo hereda owner del origen — §3) |

### Modo con mesa

`table_ref` presente → a lo sumo **un** Order abierto por `(organization_id, branch_ref, table_ref)`.

### Modo sin mesa (Solo POS / food truck / barra) — **opción B**

Si `table_ref` es **null**:

- No hay ancla de agrupación.  
- Cada acción **Nuevo Pedido** crea un **Order nuevo**.  
- No existe “agregar a la mesa”.  

Misma entidad `Order` en ambos modos.

---

## 6. Decisiones de negocio (cerradas)

### Pedido

| Decisión | Valor |
|----------|--------|
| Un abierto por mesa | Sí |
| Agregar a mismo pedido | Sí |
| Fusionar | No |
| Dividir | Sí |
| Cambiar cajero | Sí |
| Cobro desde cualquier caja autorizada | Sí (etapa cobro) |

### Pago

| Decisión | Valor |
|----------|--------|
| Pago mixto | Sí |
| Un cierre financiero | Sí |
| Abonos | Sí |
| Pagos parciales | Sí |
| Abono/parcial | Solo **clientes registrados** → genera **CxC** |

### Cocina / líneas

| Decisión | Valor |
|----------|--------|
| Líneas independientes | Sí (una línea puede estar lista antes) |
| Entrega parcial | Sí |
| Cancelación por línea | Sí (respetando reglas de cancelación según momento) |

### Cancelaciones

| Momento | Tratamiento |
|---------|-------------|
| Antes de preparar | **Modificar** pedido (no “cancelación”) · sin inventario |
| Después de preparar | **Anulación** · motivo · usuario · ts · auth posible |
| Después de entregar | **Devolución** · nunca “Cancelación” |

### Inventario (contrato de eventos; implementación = Hito 5)

| Decisión | Valor |
|----------|--------|
| Oficial | EN1 |
| POS | Solo eventos; **nunca** escribe Kardex |
| Combos | No descontar el combo; descontar **componentes** |
| Recetas | Se soportarán; **no** en Hito 3/4 |

Momento exacto descuento (cobrar vs entregar): **Hito 5** — el dominio Pedido debe emitir ambos eventos para no bloquear la decisión.

---

## 7. Acciones de usuario → eventos

### Acciones visibles (cerradas)

Nuevo Pedido · Guardar · Agregar Producto · Quitar Producto · Modificar Cantidad · Enviar · Cobrar · Entregar · Anular · Devolver · Reimprimir  

(+ operar por línea: listo / cancelar línea / entregar parcial — derivadas de decisiones cocina.)

### Eventos hacia EN1 (lista definitiva v1.0)

| `event.type` | Semántica |
|--------------|-----------|
| `pedido.creado` | Alta |
| `pedido.actualizado` | Metadatos / totales / cajero / notas (sin ítem) |
| `pedido.dividido` | Split; payload referencia pedido hijo |
| `producto.agregado` | Línea nueva |
| `producto.eliminado` | Línea quitada |
| `cantidad.modificada` | Cambio de qty |
| `pedido.enviado` | Enviado a preparación |
| `linea.lista` | Línea lista (cocina independiente) |
| `pedido.listo` | Pedido completo listo |
| `linea.entregada` | Entrega parcial de línea |
| `pedido.entregado` | Entrega total |
| `pago.registrado` | Pago / abono / parcial / mixto (una fila) |
| `pedido.cobrado` | Cierre financiero (saldo 0) |
| `linea.cancelada` | Cancelación de línea (según momento §6) |
| `pedido.anulado` | Anulación post-preparación |
| `pedido.devuelto` | Devolución post-entrega |

No agregar tipos en Hito 3 sin versión de Spec.

---

## 8. APIs EN1 (Hito 3 — solo Pedido) — cerrado

**Auth**

| Cliente | Auth |
|---------|------|
| POS / tablet | `Authorization: Bearer <device_token>` (mismo esquema Hito 1/2) |
| BackOffice | Sesión usuario admin (Flask-Login) **o** token de servicio BO acordado |

**No** usar solo `@login_required` de `/api/eposone/*` para el Device Token del POS.

**Paths v1.0** (prefijo `/api/v1`):

```http
POST   /api/v1/orders
GET    /api/v1/orders
GET    /api/v1/orders/{id}
PATCH  /api/v1/orders/{id}
POST   /api/v1/orders/{id}/events
POST   /api/v1/orders/{id}/payments
POST   /api/v1/orders/{id}/split
```

Anulación y devolución: vía `POST .../events` con `type` = `pedido.anulado` | `pedido.devuelto` (y entidades `OrderCancellation` / `OrderReturn` persistidas).

**Prohibido en Hito 3:** lógica de inventario, Kardex, stock reserved, transferencias, FE.

---

## 9. Offline y sync

```text
POS (owner) → cola local de eventos → EN1 → confirmación → eventos a BO / otros POS (lectura)
```

Idempotencia por `event_id` obligatoria.

---

## 10. Alcance por hito

| Hito | Entrega |
|------|---------|
| **3** | Dominio EN1 + APIs Pedido + eventos (este documento implementado en backend) |
| **4** | APK: acciones listadas + sync + E2E multi-POS / BO |
| **5** | Inventario operativo (Kardex, stock, reserved, combos, …) |
| **6** | Caja y pagos extendidos (arqueo, etc. además de OrderPayment) |
| **7** | Facturación |

### Congelado fuera de alcance H3

Provisioning · Bootstrap · Catálogo · Productos · Inventario maestro · POS Core  

---

## 11. Estado de congelación

| Chequeo | Estado |
|---------|--------|
| Ownership al dividir (§3) | ✅ Hijo hereda owner del origen |
| Ancla sin mesa (§5) | ✅ Opción B (`table_ref` null → Order nuevo) |
| Paths / auth API (§8) | ✅ |
| Lista `event.type` (§7) | ✅ |
| Spec marcada CONGELADA | ✅ 14 jul 2026 |

**Código del dominio Pedido:** solo tras **GO P1** en chat (Dev EN1). Este GO de congelación **no** autoriza implementación.

---

## 12. Orden de trabajo P1 / P2

```text
1. Spec CONGELADA ✅
2. GO P1 → entidades + APIs + eventos (sin inventario)
3. Review → tag/commit de contrato HTTP
4. GO P2 → consumir APIs; no inventar reglas
5. E2E (Hito 4)
```

P2 (Hito 4) — acciones mínimas UI:

Nuevo Pedido · Agregar/Eliminar producto · Modificar cantidad · Cobrar · Entregar · Sincronizar  

(`Enviar` / cocina según modo org; mismas APIs.)
