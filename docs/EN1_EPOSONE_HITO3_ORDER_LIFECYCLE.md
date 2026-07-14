# EPosOne ↔ EN1 — Hito 3: Operación del Pedido (brief + instrucciones P1/P2)

| Campo | Valor |
|-------|--------|
| Hito | **Hito 3 — Operación del Pedido** (antes “Ventas → Stock”) |
| Estado | **En diseño** · spec V1.0 registrada · **desarrollo CONGELADO** hasta preguntas §13 + congelar spec |
| Spec funcional | [`EN1_EPOSONE_HITO3_SPEC_FUNCIONAL_V1.md`](EN1_EPOSONE_HITO3_SPEC_FUNCIONAL_V1.md) |
| ADR | [`ADR-006-EPOSONE-OPERATION-VS-ADMIN.md`](ADR-006-EPOSONE-OPERATION-VS-ADMIN.md) |
| Precondición | Hito 1 ✅ · Hito 2 E2E APK cerrado |
| Ambiente | Solo **Dev EN1** + APK local |
| Audiencia código | **Ninguna** hasta sesión arquitectura + GO |

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

- Hito 1 provisioning  
- Hito 2 bootstrap (salvo bug del contrato)  
- **Todo desarrollo Hito 3** hasta spec congelada  

### Ahora

1. Leer ADR-006 + [`EN1_EPOSONE_HITO3_SPEC_FUNCIONAL_V1.md`](EN1_EPOSONE_HITO3_SPEC_FUNCIONAL_V1.md).  
2. **No** implementar dominio Pedido, APIs ni inventario operativo.  
3. Esperar respuestas §13 y versión **congelada** de la spec + GO.

---

## Instrucción — Programador 2 (EPosOne / APK)

### Congelado

- POS Core · Provisioning · contrato Bootstrap  
- **Operación del Pedido (Hito 3)** hasta spec congelada + GO  

### Ahora — puede cerrar Hito 2 (independiente)

1. “Descargar catálogo” → `GET /api/v1/devices/bootstrap` (Bearer dispositivo).  
2. No usar `/api/eposone/products` para Sync Down.  
3. No inventar reglas de negocio del Pedido.

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
