# EN1-POS V7 — Roadmap de producto

| Campo | Valor |
|-------|--------|
| Estado | **Activo — Release 0** · 19 jul 2026 |
| Sucede a | V6 ([`EN1_PLATFORM_EPOSONE_V6_ROADMAP.md`](EN1_PLATFORM_EPOSONE_V6_ROADMAP.md)) como **plan de producto** |
| Rector | [`EN1_POS_CONSTITUCION_V1.md`](EN1_POS_CONSTITUCION_V1.md) |
| Handoff | [`EN1_EPOSONE_HANDOFF_STATUS.md`](EN1_EPOSONE_HANDOFF_STATUS.md) |

V6 permanece como **paquete de contratos comerciales** (inputs). V7 es la **planificación de producto** y el criterio de cierre.

---

## Paquete Release 0 (sin código de features)

| # | Documento | Estado |
|---|-----------|--------|
| 1 | [Constitución EN1-POS V1](EN1_POS_CONSTITUCION_V1.md) | Borrador · **Prog1 OK** |
| 2 | [Domain Model V1](EN1_POS_DOMAIN_MODEL_V1.md) | Borrador · **Prog1 OK** |
| 3 | [Ownership Matrix V1](EN1_POS_OWNERSHIP_MATRIX_V1.md) | Borrador · **Prog1 OK** |
| 4 | [Definition of Done V1](EN1_POS_DEFINITION_OF_DONE_V1.md) | Borrador · **Prog1 OK** |
| 5 | [Gap Analysis — capacidades](EN1_POS_CAPABILITY_GAP_V7.md) | **Prog1 revisado (B-R0-05 Done)** |
| 6 | [Backlog único](EN1_POS_BACKLOG_V7.md) | Borrador · orden R1 respaldado por Prog1 |
| 7 | [Arquitectura V7](EN1_POS_ARQUITECTURA_V7.md) | Borrador · **Prog1 OK** |

**Cierre R0:** faltan firmas **Analista + Prog2** (+ T1 / B-R0-08). Después recién código R1.

---

## Visión (resumen)

| Pieza | Rol |
|-------|-----|
| **EPosOne** | Operación offline-first |
| **EN1-POS** | Back Office completo |
| **Standalone / Integrado / Vincular** | Dual Mode + cutover sin reinstalar |

Referencia funcional externa: cobertura tipo Loyverse — **no** copia pantalla a pantalla; superioridad en Dual Mode, FE Panamá, políticas versionadas, CxC (R2), SaaS.

---

## Releases

### Release 0 — Constitución

Constitución · Domain Model · Ownership · Gap · Backlog · DoD · Arquitectura.

### Release 1 — Backend/BO comercial funcional (cadena cerrada)

Incluye **obligatoriamente** Facturación Electrónica (ajuste Analista 19 jul):

```text
Núcleo admin → Empleados/cajeros → Catálogo mínimo → Motor totales
→ Pedido → Venta → Pago → Recibo → FE + NC → Sync → Reporte
(+ licencia, obs básica, Vincular)
```

**No** abrir inventario avanzado / compras / fidelización hasta cerrar esta cadena (DoD).

### Release 2 — Control del negocio

Inventario pleno · compras/proveedores · costos/rentabilidad · crédito · fidelización · reportes gerenciales.

### Release 3 — Restaurante y ecosistema

KDS · mesas/canales · QR · APIs públicas · integraciones · marketplace.

---

## Regla de oro

> No se considera funcionalidad terminada por tener tabla, endpoint o pantalla.  
> Solo DoD completo → **Completa**.

---

## Distribución inmediata

| Rol | Acción |
|-----|--------|
| **Analista** | Aprobar paquete R0; resolver T1 propinas / mapear V6 → B-R1-08 |
| **Prog1** | No features nuevas hasta R0 aprobado; preparar B-R1-01+ según backlog |
| **Prog2** | Hito 4 cajeros/sync E2E; no inventar dominio; preparar paridad motor |

---

## Índice rápido

- Constitución → Domain → Ownership → DoD → Gap → Backlog → Arquitectura  
- Contratos V6: fiscal, propinas, pagos, recibo, motores, ADR-008  
- Histórico: V4, V5, ADR-001…007
