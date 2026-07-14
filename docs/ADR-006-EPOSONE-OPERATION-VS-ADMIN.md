# ADR-006 — Operación (EPosOne) vs Administración (EN1)

| Campo | Valor |
|-------|--------|
| Estado | **Aprobado** — 14 jul 2026 |
| Ámbito | EN1 (P1) + EPosOne APK (P2) |
| Relación | Amplía ADR-001…003; no rompe una sola APK / un solo dominio |
| Handoff | [`EN1_EPOSONE_HANDOFF_STATUS.md`](EN1_EPOSONE_HANDOFF_STATUS.md) |
| Hito 3 | [`EN1_EPOSONE_HITO3_ORDER_LIFECYCLE.md`](EN1_EPOSONE_HITO3_ORDER_LIFECYCLE.md) · spec [`EN1_EPOSONE_HITO3_SPEC_FUNCIONAL_V1.md`](EN1_EPOSONE_HITO3_SPEC_FUNCIONAL_V1.md) (**en diseño**) |

---

## Decisión

La diferencia entre un micro negocio y una cadena **no** es un producto distinto (no hay EPosOne Lite / Pro).  
Es **cómo se usa** el mismo EPosOne + el mismo EN1.

| Producto | Rol |
|----------|-----|
| **EPosOne** | Sistema de **operación** (ejecución): vende, cobra, opera offline |
| **EN1** | Sistema de **administración** (gestión): fuente oficial, control, auditoría |

Principio: **operación vs administración**, no “POS vs BackOffice” como productos separados.

---

## Escenarios soportados (obligatorio)

| Escenario | Ejemplos | Cómo se administra |
|-----------|----------|--------------------|
| **1 — Solo POS** | Food truck, kiosco, tienda de barrio | Administración **básica** desde la tablet (no hay PC) |
| **2 — POS + BackOffice** | Restaurante, mini súper, farmacia | Admin en EN1; POS solo opera |
| **3 — Multi sucursal** | Cadenas, hoteles, franquicias | Todo admin en EN1; POS casi sin admin |

---

## Responsabilidades

### EPosOne (operación)

Incluye:

- Pedidos, ventas, cobros, caja, impresión  
- Clientes (consulta + alta rápida)  
- Consulta de productos y disponibilidad básica  
- Offline-first + cola de sincronización  
- Eventos de negocio hacia EN1  

**No** es un mini-ERP estándar del cajero. En escenarios corporativos no ofrece pantallas de:

- Crear bodegas, conteos, OC, transferencias  
- Costos, Kardex, lotes, vencimientos  
- Ajustes de inventario como trabajo diario del operador  

### EN1 (administración)

Fuente oficial de:

- Productos, categorías, bodegas  
- Inventario, ajustes, conteos, transferencias, compras/recepciones  
- Kardex, stock min/max, proveedores, costos  
- Configuración, reportes, auditoría  

### Excepción — Administración básica (Solo POS)

Cuando la org opera solo con tablet, EPosOne permite un conjunto **mínimo**, etiquetado como administración básica:

- Crear / editar producto  
- Cambiar precio  
- Ver existencias  
- Ajuste rápido de inventario (con motivo)  
- Alta rápida de clientes  

Toda modificación es un **evento**; EN1 es quien materializa Kardex/stock oficial al sincronizar.  
El POS **nunca escribe tablas de inventario de EN1** directamente.

---

## Inventario — flujo oficial

```text
POS cobra / ajusta (evento)
  → cola sync (si offline)
  → EN1 interpreta evento
  → EN1 descuenta / ajusta stock
  → EN1 crea Kardex
  → EN1 publica stock actualizado (bootstrap / sync down)
```

- Inventario oficial = **siempre EN1**.  
- POS consulta stock solo como **referencia para vender**.  
- “Ajuste rápido” deshabilitado por defecto en modos corporativos; con autorización + auditoría en EN1.

---

## Capacidades (no dos APKs)

Una sola APK. Las funciones se habilitan por:

1. **Modo de organización** (config EN1 / setup inicial), y  
2. **Nivel del usuario** en el POS.

### Modos de organización (EN1)

