# Definition of Done — EN1-POS V1

| Campo | Valor |
|-------|--------|
| Estado | **Borrador Release 0** — 19 jul 2026 |
| Rector | [`EN1_POS_CONSTITUCION_V1.md`](EN1_POS_CONSTITUCION_V1.md) |
| Uso | Clasificar capacidades en Gap Analysis y cerrar ítems de Backlog |

---

## 1. Principio

Una capacidad **no** está **Completa** porque exista:

- una tabla,
- un endpoint,
- una pantalla,
- un stub,
- un documento borrador.

Está **Completa** solo si cumple **todos** los puntos del checklist. Si falta **uno** → estado máximo **Parcial**.

---

## 2. Checklist obligatorio (11 puntos)

| # | Dimensión | Criterio mínimo |
|---|-----------|-----------------|
| 1 | **Dominio** | Entidad/relación nombrada en Domain Model; sin ambigüedad (ej. pedido ≠ venta). |
| 2 | **Persistencia** | Datos durables en SoT del modo (PG en EN1 Integrado; local en Standalone). |
| 3 | **API** | Contrato HTTP/sync estable, errores, idempotencia donde aplique. |
| 4 | **Back Office** | Pantalla o flujo EN1-POS usable para administrar/consultar lo que el dominio exige. |
| 5 | **Flutter (EPosOne)** | Flujo operativo en APK cuando la capacidad es de ejecución (o N/A documentado si es solo admin). |
| 6 | **Sync** | Bootstrap y/o push/pull según Ownership; versiones; reintento; resultado observable. |
| 7 | **Permisos** | Quién puede hacer la acción (rol/módulo/sucursal/caja según aplique). |
| 8 | **Auditoría** | Acción sensible deja rastro (actor, entidad, antes/después o evento equivalente). |
| 9 | **Reportes** | La capacidad es visible en reporte operativo mínimo **o** N/A explícito con justificación. |
| 10 | **Pruebas E2E** | Al menos un camino automatizado o checklist E2E firmado (EN1↔APK) que demuestre la capacidad. |
| 11 | **Documentación** | Contrato/ADR/sección de handoff actualizado; no “solo está en el código”. |

**N/A permitido** solo si está escrito en el ítem del backlog (ej. “solo Back Office, sin Flutter”).

---

## 3. Estados de capacidad (Gap / Backlog)

| Estado | Significado |
|--------|-------------|
| **Completa** | DoD 11/11 (o N/A justificados). |
| **Parcial** | Existe avance real pero falta ≥1 dimensión DoD. |
| **Stub** | Scaffold / `not_implemented` / UI sin lógica / política sin motor. |
| **Inexistente** | No hay implementación usable. |
| **Duplicada** | Dos caminos que hacen lo mismo sin owner único. |
| **Requiere rediseño** | Existe pero viola Domain Model / Ownership / Constitución. |

---

## 4. Definición de “cadena cerrada” (Release 1)

La cadena R1 se declara cerrada solo cuando **cada eslabón** de:

```text
Empresa → … → Turno → Pedido → Venta → Pago → Recibo → FE → Sync → Reporte
```

está **Completa** (DoD) o tiene excepción aprobada por Analista/Producto por escrito.

No basta con “el pedido se cobra”.

---

## 5. Anti-patrones (rechazo de cierre)

- “Listo en EN1, pendiente APK” sin marcar **Parcial**.
- Motor de totales distinto en UI vs backend vs recibo.
- FE “después” sin contingencia ni entidad documento fiscal.
- Inventario como número editable sin movimiento.
- Promociones de pantalla sin política versionada.

---

## 6. Plantilla de cierre (copiar en PR / handoff)

```text
Capacidad: …
Dominio: ✅/❌
Persistencia: ✅/❌
API: ✅/❌
Back Office: ✅/❌
Flutter: ✅/❌/N/A
Sync: ✅/❌/N/A
Permisos: ✅/❌
Auditoría: ✅/❌
Reportes: ✅/❌/N/A
E2E: ✅/❌
Documentación: ✅/❌
Estado final: Completa | Parcial
```

---

## 7. Aprobación DoD

| Rol | Firma | Fecha |
|-----|-------|-------|
| Prog1 (EN1) | **Aceptado** — 11 puntos son el único criterio de Completa en R1 | 19 jul 2026 |
| Analista | Pendiente | — |
| Prog2 (EPosOne) | Pendiente | — |
