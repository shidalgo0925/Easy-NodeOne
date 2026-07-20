# EN1-POS V7 — Roadmap de producto

| Campo | Valor |
|-------|--------|
| Estado | **Activo** — R0 (Prog1 OK) + **R1 iniciado (B-R1-01)** · actualizado **19 jul 2026** |
| Sucede a | V6 ([`EN1_PLATFORM_EPOSONE_V6_ROADMAP.md`](EN1_PLATFORM_EPOSONE_V6_ROADMAP.md)) como **plan de producto** |
| Rector | [`EN1_POS_CONSTITUCION_V1.md`](EN1_POS_CONSTITUCION_V1.md) |
| Backlog | [`EN1_POS_BACKLOG_V7.md`](EN1_POS_BACKLOG_V7.md) |
| Handoff | [`EN1_EPOSONE_HANDOFF_STATUS.md`](EN1_EPOSONE_HANDOFF_STATUS.md) |

V6 permanece como **paquete de contratos comerciales** (inputs). V7 es la **planificación de producto** y el criterio de cierre.

---

## Estado actual (19 jul 2026)

| Bloque | Estado |
|--------|--------|
| **Release 0** docs | Creados + en `develop` · **Prog1 firmó** · faltan **Analista + Prog2** (+ T1 propinas) |
| **V6 infra** | Policy engine + seed ITBMS + stub motor totales · en `develop` |
| **B-R1-01** Núcleo Empresa→Caja | **Avance** (no DoD completo): panel Empresa, edit/deact. sucursal/caja, jerarquía |
| Cadena R1 resto | Pendiente (device → … → FE → sync → reporte) |
| Prog2 paralelo | Hito 4 cajeros/sync (sin dominio nuevo) |

**Nota:** R0 formal sigue abierto (faltan 2 firmas). Prog1 avanzó B-R1-01 por **GO del owner** para no frenar el núcleo admin.

### Commits relevantes (develop)

| Commit | Contenido |
|--------|-----------|
| `6b40f53` | Infra políticas comerciales + ITBMS catálogo + cobro BO |
| `b98925e` | Release 0 EN1-POS V7 (paquete docs) |
| `502d285` | Firma Prog1 R0 + Gap endurecido |
| `4205f08` | B-R1-01 Empresa BO + edit/deact. + jerarquía |

---

## Paquete Release 0

| # | Documento | Estado |
|---|-----------|--------|
| 1 | [Constitución EN1-POS V1](EN1_POS_CONSTITUCION_V1.md) | Borrador · **Prog1 OK** · falta A+P2 |
| 2 | [Domain Model V1](EN1_POS_DOMAIN_MODEL_V1.md) | Borrador · **Prog1 OK** · falta A+P2 |
| 3 | [Ownership Matrix V1](EN1_POS_OWNERSHIP_MATRIX_V1.md) | Borrador · **Prog1 OK** · falta A+P2 |
| 4 | [Definition of Done V1](EN1_POS_DEFINITION_OF_DONE_V1.md) | Borrador · **Prog1 OK** · falta A+P2 |
| 5 | [Gap Analysis — capacidades](EN1_POS_CAPABILITY_GAP_V7.md) | **B-R0-05 Done Prog1** (0 Completa) |
| 6 | [Backlog único](EN1_POS_BACKLOG_V7.md) | Activo · R1 priorizado |
| 7 | [Arquitectura V7](EN1_POS_ARQUITECTURA_V7.md) | Borrador · **Prog1 OK** · falta A+P2 |

**Cierre R0 formal:** firmas Analista + Prog2 + B-R0-08 (T1 propinas).

---

## Visión (resumen)

| Pieza | Rol |
|-------|-----|
| **EPosOne** | Operación offline-first |
| **EN1-POS** | Back Office completo |
| **Standalone / Integrado / Vincular** | Dual Mode + cutover sin reinstalar |

Referencia funcional: cobertura tipo Loyverse — **no** copia pantalla a pantalla; superioridad en Dual Mode, FE Panamá, políticas versionadas, CxC (R2), SaaS.

---

## Releases

### Release 0 — Constitución

Docs rector + Domain + Ownership + Gap + Backlog + DoD + Arquitectura.

### Release 1 — Cadena operativa comercial (incluye FE)

```text
Núcleo admin → Empleados/cajeros → Catálogo mínimo → Motor totales
→ Pedido → Venta → Pago → Recibo → FE + NC → Sync → Reporte
(+ licencia, obs básica, Vincular)
```

| Ítem | Estado |
|------|--------|
| B-R1-01 Empresa→Sucursal→POS→Caja | **En curso / avance** |
| B-R1-02 … B-R1-19 | Pendiente |

**No** abrir inventario avanzado / compras / fidelización hasta cerrar la cadena (DoD).

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
| **Analista** | Firmar R0; resolver **T1 propinas** (B-R0-08); mapear V6 → motor R1 |
| **Prog2** | Firmar R0 (Ownership/Arquitectura); Hito 4 cajeros/sync E2E |
| **Prog1** | Cerrar DoD B-R1-01 (checklist E2E) o seguir **B-R1-02** dispositivos según GO |

---

## Índice rápido

- Constitución → Domain → Ownership → DoD → Gap → Backlog → Arquitectura  
- Contratos V6: fiscal, propinas, pagos, recibo, motores, ADR-008  
- Histórico: V4, V5, ADR-001…007
