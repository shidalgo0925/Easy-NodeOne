# ADR-020 — Propiedad operacional de eventos de pedido (EPosOne ↔ EN1)

| Campo | Valor |
|-------|--------|
| ID | ADR-020 |
| Título | Propiedad de Order Events: quién puede mutar un pedido |
| Estado | **Aprobado (instrucción)** — 28 jul 2026 · dominio documental; gaps de código = backlog |
| Ámbito | EPosOne (operación / Offline First) · EN1 (administración) · sync bidireccional |
| Relacionados | [ADR-006](ADR-006-EPOSONE-OPERATION-VS-ADMIN.md) · [ADR-003](ADR-003-EPOSONE-SYNC.md) · [Order Domain Spec v1](EN1_EPOSONE_ORDER_DOMAIN_SPEC_V1.md) · [Hito 3 Lifecycle](EN1_EPOSONE_HITO3_ORDER_LIFECYCLE.md) · [ADR-019](ADR-019-ADMINISTRATIVE-HIERARCHY.md) |
| Código hoy | `EposoneOrder` / `EposoneOrderEvent` · `eposone/order_domain.py` · sync Sprint 7 |
| No sustituye | Order Domain Spec v1.0 (**CONGELADA**) como SoT de entidades/estados; este ADR es SoT de **quién escribe y cómo** |

---

## Pregunta rectora

> **¿Quién puede modificar un pedido entre EPosOne y EN1, sin conflictos, sin borrado histórico y con una sola trazabilidad de auditoría (Offline First + Event Driven)?**

---

## Decisión

1. **El pedido no se elimina** una vez sale de borrador operativo.  
2. **EPosOne es dueño de la operación** mientras el pedido esté activo en el flujo POS.  
3. **EN1 es dueño de la administración** (BO, auditoría, reportes, fiscal, integraciones).  
4. Toda mutación de estado/negocio ocurre **solo vía Order Event** — nunca escribiendo “a mano” la BD del POS ni el pedido en EN1 sin evento.  
5. Sync **bidireccional** con el **mismo contrato** de eventos.

```text
                    ┌─────────────────────┐
                    │   Order (histórico) │
                    │   append-only events│
                    └──────────┬──────────┘
                               │
           ┌───────────────────┼───────────────────┐
           ▼                                       ▼
   EPosOne (operación)                      EN1 (administración)
   Owner mientras activo en POS             Acciones admin vía eventos
           │                                       │
           └──────── Event + Sync ─────────────────┘
```

---

## 1. Inmutabilidad histórica — no eliminar

| Estado | Eliminar físico / hard-delete | Acciones permitidas |
|--------|-------------------------------|---------------------|
| **DRAFT** (borrador local / no confirmado) | Permitido solo si política local lo admite (sin impacto fiscal/sync oficial) | Editar, confirmar, descartar borrador |
| **CONFIRMED** y posteriores | **Prohibido** | Cancelar · Reabrir (si política) · Reembolsar · Nota de crédito (**futuro**) |

Toda acción post-confirmación **conserva trazabilidad** (Order Event + entidades de anulación/devolución según Order Domain Spec).

**Prohibido:** `DELETE` de pedido confirmado, “vaciar” historial de eventos, o reescribir eventos pasados.

---

## 2. EPosOne = dueño de la operación

Mientras el pedido pertenece al flujo operativo del POS (sesión activa / owner device-pos según Order Domain §3):

EPosOne **puede** originar:

| Acción | Notas |
|--------|--------|
| Crear pedido | → evento creación |
| Editar DRAFT | líneas / metadatos |
| Confirmar | fin de borrador operativo |
| Agregar / quitar productos | según política de estado |
| Cancelar | operativa |
| Cobrar / abonar | pagos |
| Reembolsar | operativo (si política) |
| Cerrar / completar | cierre de ciclo |

Cada acción genera un **Order Event local** y luego se sincroniza hacia EN1.

### Orígenes de escritura operativa

