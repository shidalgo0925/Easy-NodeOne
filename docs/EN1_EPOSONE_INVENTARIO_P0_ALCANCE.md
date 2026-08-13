# EN1 + EPosOne — Inventario P0 (alcance)

| Campo | Valor |
|-------|--------|
| Estado | **Análisis acordado** — alcance P0 (no es implementación) |
| Fecha | 10 ago 2026 |
| Audiencia | Producto / Ana / EN1 + EPosOne |
| Relacionado | [ADR-006](ADR-006-EPOSONE-OPERATION-VS-ADMIN.md) · [Handoff productos+inventario](EN1_EPOSONE_HANDOFF_PRODUCTOS_INVENTARIO.md) · [Order Domain](EN1_EPOSONE_ORDER_DOMAIN_SPEC_V1.md) · [Handoff status](EN1_EPOSONE_HANDOFF_STATUS.md) |

---

## Una frase

Inventario EPosOne es un **flujo operativo** (productos → existencias → movimientos → alertas), no una pantalla de “stock = N”. En P0 una tienda puede entrar mercancía, vender y ver bajar el stock, ajustar con motivo y consultar kardex — sin convertirse en un ERP.

---

## Principios (no negociables)

| Regla | Detalle |
|-------|---------|
| Stock = consecuencia | La existencia actual sale de **movimientos** auditable; no se edita el número a mano |
| EN1 = fuente oficial | [ADR-006](ADR-006-EPOSONE-OPERATION-VS-ADMIN.md): POS opera y emite eventos; no escribe tablas de stock EN1 |
| Historia | Quién + cuándo + sucursal + producto + antes/después + motivo + referencia |
| Modelo anticipado | Simple / Fraccionable / Receta-Combo en el **dominio desde P0**, aunque la UI de bar avance después |

---

## P0 — SÍ

| Capacidad | Notas |
|-----------|--------|
| Dashboard operativo | Productos, existencia, stock bajo, agotados, movimientos hoy. Valor $ solo estimado (último costo) o diferido si no hay costo confiable |
| Productos (alta corta) | Nombre, categoría, SKU, barcode, unidad, precio/costo/impuesto, imagen opcional — pocos campos |
| Tipos en **modelo** | Simple · Fraccionable · Receta/Combo |
| Control de existencia | Flag + mínimo (+ máximo opcional) + existencia inicial vía movimiento |
| Existencias | on_hand / reserved / available por sucursal-bodega |
| Entrada de mercancía | Proveedor opcional, documento/factura, líneas qty+costo → movimiento ENTRY |
| Venta → salida automática | Cobro confirmado → SALE (o expansión BOM). El cajero **no** toca inventario |
| Devolución | RETURN con referencia a pedido |
| Ajuste con motivo | Sistema vs físico; motivos predefinidos; auditoría completa |
| Stock mínimo → alerta | Lista “requieren atención” |
| Kardex / historial | Por producto: fecha, movimiento, cant., antes, después, ref. |
| Solo POS (excepción) | Alta/ajuste básico con motivo como **evento** hacia EN1 |

### Motivos de ajuste (P0)

Conteo físico · Producto dañado · Vencimiento · Pérdida/merma · Uso interno · Error de registro · Otro.

---

## P0 — NO

| Capacidad | Fase |
|-----------|------|
| UI completa de tragos (presentaciones en caja) | **P1** |
| Merma bar (teórico vs físico + autorización dedicada) | **P1** |
| Conteo físico / inventario cíclico (UI) | **P1** (diseñado; implementar después) |
| Transferencias EN TRÁNSITO (enviar → recibir) | **P2** |
| Proveedores / órdenes de compra avanzadas | **P2** |
| Lotes / vencimientos | **P2** |
| Multi-almacén fino / ubicaciones | **P2** |
| Costo promedio ponderado / rentabilidad | **P2** |
| ERP completo estilo Odoo | **Fuera de alcance** |

---

## Decisiones de modelo (P0, aunque UI venga después)

1. **Una unidad base** por producto fraccionable (ej. ml). Botella / trago / doble = **presentaciones**, no otro saldo paralelo.
2. **Combo ≠ Receta** en lenguaje de producto; mismo mecanismo BOM al descontar stock.
3. **Merma** es un tipo/flujo propio (no solo “ajuste genérico”); UI rica en P1.

Tipos de movimiento conceptuales:

`INITIAL` · `PURCHASE_ENTRY` · `SALE` · `RETURN` · `ADJUSTMENT+` · `ADJUSTMENT-` · `TRANSFER_OUT` · `TRANSFER_IN` · `WASTE`

(Hoy en Core: `adjust` / `reserve` / `release` / `deduct` / `return` — mapear/ampliar en implementación.)

---

## Criterio de hecho P0

Un negocio puede, de punta a punta:

1. Dar de alta un producto (con control de existencia).  
2. Cargar una **entrada** de mercancía.  
3. **Vender** en POS y ver bajar el stock (y alertar si llega al mínimo).  
4. **Ajustar** con motivo y ver el rastro.  
5. Consultar **kardex**.

Sin transferencias, sin OC, sin lotes.

---

## Encaje con lo ya existente en EN1

| Capacidad | Hoy |
|-----------|-----|
| Productos + `tracks_inventory` + min/max + UOM | Sí — BO `/admin/eposone/section/products` |
| Saldos / movimientos básicos / ajuste BO | Sí — `core_stock_*`, sección Inventario |
| `kit` / `pack_factor` | Puente débil — **no** sustituye fraccionable (ml) ni BOM completo |
| Venta POS → deduct oficial | **Pendiente** (Hito 5) |
| Entrada de mercancía como flujo | **Pendiente** |
| Transferencias UI | Deshabilitada |
| Fraccionable / merma / presentaciones | **Diseño P0; implementar por fases** |

Detalle técnico previo: [EN1_EPOSONE_HANDOFF_PRODUCTOS_INVENTARIO.md](EN1_EPOSONE_HANDOFF_PRODUCTOS_INVENTARIO.md).

---

## Navegación objetivo (referencia UX)

```text
INVENTARIO
 ├── Dashboard + “Requieren atención”
 ├── Productos
 ├── Existencias
 ├── Movimientos (entradas, salidas, ajustes, historial)
 └── Alertas (stock bajo, agotados, diferencias)
```

Accesos rápidos sugeridos: `[ Productos ] [ Entradas ] [ Ajustes ] [ Transferir ]`  
(`Transferir` visible según modo; operación completa = P2.)

---

## Próximo paso (implementación)

Requiere **GO** explícito en un chat dedicado, con un slice acotado, por ejemplo:

1. Dominio/API: tipos + unidad base + BOM (sin UI bar), o  
2. P0 operativo: entrada + venta→deduct simple + kardex/alertas.

Hasta ese GO: este documento es la **fuente de alcance P0** para producto.
