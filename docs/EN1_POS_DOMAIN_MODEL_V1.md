# Domain Model EN1-POS V1

| Campo | Valor |
|-------|--------|
| Estado | **Borrador Release 0** — 19 jul 2026 |
| Alcance | Lenguaje de **negocio** (no tablas ni endpoints) |
| Rector | [`EN1_POS_CONSTITUCION_V1.md`](EN1_POS_CONSTITUCION_V1.md) |
| Uso | Base objetiva del Gap Analysis y del Backlog |

---

## 1. Propósito

Definir **qué es el negocio** que EN1-POS y EPosOne administran/operan.

Si una feature no mapea a una entidad o relación de este modelo, es ruido o parche.

---

## 2. Cadena operativa principal (Release 1)

```text
Empresa
  → Sucursal
    → POS
      → Caja
        → Dispositivo
        → Turno
          → Pedido
            → Venta
              → Pago(s)
                → Recibo
                  → Factura electrónica (y NC/ND)
                    → Reporte
```

### Significado de cada eslabón

| Entidad | Definición de negocio |
|---------|----------------------|
| **Empresa** | Persona jurídica / negocio que opera con EN1-POS. Tiene moneda, TZ, datos legales y preferencias regionales. |
| **Sucursal** | Lugar físico o lógico de operación bajo la empresa. |
| **POS** | Punto de venta dentro de una sucursal (canal operativo). |
| **Caja** | Unidad de tesorería operativa (register) donde se abren turnos y se consolidan pagos en efectivo/medios. |
| **Dispositivo** | Terminal (tablet/APK) provisionado a una caja/POS. |
| **Turno** | Periodo de responsabilidad de un cajero sobre una caja (apertura → movimientos → cierre). |
| **Pedido** | Intención de consumo/venta en curso (líneas, estados operativos, mesero/cajero, notas). |
| **Venta** | Hecho financiero **cerrado** derivado del pedido (o equivalente). No es el pedido ambiguo: es la operación contable/comercial consolidada. |
| **Pago** | Aplicación de medio(s) de cobro a una venta (1:N, mixto, referencias, propina asociada según política). |
| **Recibo** | Comprobante operativo imprimible/reimprimible con trazabilidad completa de la venta. |
| **Documento fiscal** | Comprobante legal (FE / NC / ND) **relacionado** a la venta, no idéntico a ella. |
| **Reporte** | Vista consolidada auditable de operaciones (ventas, pagos, caja, impuestos, etc.). |

**Regla Panamá:** la cadena comercial no se considera cerrada sin camino a **documento fiscal** (incluye contingencia autorizada).

---

## 2.1 Reglas de cobro multi-dispositivo y propina (congeladas 20 jul 2026)

Aprobadas con Analista — aplicables a Dual Mode (Standalone / Integrado).

### R-PAY-MULTI — Pedido abierto en un device, cobro en otro

> Un pedido puede abrirse en cualquier dispositivo autorizado y **pagarse en cualquier otro** dispositivo autorizado de la misma organización, siempre que el pedido permanezca abierto (no cancelado / no ya pagado). Al registrarse el pago, el estado debe sincronizarse en **todos** los dispositivos: el pedido deja de figurar como abierto, se impiden nuevos cobros y se conserva historial para consulta. **No** deben existir dos pedidos ni exigir cierre manual del mesero.

Implicaciones:

| Situación | Comportamiento |
|-----------|----------------|
| Mesero tablet A crea; cajero tablet B / caja cobra | Mismo `pedido`; B puede cobrar |
| Tras pago, A online | Sync/pull → sale de abiertos; no re-cobrar |
| A offline al cobrar B | Al reconectar: detectar pagado → cerrar local; **nunca** segundo cobro |
| Back Office EN1 cobra | Mismo efecto SoT; devices hacen pull |

Edición de líneas/mesa mientras abierto: sigue Ownership de operación (owner / reglas Hito 3). **Etapa cobro** = excepción multi-device (ya en Order Domain).

### R-TIP-COBRO — Propina es del cobro, no del dispositivo

> La propina forma parte del **proceso de cobro**, no del dispositivo. Cualquier punto autorizado de cobro (tablet mesero, caja, Back Office) puede registrarla o modificarla según el **contrato comercial de propinas** vigente (deshabilitada / sugerida / libre / % fijo). Hay una sola fuente de verdad en el pedido; el recibo usa la propina definitiva al cerrar el cobro.

| Política (contrato) | UI en todo punto de cobro |
|---------------------|---------------------------|
| Deshabilitada | No muestra opción |
| Solo sugerida | Muestra sugerencia; editable/rechazable |
| Libre | Monto libre (con topes de política si existen) |
| % fijo / obligatorio | Calculada; override solo si política lo permite |

