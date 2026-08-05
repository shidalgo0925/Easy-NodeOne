# ADR-025 — Operations Control Center (OCC)

| Campo | Valor |
|-------|--------|
| Estado | **Aprobado** — 5 ago 2026 |
| Ámbito | EPosOne (org) · reutilizable en EN1 (multi-org / plataforma) |
| Relación | Amplía [ADR-006](ADR-006-EPOSONE-OPERATION-VS-ADMIN.md) · [ADR-009](ADR-009-EN1-CAJA-CENTRO-COBRO.md) · Order Domain · Sync · Devices · Licensing |
| Handoff | [`EN1_EPOSONE_HANDOFF_STATUS.md`](EN1_EPOSONE_HANDOFF_STATUS.md) |
| Sustituye en UI | Terminología “Reporte X / Reporte Z” como entidades de producto |

---

## Contexto

La conversación de “informes de caja” resolvió un problema mayor que reportes: EPosOne necesitaba un **dominio funcional** de supervisión operativa.

Hasta ahora los dominios explícitos eran Pedidos, Productos, Inventario, Contactos/Clientes, Caja. El gerente, sin embargo, no quiere un PDF “Z”: quiere responder en &lt;10 s:

1. ¿Vendieron lo que debían?
2. ¿Entregaron el dinero correcto?
3. ¿Hay algo que requiera mi atención?

Muchos POS acumulan decenas de “reportes” (una necesidad = una pantalla = otra fórmula). Eso no escala.

## Decisión

### 1. Nuevo dominio: **Control Operacional (Operations Control)**

No es un pack de reportes. Es un **pilar de producto**: superficie operacional tipo **NOC comercial** (Network Operations Center aplicado a retail/F&B).

Preguntas canónicas del OCC:

| NOC telecom | OCC comercio (EPosOne / EN1) |
|-------------|------------------------------|
| ¿Qué está caído? | ¿Qué sucursal/caja tiene problemas? |
| ¿Qué está lento? | ¿Qué dispositivo está offline / sync retrasada? |
| ¿Qué requiere atención? | ¿Turno abierto de más, diferencia, licencia por vencer, impresora caída, ventas sin sync? |

### 2. Principio arquitectónico (obligatorio)

> **El Centro de Control nunca será un conjunto de reportes.**  
> Es una **superficie operacional** construida sobre los dominios del sistema (Caja/Turno, Pedidos, Pagos, Sync, Dispositivos, Cajeros, Licencias, Alertas, y futuros: KDS, Delivery, etc.).

Implicaciones:

- Una **fuente de verdad** por dominio (p. ej. `CoreCashShift` + pagos Order Domain para caja; no recalcular “Z” en paralelo).
- Nuevos canales (KDS, Delivery, Marketplace) agregan **widgets / señales**, no un “Reporte Delivery” suelto.
- Navegación drill-down (Caja → Arqueo → Bitácora → Pedido), **no** PDF tras PDF como flujo principal.

### 3. Nombre de producto

| Usar | No usar |
|------|---------|
| **Operations Control Center** / **Centro de Control de Operaciones** | Cash Shift Center |
| **Operational Views** (perspectivas) | “Reportes X/Z” en UI |
| Estados de turno: **Conciliado** · **Conciliado con observaciones** · **Diferencia pendiente** (semáforo) | Obligar al gerente a interpretar solo números crudos |

### 4. IA de información (un módulo)

```text
Centro de Control (OCC)
├── Hoy              ← dashboard ejecutivo (estado del día)
├── Operación        ← salud global + KPIs de operación
├── Cajas            ← Cierres · Arqueos · Bitácoras (vistas del turno)
├── Pagos            ← conciliación por medio / período
├── Alertas          ← excepciones (solo problemas)
└── Auditoría        ← timeline / evidencia
```

**Caja** sigue siendo dominio de cobro ([ADR-009](ADR-009-EN1-CAJA-CENTRO-COBRO.md)). El OCC **observa** caja (y el resto); no sustituye el módulo de Caja.