```text
Tablet / POS
  → acción de negocio
  → OrderEvent (origin = EPOSONE)
  → cola sync
  → EN1 aplica / proyecta
```

---

## 3. EN1 = dueño de la administración

EN1 **no** modifica directamente un pedido que está siendo operado activamente por una tablet (owner = POS).

Función de EN1 respecto al pedido:

- Back Office (consulta, listados, detalle de solo lectura operativa)
- Auditoría y timeline de eventos
- Reportes / BI / CRM
- Facturación e integraciones
- Gestión administrativa (políticas, correcciones autorizadas)

**Prohibido en EN1:** editar líneas de un pedido activo en POS “como si fuera el cajero”, o `UPDATE`/`DELETE` directo sobre tablas POS/locales.

---

## 4. Acciones administrativas desde EN1

Sí pueden **originarse en EN1** (con autorización / RBAC / motivo):

| Acción admin | Ejemplo |
|--------------|---------|
| Cancelación administrativa | Pedido trabado, fraude, error de caja |
| Reembolso administrativo | Post-cierre autorizado |
| Corrección autorizada | Ajuste con motivo + actor |
| Nota de crédito | **Futuro** |

Flujo obligatorio:

```text
EN1 (UI/API admin)
  → genera OrderEvent (origin = EN1)
  → sync hacia dispositivo(s) / proyección
  → EPosOne recibe evento
  → actualiza estado local
```

**Nunca** se modifica directamente la base de datos del POS.  
**Siempre** mediante eventos del contrato compartido.

---

## 5. Sincronización bidireccional

```text
EPosOne → EN1
  Pedido / acción
    → OrderEvent
    → Sync
    → EN1 (fuente oficial proyectada)

EN1 → EPosOne
  Acción administrativa
    → OrderEvent
    → Sync
    → EPosOne (estado local)
```

Reglas:

- Mismo **contrato** de eventos en ambos sentidos.  
- Idempotencia por `event_id` (org-scoped).  
- Orden causal / `sequence` según diseño EN1 (Order Domain).  
- Conflictos de edición concurrente: **no merge de líneas**; gana ownership (Order Domain §3).

---

## 6. Dominio Order Events

El dominio **ya existe** en EN1 (`EposoneOrderEvent` / Order Domain Spec §4). Este ADR fija el contrato operacional y los campos de gobernanza.

### Campos mínimos (contrato)

| Campo | Rol |
|-------|-----|
| `event_id` | Idempotencia |
| `order_id` | Pedido |
| `organization_id` | Tenant |
| `event_type` / `type` | Tipo de evento |
| `created_by` / `actor_user_ref` | Actor |
| `created_at` / `occurred_at` | Tiempo |
| `origin` | `EPOSONE` \| `EN1` \| `SYSTEM` |
| `reason` | Motivo (obligatorio en admin / cancel / refund) |
| `payload` | JSON del cambio |
| `sync_status` | Pendiente / enviado / aplicado / error (backlog si aún no modelado) |

### `origin`

| Valor | Quién emite |
|-------|-------------|
| `EPOSONE` | Tablet / operación POS |
| `EN1` | Acción administrativa en plataforma |
| `SYSTEM` | Jobs, políticas automáticas, reparaciones controladas |

### `event_type` — alias canónicos (ADR) ↔ nombres Order Domain

| Alias operacional (ADR-020) | Tipo Order Domain Spec (SoT v1) |
|-----------------------------|--------------------------------|
| `ORDER_CREATED` | `pedido.creado` |
| `ORDER_UPDATED` | `pedido.actualizado` (+ ítems vía eventos de línea si aplica) |
| `ORDER_CONFIRMED` | Confirmación operativa (mapear al evento de envío/confirmación vigente en spec) |
| `ORDER_CANCELLED` | `pedido.anulado` |
| `ORDER_PAID` | `pedido.cobrado` |
| `ORDER_REFUNDED` | reembolso / `pedido.devuelto` según semántica |
| `ORDER_COMPLETED` | cierre / `pedido.entregado` + cierre financiero según ciclo |

