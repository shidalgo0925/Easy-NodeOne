# Order Domain Specification v1.0

| Campo | Valor |
|-------|--------|
| Estado | **Borrador arquitectónico** — 14 jul 2026 · pendiente **congelar** antes de GO P1 |
| Fuente de verdad | Hito 3 (Dominio) + contrato para Hito 4 (Operación APK) |
| Roadmap | [`EN1_PLATFORM_EPOSONE_V5_ROADMAP.md`](EN1_PLATFORM_EPOSONE_V5_ROADMAP.md) |
| Spec funcional | [`EN1_EPOSONE_HITO3_SPEC_FUNCIONAL_V1.md`](EN1_EPOSONE_HITO3_SPEC_FUNCIONAL_V1.md) |
| ADR | [`ADR-006-EPOSONE-OPERATION-VS-ADMIN.md`](ADR-006-EPOSONE-OPERATION-VS-ADMIN.md) |
| Desarrollo | **Prohibido** hasta marcar esta Spec como **CONGELADA** + GO explícito P1 |

Este documento es la **única fuente de verdad** del dominio Pedido. P1 implementa EN1 según él; P2 consume el contrato sin inventar reglas.

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

### Pendiente de clavar al congelar (no inventar en código)

- Ownership del **pedido hijo** al **dividir**: ¿hereda POS padre o POS que ejecuta la división? → default propuesto al congelar: **mismo owner_pos** del pedido origen, salvo acción explícita de transferencia.  
- Ancla sin mesa (food truck / barra): ver §5.

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

## 5. Ancla de agrupación (mesa / sin mesa)

**Cerrado:** un **pedido abierto por mesa**; si llega otra orden de esa mesa → **se agrega al mismo Pedido**.  
**Cerrado:** no fusionar pedidos.  
**Cerrado:** dividir pedidos **permitido**.

### Modo con mesa

`table_ref` obligatorio (o equivalente) → a lo sumo **un** Order abierto por `(org, branch, table_ref)`.

### Modo sin mesa (Solo POS / food truck / barra) — a clavar al congelar

Misma entidad Order. Ancla candidata (elegir una en congelación):

| Opción | Uso |
|--------|-----|
| A | `service_ref` / turno de mostrador |
| B | Sin ancla: cada “Nuevo Pedido” es un Order nuevo (no hay “mesa”) |
| C | `counter_ticket` efímero |

**Default propuesto para congelar:** opción **B** cuando `table_ref` es null (negocio sin mesas).

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

### Eventos hacia EN1 (mínimo)

| Evento | Notas |
|--------|--------|
| `pedido.creado` | |
| `pedido.actualizado` | |
| `producto.agregado` | |
| `producto.eliminado` | |
| `cantidad.modificada` | |
| `pedido.enviado` | |
| `pedido.listo` / `linea.lista` | según granularidad cocina |
| `pedido.entregado` / entrega parcial | |
| `pedido.cobrado` | cierre financiero |
| `pago.registrado` | mixto / abono / parcial |
| `pedido.anulado` | |
| `pedido.devuelto` | |
| `linea.cancelada` | si aplica |

Nombres finales pueden ajustarse al congelar; la semántica no.

---

## 8. APIs EN1 (Hito 3 — solo Pedido)

Auth: **Device Bearer** (mismo esquema Hito 1/2) y/o sesión BO para BackOffice.  
**No** reutilizar solo `@login_required` de `/api/eposone/*` para el POS.

Ejemplos (paths finales al congelar; semántica fija):

```http
POST   /api/v1/orders
GET    /api/v1/orders
GET    /api/v1/orders/{id}
PATCH  /api/v1/orders/{id}
POST   /api/v1/orders/{id}/events
POST   /api/v1/orders/{id}/payments
```

(Endpoints de anulación/devolución pueden ser events tipados o sub-rutas — decidir al congelar.)

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

## 11. Criterio de “Spec congelada”

Arquitectura marca esta Spec **CONGELADA** cuando:

1. Ownership al dividir + ancla sin mesa (§3 y §5) quedan en una sola opción cada uno.  
2. Paths/auth API §8 cerrados.  
3. Lista de `event.type` definitiva.  
4. GO a P1 emitido en chat (solo Dev EN1).  

Hasta entonces: **nadie escribe código** del dominio Pedido.

---

## 12. Orden de trabajo P1 / P2

```text
1. Congelar este documento
2. GO → P1: entidades + APIs + eventos (sin inventario)
3. Review → congelar contrato HTTP/eventos (tag o commit)
4. GO → P2: consumir APIs; no inventar reglas
5. E2E (Hito 4)
```

P2 implementación de UI (Hito 4) — acciones mínimas:

Nuevo Pedido · Agregar/Eliminar producto · Modificar cantidad · Cobrar · Entregar · Sincronizar  

(`Enviar` / cocina según modo org; mismas APIs.)