**Operational View** sobre un mismo turno (ejemplo): Executive · Audit · Payments · Timeline · Exceptions — mismo `Cash Shift`, distinta perspectiva.

### 5. Alcance del dominio (más que turnos)

El OCC controla la **operación**, no solo arqueos:

- Caja / turnos / diferencias  
- Pedidos (atrasados, cocina, sync pendiente)  
- Pagos / medios  
- Sincronización / offline  
- Dispositivos / impresoras  
- Cajeros  
- Licencias (vencimiento, gracia)  
- Alertas agregadas  

Fase A **no** implementa todos los widgets; el **contrato de dominio** sí los admite.

### 6. EPosOne vs EN1 (misma arquitectura)

| Nivel | OCC agrega |
|-------|------------|
| **EPosOne** | Operación de **una** organización (sucursales / cajas) |
| **EN1** | Operación de **muchas** organizaciones (plataforma) |

Misma idea; cambia el nivel de agregación. No rediseñar el patrón al pasar a multiempresa.

### 7. Roadmap por madurez (no por “pantalla”)

| Fase | Objetivo | Entrega mínima |
|------|----------|----------------|
| **A — Visibilidad** | Ver la operación del día y navegar al detalle | Dashboard Hoy + Cierres (tabla semáforo) + click → Arqueo existente |
| **B — Control** | Enfocarse solo donde hay riesgo | Alertas/Excepciones + Bitácora del turno |
| **C — Inteligencia operacional** | Insights y salud | Medios de pago · Salud operativa · Ranking/Insights |
| **D — Conciliación financiera** | Cerrar el ciclo con dinero real | Depósito/banco · conciliación 4 vías (sistema → operador → físico → banco) |

Jerarquía de atención del gerente: **Hoy → Alertas → Arqueo → Bitácora** (no recorrer todos los cierres si todo está verde).

---

## Consecuencias

**Positivo**

- Vocabulario de producto estable; fin de X/Z como entidades UI.  
- Extensible a KDS/Delivery/eCommerce sin menú de reportes.  
- Reutilizable en EN1 multi-org.  
- Evita lógica duplicada de “reporte vs reality”.

**Riesgos / límites**

- No hervir el océano en Fase A: el dominio es amplio; la **primera vertical** es visibilidad de cierres/caja.  
- Conciliación bancaria (Fase D) requiere **nuevos datos** (depósito/liquidación); no inventar el widget sin captura.  
- Distinguir OCC “Hoy” del dashboard comercial/setup actual de EPosOne (pueden coexistir: Control vs Operación de venta).

**No implica**

- Eliminar el cierre de turno del operador (sigue siendo la vista Arqueo).  
- Reemplazar ADR-009: Caja EN1 sigue siendo el dominio de cobro; OCC lo supervisa.

---

## Criterio de hecho (ADR)

- [x] Dominio OCC nombrado y separado de “reportes”.  
- [x] Principio “OCC ≠ conjunto de reportes” escrito.  
- [x] IA de navegación congelada (Hoy / Operación / Cajas / Pagos / Alertas / Auditoría).  
- [x] Fases A–D por madurez documentadas.  
- [x] Fase A Visibilidad en código (Dev): `/admin/eposone/control` · Hoy + Cierres → Arqueo.  
- [x] Fase B Control en código (Dev): Excepciones (`/control/excepciones`) + Bitácora (`/control/auditoria/<shift_id>`).  
- [x] Fase C Inteligencia en código (Dev): Operación (`/control/operacion`) + Pagos (`/control/pagos`).

---

## Referencias

- [ADR-006 Op vs Admin](ADR-006-EPOSONE-OPERATION-VS-ADMIN.md)  
- [ADR-009 Caja EN1](ADR-009-EN1-CAJA-CENTRO-COBRO.md)  
- [ADR-003 Sync](ADR-003-EPOSONE-SYNC.md)  
- Cierre turno BO: `nodeone/modules/eposone/shift_close_service.py` · dashboard: `nodeone/core/commerce/dashboard.py`