Implementaciones nuevas deben **emitir el tipo del Order Domain Spec** y pueden aceptar el alias ADR en APIs internas con normalización.

---

## 7. Regla de propiedad (Owner)

| Situación | Owner | Quién escribe acciones operativas |
|-----------|--------|-----------------------------------|
| Pedido activo en sesión POS | **EPosOne** (device/pos owner) | Solo la tablet/POS dueño (otros: lectura) |
| Cobro autorizado desde otra caja/BO | Según Order Domain §3 (cobro puede ser otro POS/BO autorizado) | Acción + evento; no “robar” edición de líneas |
| Intervención EN1 | Sigue siendo proyección admin | **Solo** Order Event `origin=EN1` |

Mientras `Owner = EPosOne` para un pedido abierto:

- Acciones operativas → tablet.  
- EN1 → lectura + acciones admin vía eventos (nunca mutación directa).

---

## 8. Auditoría obligatoria

Todo cambio debe conservar, cuando aplique:

| Dato | Campo típico |
|------|----------------|
| Usuario | `actor_user_ref` / `created_by` |
| Organización | `organization_id` |
| Caja | `register_ref` (en pedido / payload) |
| Dispositivo | `actor_device_uuid` |
| Turno | payload / sesión de caja |
| Fecha/hora | `occurred_at` |
| Motivo | `reason` |
| Origen | `origin` (`EPOSONE` / `EN1` / `SYSTEM`) |

**No deben existir** operaciones que muten un pedido sin generar Order Event de auditoría.

---

## Consecuencias

### Positivas

- Pedido **inmutable** en sentido histórico.  
- Sin eliminación física post-confirmación.  
- Sin carrera EPosOne ↔ EN1 sobre las mismas filas.  
- Sync Event Driven alineado Offline First.  
- Auditoría completa y reconstruible.

### Costos / backlog

| Gap | Acción |
|-----|--------|
| UI EN1 que aún edite pedido “directo” | Cerrar o redirigir a flujo de eventos admin |
| Campos `origin` / `reason` / `sync_status` incompletos en modelo | Extender `EposoneOrderEvent` + migración Dev |
| Alias `ORDER_*` vs `pedido.*` | Capa de normalización documentada; no duplicar semántica |
| Soft-delete / ocultar DRAFT | Política explícita en Order Domain v1.1 si hace falta |
| Nota de crédito | Fuera de v1; evento futuro |

### Relación con ADR-006

ADR-006 define **operación vs administración** a nivel producto.  
ADR-020 fija **cómo se muta el Pedido** entre ambos lados: solo eventos, con ownership claro.

---

## Resultado esperado (DoD documental)

- [x] Dueño operativo = EPosOne mientras el pedido esté activo en POS.  
- [x] Dueño administrativo = EN1 vía Order Events.  
- [x] Prohibición de delete post-confirmación.  
- [x] Sync bidireccional bajo el mismo contrato.  
- [x] Auditoría mínima definida.  
- [ ] Código / APIs / UI EN1 alineados (backlog con GO de implementación).

---

## Referencias de implementación (Dev)

| Pieza | Ubicación |
|-------|-----------|
| Modelo | `backend/models/eposone_order.py` (`EposoneOrderEvent`) |
| Dominio | `backend/nodeone/modules/eposone/order_domain.py` |
| Schema | `backend/nodeone/services/eposone_order_schema.py` |
| Spec entidades | [`EN1_EPOSONE_ORDER_DOMAIN_SPEC_V1.md`](EN1_EPOSONE_ORDER_DOMAIN_SPEC_V1.md) |

---

*Si hay conflicto entre este ADR y la Order Domain Spec v1.0 congelada en nombres de `type` o estados, prevalece la Spec para el contrato Hito 3; este ADR prevalece para **ownership y canal de mutación** (eventos, no writes directos).*