Estados útiles: **propina pendiente** vs **propina definida** (antes del cierre financiero). Si la caja cambia la propina al cobrar → actualiza pedido → sync a todos.
---

## 3. Cadena de catálogo e inventario (Release 1 mínimo / Release 2 pleno)

```text
Producto (y organización comercial)
  → Categoría / modificadores / variantes (catálogo)
  → Inventario (existencia por sucursal)
    → Movimiento (kardex)
      → Costo
        → Rentabilidad
```

| Entidad | Definición |
|---------|------------|
| **Producto** | Ítem vendible o insumo (SKU, precio, costo, impuesto aplicable, estado). |
| **Categoría** | Organización comercial del catálogo (no confundir con categoría **fiscal**/ITBMS). |
| **Categoría fiscal** | Clasificación legal de impuesto aplicable a la línea (ej. ITBMS 7/10/15/exento). |
| **Inventario** | Posición de stock por sucursal (disponible, reservado, etc. según madurez). |
| **Movimiento** | Hecho de entrada/salida/ajuste con trazabilidad. |
| **Costo / Rentabilidad** | Derivados de ventas + costos (pleno en R2). |

En **Release 1** el catálogo debe ser administrable desde EN1-POS lo suficiente para vender y fiscalizar; inventario avanzado/compras/rentabilidad = **R2**.

---

## 4. Actores

| Actor | Rol |
|-------|-----|
| **Usuario administrativo EN1** | Configura y audita vía Back Office. |
| **Empleado operativo** | Cajero, mesero, supervisor, cocina, etc. |
| **Cajero** | Empleado con PIN que abre turno y atribuye ventas/pagos. |
| **Cliente** | Comprador; puede tener crédito/fidelización (R2). |
| **Dispositivo** | Actor técnico autenticado en sync/bootstrap. |

---

## 5. Comercial y políticas

| Concepto | Definición |
|----------|------------|
| **Política comercial** | Conjunto versionado de reglas (fiscal, propinas, pagos, recibo, precios, promos…). |
| **Alcance** | Empresa / sucursal / POS / caja (herencia y override). |
| **Vigencia** | Desde/hasta, días, prioridad. |
| **Motor de totales** | Función pura: pedido + políticas → desglose auditable idéntico en APK, EN1, recibo, FE y reportes. |

Documentos V6 (modelo comercial, contratos, motores, ADR-008) son **inputs técnicos** de este dominio; no sustituyen este modelo.

---

## 6. Entidades transversales

| Concepto | Definición |
|----------|------------|
| **Evento** | Hecho de negocio con idempotencia, origen (dispositivo/usuario), timestamps. |
| **Versión de sync** | Marcador por dominio (catálogo, políticas, cajeros…) para bootstrap/pull. |
| **Licencia** | Derecho de uso por caja/dispositivo/módulos/plan. |
| **Auditoría** | Registro de acción sensible (quién, qué, antes/después, cuándo). |
| **Permiso** | Autorización por módulo/sucursal/acción. |

---

## 7. Separaciones críticas (anti-ambigüedad)

| No confundir | Porque |
|--------------|--------|
| **Pedido** vs **Venta** | Pedido es operativo; venta es financiera cerrada. |
| **Recibo** vs **Documento fiscal** | Recibo = operativa; FE = legal. Relacionados, distintos. |
| **Categoría comercial** vs **Categoría fiscal** | Menú/filtro vs ITBMS/legal. |
| **Stock editable** vs **Movimiento** | El número no se “edita”; se mueve con kardex. |
| **Promoción UI** vs **Política publicada** | Código de descuento ≠ motor comercial versionado. |

---

## 8. Dual Mode (mismo dominio)

| Entidad | Standalone | Integrado |
|---------|------------|-----------|
| Maestros (producto, política, cajero…) | Local SoT | EN1 SoT; local réplica |
| Operación (pedido, turno, pago…) | Local + cola | Local + push a EN1 |
| Documento fiscal | Según capacidad local/PAC | Preferente vía EN1 + contingencia |

Ownership detallado: [`EN1_POS_OWNERSHIP_MATRIX_V1.md`](EN1_POS_OWNERSHIP_MATRIX_V1.md).

---

## 9. Fuera de este documento

- DDL, nombres de tabla, rutas HTTP.
- UX de pantallas.
- Algoritmos concretos de ITBMS/propina (contratos V6).

Esos se derivan **después** de congelar dominio + gap + backlog.

---

## 10. Aprobación Domain Model

| Rol | Firma | Fecha |
|-----|-------|-------|
| Prog1 (EN1) | **Aceptado** — Pedido ≠ Venta ≠ Recibo ≠ Documento fiscal · **+ R-PAY-MULTI / R-TIP-COBRO (20 jul)** | 20 jul 2026 |
| Analista | Pendiente | — |
| Prog2 (EPosOne) | Pendiente | — |
