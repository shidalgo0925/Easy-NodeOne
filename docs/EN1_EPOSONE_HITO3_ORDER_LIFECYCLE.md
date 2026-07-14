# EPosOne ↔ EN1 — Hito 3: Operación del Pedido (brief + instrucciones P1/P2)

| Campo | Valor |
|-------|--------|
| Hito | **Hito 3 — Operación del Pedido** (antes “Ventas → Stock”) |
| Estado | **Aprobado como dirección** — 14 jul 2026 · **sin implementación** hasta GO + contrato |
| ADR | [`ADR-006-EPOSONE-OPERATION-VS-ADMIN.md`](ADR-006-EPOSONE-OPERATION-VS-ADMIN.md) |
| Precondición | Hito 1 ✅ · Hito 2 E2E APK cerrado |
| Ambiente | Solo **Dev EN1** + APK local |

---

## Redefinición

| Antes | Ahora |
|-------|--------|
| Ventas → Stock | **Operación del Pedido** |

Incluye:

1. Ciclo de vida del Pedido (acciones → estados internos)  
2. Sincronización POS ↔ EN1 del **historial de eventos**  
3. Cobro desde POS o BackOffice  
4. Base para inventario, caja y facturación (hitos siguientes)

**No** incluye en este hito: inventario operativo completo, FE, transferencias, compras, OCR/contes, CRM, IA.

---

## Criterio de cierre Hito 3

Un pedido debe poder:

1. Crearse en un POS  
2. Modificarse desde el POS  
3. Sincronizarse con EN1  
4. Verse en BackOffice EN1  
5. Continuar operación desde **otro POS** o desde BackOffice  
6. Cobrarse desde cualquiera de esos puntos  
7. Mantener historial completo de eventos sin perder consistencia  

Con eso queda la comunicación **bidireccional** EPosOne ↔ EN1.

---

## Modelo de dominio (preparar, no codificar aún)

| Entidad | Notas |
|---------|--------|
| **Order** | Pedido; entidad principal |
| **Order Item** | Líneas |
| **Order Event** | Historial append-only (fuente de verdad del ciclo) |
| **Payment** | Cobro(s) asociados |
| **Cancellation** | Anulación post-preparación |
| **Return** | Devolución post-entrega |

IDs opacos; dominio portable (ADR-002). Detalle de campos = **contrato Hito 3** (chat + GO aparte).

---

## Eventos (lista conceptual)

```text
pedido.creado
pedido.item_agregado | pedido.item_eliminado | pedido.item_cantidad
pedido.enviado
pedido.listo
pedido.entregado
pedido.cobrado
pedido.anulado
pedido.devuelto
```

(Nombres finales en el contrato.)

---

## Cancelaciones (regla de negocio fija)

| Momento | Tipo | Inventario | Auth |
|---------|------|------------|------|
| Antes de preparación | Modificación | No mueve stock | No especial |
| Después de preparación | Anulación | Según política (hito inventario) | Motivo + usuario + ts; auth opcional |
| Después de entrega | Devolución | Puede crédito / ajuste / merma | Según tipo producto |

---

## Instrucción — Programador 1 (EN1)

### Congelado (no tocar sin GO)

- Hito 1 provisioning (`/api/v1/devices/register|config`)  
- Hito 2 bootstrap (`/api/v1/devices/bootstrap`) — salvo bug de auth del contrato  

### Ahora (docs / diseño)

1. Leer ADR-006 completo.  
2. **No** implementar inventario operativo ni FE.  
3. Preparar (diseño) dominio Order / Order Item / Order Event / Payment / Cancellation / Return.  
4. EN1 será fuente oficial del **estado del Pedido** una vez sincronizado + historial completo.  
5. Un pedido iniciado en un POS debe poder consultarse y finalizarse en otro POS o en BO.  
6. **No** lógica de negocio adicional hasta **contrato Hito 3** acordado + GO.

### Hito 2 (si aún abierto en APK)

Si P2 reporta 401 al “Descargar catálogo”: el token de dispositivo **no** autentica `/api/eposone/products` (`@login_required`). El contrato Hito 2 es solo:

`GET /api/v1/devices/bootstrap` + `Authorization: Bearer <device_token>`

No “arreglar” abriendo device auth en BO API salvo GO explícito que cambie arquitectura.

---

## Instrucción — Programador 2 (EPosOne / APK)

### Congelado

- POS Core  
- Provisioning (Hito 1)  
- Device Bootstrap (contrato Hito 2)  

### Ahora — cerrar Hito 2 primero

1. “Descargar catálogo EN1” → **`GET /api/v1/devices/bootstrap`** (Bearer del register).  
2. **No** usar `GET /api/eposone/products` para Sync Down (ese endpoint es sesión usuario BO → 401 con device token).  
3. Persistir catálogo/imágenes/stock de referencia localmente.  
4. E2E tablet limpia → criterio de cierre Hito 2.

### Después (Hito 3 — sin código hasta GO)

1. Leer ADR-006.  
2. Flujo operativo del Pedido offline-first.  
3. Cada acción relevante = **evento** en cola → sync EN1.  
4. Usuario hace acciones; **sistema** cambia estado (sin picker de estados).  
5. No inventariar / transferir / comprar / FE en este hito.

---

## Orden del roadmap (congelado)

```text
Provisioning ✅
    ↓
Bootstrap 🟡  (cerrar E2E: endpoint correcto)
    ↓
Hito 3 — Operación del Pedido ⏸  (contrato + GO)
    ↓
Inventario operativo por eventos ⏸
    ↓
Caja / FE / analítica ⏸
```

---

## Qué NO hacer todavía

- Reabrir Hito 1  
- Cambiar contrato Hito 2  
- Ventas→stock sin dominio Pedido  
- Mini-ERP completo en POS  
- Dos APKs (Lite/Pro)  
- Implementar Hito 3 sin contrato firmado  

---

## Siguiente chat de código

1. P2: fix consumo bootstrap + E2E (cierra Hito 2).  
2. Ambos: chat **contrato Hito 3** (payloads eventos, auth, idempotencia).  
3. GO implementación Hito 3 por lado (EN1 / APK) en chats separados.
