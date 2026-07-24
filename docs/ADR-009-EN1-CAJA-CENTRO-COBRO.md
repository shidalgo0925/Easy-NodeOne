# ADR-009 — Caja EN1 (centro de cobro del ecosistema)

| Campo | Valor |
|-------|--------|
| Estado | **Aprobado** — 20 jul 2026 |
| Ámbito | EN1 (tesorería / cobro administrativo) · canales: BO, EPosOne, Web, API, futuros |
| Relación | Amplía ADR-006 (Op vs Admin) · Domain Model Caja/Turno · R-PAY-MULTI · Hito caja `C-CASH-*` |
| Handoff | [`EN1_EPOSONE_HANDOFF_STATUS.md`](EN1_EPOSONE_HANDOFF_STATUS.md) |
| Backlog | **B-R1-05** (+ subtareas política y reporte cierre) |

---

## Contexto

EN1 recibe (o recibirá) pedidos de varios canales: Back Office, EPosOne, Web, API, WhatsApp, Marketplace, etc. Mezclar “caja = tablet” con tesorería administrativa rompe el dominio y obliga a rediseñar el cobro por cada canal nuevo.

## Decisión

**EN1 posee un módulo de Caja propio**, independiente del canal de venta.

| Concepto | Definición |
|----------|------------|
| **Caja** | Punto de cobro **administrativo** asociado a una **sucursal**, operado por **turnos**. Ej.: Caja Principal, Recepción, Oficina, Tesorería, Caja Online. |
| **Dispositivo** | Cliente (tablet, PC, terminal) que **opera** una Caja. No es la Caja. |
| **Turno** | Única unidad operativa de caja. No existe “cierre del día” como entidad. El reporte diario = **suma de turnos cerrados** en el período. |

### Principios

1. **La Caja pertenece a EN1** y puede recibir pagos de pedidos de cualquier canal **autorizado** por política de empresa.
2. **El origen del pedido no determina dónde se cobra**; la política sí.
3. **Flujo obligatorio del turno:** Abrir → Cobrar → Movimientos → Arqueo → Cerrar.
4. **EPosOne es un canal más**, no el dueño exclusivo de la caja.

### Política entre canales (nueva)

Configuración por empresa:

```text
allow_en1_collect_foreign_channel = Sí | No
```

| Valor | Comportamiento |
|-------|----------------|
| **Sí** (default recomendado) | EN1 (BO / cajas EN1) puede cobrar pedidos originados en otros canales autorizados. El pago queda en el turno de la caja EN1; auditoría indica cobro desde EN1. |
| **No** | Cada canal cobra solo sus propios pedidos; EN1 puede consultar estado pero no cobrar “ajenos”. |

**Alcance V1 del flag (congelado):**

- Aplica a **todos** los canales distintos del Back Office EN1 (EPosOne, Web, API, etc.).
- Ámbito: **misma organización**. Restricción por sucursal = opcional post-V1.
- Lista de canales “autorizados” puede refinarse después; el flag es el interruptor maestro.

### Cierre de turno (contenido mínimo V1)

| Bloque | Contenido |
|--------|-----------|
| **Ventas** | # documentos, brutas, descuentos, impuestos, propinas, reembolsos, netas |
| **Medios de pago** | Efectivo, tarjetas, Yappy, ACH, transferencia, crédito, gift card, otros |
| **Movimientos** | Fondo inicial, entradas, salidas, ajustes, depósitos |
| **Arqueo efectivo** | Esperado · Contado · Diferencia |
| **Conciliación electrónica** | Totales por medio **no efectivo** (no forman parte del dinero contado en cajón) |

**Regla de arqueo:** el `expected` del cajón incluye **solo efectivo** (apertura + movimientos de efectivo ± pagos en efectivo). Medios electrónicos se listan y concilian aparte.

### Relación con código actual

| Ya existe | Pendiente (este ADR) |
|-----------|----------------------|
| `register` org unit + `CoreCashShift` open / reconcile / close | Formalizar setting `allow_en1_collect_foreign_channel` |
| Cobro BO / API Order Domain (de facto multi-origen intra-org) | Respetar el flag en cobro |
| Esperado vs contado básico | Reporte cierre completo + esperado **solo efectivo** + bloque conciliación electrónica |

---

## Consecuencias

- Positivo: un solo módulo de caja para todo el ecosistema; EPosOne no redefine tesorería.
- Positivo: “cierre del día” = agregación de turnos (reportes), sin entidad extra.
- Riesgo: si hay caja física tablet y caja BO en la misma sucursal, deben ser **registers distintos** o el mismo turn consciente; provisioning/política de asignación sigue siendo operativa.
- No implica implementar WhatsApp/Marketplace en V1; solo que el diseño de Caja no los excluye.

## No-goals V1

Denominaciones, X/Z fiscal, reapertura de turno, marketplace real, WhatsApp real.

---

## Changelog

- **2026-07-20:** Aprobado — decisión arquitectura Caja EN1 + política + cierre turno mínimo.