| Modo | Efecto |
|------|--------|
| **Solo POS** | Admin básica habilitada en tablet |
| **POS + BackOffice** | Admin en EN1; POS enfocado a operación |
| **Corporativo** | Admin en EN1; POS casi solo vender |

### Niveles en POS (referencia)

| Función | Operador | Encargado | Administrador |
|---------|----------|-----------|---------------|
| Vender / cobrar | ✅ | ✅ | ✅ |
| Abrir/cerrar caja | ✅ | ✅ | ✅ |
| Crear productos / precios | ❌ | ✅\* | ✅\* |
| Ajuste rápido inventario | ❌ | ✅\* | ✅\* |
| Conteo / transferencias / compras | ❌ | ❌ | ✅\*\* |
| Config del negocio | ❌ | ❌ | ✅\* |

\* Solo si el **modo de org** lo permite (p. ej. Solo POS).  
\*\* Preferible en EN1; en POS solo si modo Solo POS y política lo permite. Conteo/OC/transferencias **no** son Hito 3.

Detalle de flags/UI: fuera de Hito 3 — se define al abrir el hito de capacidades.

---

## Pedido = entidad principal

Todo inicia con un **Pedido**. Ventas, inventario, caja y FE son **consecuencias**.

- El usuario ejecuta **acciones**; el sistema cambia **estados internos**.  
- No hay pantallas de “editar estado” manual.

| Acción | Estado generado (ejemplo) |
|--------|---------------------------|
| Crear pedido | Borrador |
| Enviar | En preparación |
| Marcar listo | Listo |
| Entregar | Entregado |
| Cobrar | Cobrado |
| Anular | Anulado |
| Devolver | Devuelto |

### Cancelaciones (tres escenarios)

| Momento | Tratamiento |
|---------|-------------|
| Antes de preparación | Modificación del pedido; sin movimiento inventario; sin auth especial |
| Después de preparación | Anulación; motivo + usuario + fecha/hora; auth según política |
| Después de entrega | Devolución; puede → nota crédito / ajuste / merma según tipo de producto |

### Sync = ciclo de vida del Pedido (no solo “venta”)

Eventos (mínimo conceptual):

`pedido.creado` · ítem agregado/eliminado/cantidad · `pedido.enviado` · `pedido.listo` · `pedido.entregado` · `pedido.cobrado` · `pedido.anulado` · `pedido.devuelto`

EN1 mantiene historial completo. Un pedido puede crearse en un POS y continuar/cobrarse en otro POS o en BackOffice.

---

## Roadmap — qué implica

| Hito | Contenido |
|------|-----------|
| **1** Provisioning | ✅ Cerrado / congelado |
| **2** Bootstrap | 🟡 Cerrar E2E APK (`/api/v1/devices/bootstrap`) |
| **3** Operación del Pedido | Ciclo de vida + sync bidireccional (reemplaza “Ventas → Stock” como siguiente) |
| **4+** | Inventario operativo por eventos, caja avanzada, FE, analítica |

**No** implementar todavía: inventario operativo completo, FE, transferencias, compras, CRM, IA.

---

## Consecuencias

### Positivas

- Food truck y cadena con **una** APK  
- Lógica de inventario / Kardex **no** duplicada en el POS  
- Auditoría y permisos concentrados en EN1  
- Offline-first natural vía cola de eventos  

### Negativas / costos

- Hito 3 es más amplio que “descontar stock al cobrar”  
- Hay que diseñar contrato de eventos y modos de org (después de cerrar Hito 2)  
- Admin básica en POS requiere UX cuidadosa para no convertirse en ERP  

### Rechazado

- Dos productos (Lite / Pro)  
- Que el POS escriba tablas de inventario EN1  
- Que el cajero gestione Kardex / conteos / OC como pantallas estándar  
- Siguiente hito = solo “ventas → stock” sin dominio de Pedido  

---

## Instrucciones inmediatas

Ver [`EN1_EPOSONE_HITO3_ORDER_LIFECYCLE.md`](EN1_EPOSONE_HITO3_ORDER_LIFECYCLE.md) — P1 y P2.

Hasta cerrar Hito 2 E2E: **no** abrir código de Hito 3 sin GO + contrato firmado.
