# ADR-016 — Licenciamiento Comercial V2: Producto → Suscripción → Entitlement

| Campo | Valor |
|-------|-------|
| ID | ADR-016 |
| Título | Licenciamiento Comercial V2 — Organization Product Entitlement |
| Estado | **Aprobado (GO)** — 27 jul 2026 |
| Ámbito | EN1 Platform · EPosOne · Membership · Educación · ePayroll · cualquier producto futuro |
| Enmienda UX/estados | [ADR-028](ADR-028-EPOSONE-PLAN-DEFAULTS-COMMERCIAL-OVERRIDES.md) — plan=defaults · overrides auditados · `/start` sin precio · `PENDING` vs `TRIAL` (6 ago 2026) |
| Enmienda dominio | **[ADR-031](ADR-031-EN1-COMMERCIAL-DOMAIN-ARCHITECTURE.md)** (7 ago 2026) — Cliente/Contrato encima; Suscripción bajo Contrato |
| Relacionados | [ADR-005](ADR-005-EPOSONE-LICENSING-POS.md) · [ADR-007](ADR-007-EPOSONE-COMMERCIAL-LICENSING-OFFLINE.md) · [ADR-008](ADR-008-EPOSONE-COMMERCIAL-ENGINE.md) · [ADR-014](ADR-014-SUBSCRIPTION-REGISTRY.md) · [ADR-022](ADR-022-EN1-MULTIPRODUCT-COMMERCIAL-MODEL.md) |
| Precedencia | Reemplaza la **unidad comercial** de ADR-005 (POS) y ADR-007 (Caja). Preserva ADR-007 offline/sync. **ADR-031 prevalece** sobre “Organización como raíz” de ADR-022. |
| Alcance | Decisión arquitectónica y modelo conceptual. **No** implementa facturación, Marketplace ni renovación automática con cobro. |

---

## Enmienda ADR-031 (7 ago 2026)

Jerarquía canónica:

```text
Cliente → Organización (empresa) → Contrato → Suscripción → Entitlement/Licencia → Implementación (fase posterior)
```

**Sigue válido:** se compra derecho de producto (no APK/caja/POS); capas Producto / Suscripción / Entitlement / Recursos; overrides (ADR-028).

---

## Pregunta rectora

> **¿Qué compra realmente un cliente cuando adquiere EPosOne?**

No compra una APK, ni una tablet, ni una caja, ni un POS.

**Compra el derecho de utilizar un producto de la plataforma EN1, bajo un plan, durante una vigencia, con capacidades y límites negociados** — documentado en **Contrato** y materializado en **Suscripción + Entitlement** (ADR-031).

---

## Jerarquía comercial (proyección producto; ver enmienda ADR-031)

```text
Organización / Contrato
    │
    ▼
Producto                    ← qué se vende (EPosOne, Membership, Educación, ePayroll…)
    │
    ▼
Suscripción                 ← relación comercial (plan, vigencia, estado) bajo Contrato
    │
    ▼
Entitlement                 ← lo que realmente puede usar (cupos, features, excepciones)
    │
    ▼
Recursos consumidos         ← POS, cajas, tablets, cajeros, usuarios…
```

### Por qué cuatro capas (no tres)

| Capa | Responsabilidad | Ejemplo |
|------|-----------------|---------|
| **Producto** | Catálogo: qué vende la plataforma | EPosOne, Membership, ePayroll |
| **Suscripción** | Relación comercial del tenant con el producto | Plan Professional, inicio 01/08, fin 31/08, ACTIVE |
| **Entitlement** | Capacidad operativa efectiva (puede incluir excepciones comerciales) | 3 POS, 5 cajas, 5 tablets, offline=sí, KDS=sí |
| **Recursos** | Instancias reales que consumen cupo del entitlement | POS-01, CAJA_01, Tablet Samsung, Cajero1 |

La capa de **Entitlement** es la que da flexibilidad comercial real:

- Un plan Starter define 1 POS y 2 tablets.
- Pero se negocia con un cliente: "te doy 5 tablets sin cambiarte de plan".
- No se crea un plan nuevo. Solo se modifica el entitlement de esa organización.

---

## Principio rector

> **Los recursos consumen capacidad; nunca poseen derechos.**

Una caja consume un cupo. Una tablet consume un cupo. Un POS consume un cupo. Un cajero consume un cupo.

**Ninguno es propietario de la licencia.**

Toda la autoridad reside en:

```text
Organización → Producto → Suscripción → Entitlement
```

Y desde ahí se deriva todo lo demás.

---

## Modelo de datos conceptual

### Producto (ya existe: Product Registry)

Catálogo de productos de la plataforma. Ya definido en `nodeone.core.platform.product_registry`.

### Suscripción (ya existe: Subscription Registry — ADR-014)

`ets_product_subscription` — una fila por `(organization_id, product_code)`.

**No se modifica ADR-014.** Se extiende con la capa de Entitlement.

#### subscription.status (sin cambios)

`PENDING` · `TRIAL` · `ACTIVE` · `PAST_DUE` · `SUSPENDED` · `CANCELLED` · `EXPIRED`

Entitled comercialmente: `TRIAL` · `ACTIVE` · `PAST_DUE`.

### Entitlement (nuevo)

Tabla conceptual: `ets_product_entitlement`.

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id` | PK | |
| `subscription_id` | FK → `ets_product_subscription` | Suscripción padre |
| `organization_id` | FK → `saas_organization` | Desnormalizado para consultas rápidas |
| `product_code` | string | Referencia al Product Registry |
| `plan_code` | string | Plan comercial (starter, professional, enterprise) |
| `resource_limits` | JSONB | `{"pos": 3, "registers": 10, "tablets": 10, "cashiers": 30}` |
| `features` | JSONB | `{"offline": true, "kds": true, "api": false, "fiscal": true}` |
| `overrides` | JSONB | Excepciones comerciales negociadas (ej. `{"tablets": 5}` sobre un plan que da 2) |
| `effective_state` | string | Estado operativo efectivo (ver §Estados) |
| `starts_at` | datetime | |
| `ends_at` | datetime | |
| `updated_by` | FK → user | Auditoría |
| `created_at` / `updated_at` | timestamps | |

**`resource_limits`** se calcula como: defaults del plan + overrides comerciales.

El servicio de Entitlement resuelve los límites efectivos:

```python
effective_limits = {**plan_defaults, **overrides}
```

### Resolución de capacidad (enforcement)

Al crear un recurso (POS, caja, cajero, aprovisionar tablet):

```text
1. Obtener entitlement activo de la organización para el producto.
2. Contar recursos actuales del tipo solicitado.
3. ¿Tiene cupo?
   ├── Sí → crear.
   └── No → denegar con mensaje:
       "Ha alcanzado el límite de [recurso] de su plan.
        Contacte a su proveedor para ampliar."
```

EPosOne (ni ninguna app) **no** contiene lógica de planes. Solo consume la respuesta del Core.

---

## Estados

### subscription.status (ADR-014, sin cambios)

`PENDING` · `TRIAL` · `ACTIVE` · `PAST_DUE` · `SUSPENDED` · `CANCELLED` · `EXPIRED`

### entitlement.effective_state (nuevo)

Secuencia de ciclo de vida comercial:

```text
TRIAL
  ↓
ACTIVE
  ↓
PAST_DUE          ← factura impaga; sin restricciones fuertes aún
  ↓
GRACE             ← período de gracia; limitaciones según política del producto
  ↓
SUSPENDED         ← bloqueo por impago / decisión administrativa
  ↓
CANCELLED         ← relación terminada
```

También: `EXPIRED` (venció la vigencia sin renovación).

| Estado | Significado | Puede operar |
|--------|-------------|--------------|
| `TRIAL` | Evaluación gratuita con límites del plan trial | Sí |
| `ACTIVE` | Suscripción al día | Sí |
| `PAST_DUE` | Factura no pagada; aún sin restricciones fuertes | Sí (avisos) |
| `GRACE` | Período de gracia; limitaciones según política | Sí (parcial, según política) |
| `SUSPENDED` | Suspendido por impago o decisión admin | No (salvo excepciones de política) |
| `CANCELLED` | Relación terminada | No |
| `EXPIRED` | Vigencia vencida sin renovación | No |

**Por qué PAST_DUE y GRACE son distintos:**

- **PAST_DUE** = la factura no se pagó. El área comercial gestiona cobranza. El cliente opera normalmente.
- **GRACE** = ya entró en período de gracia. Empiezan limitaciones según la política del producto (ej. no crear nuevos recursos, avisos progresivos, degradación de features).

Esto da herramientas de cobranza **sin bloquear de inmediato** al cliente.

### Relación entre ambos estados

`subscription.status` es la vista **comercial/administrativa** (Registry).

`entitlement.effective_state` es la vista **operativa** (lo que el License Engine y la APK ven).

El Entitlement Engine calcula `effective_state` a partir de `subscription.status` + políticas + vigencias + grace. **No se duplica lógica** entre ambos: el Registry persiste el estado comercial; el Entitlement lo interpreta operativamente.

---

## Relación con ADR-007 (offline/sync/heartbeat)

**ADR-007 queda intacto.** No se toca:

- Offline First
- License Store local en APK
- Heartbeat integrado
- Grace Offline Window
- Provisioning ≠ Licencia
- Snapshot versionado en sync/bootstrap

**Lo único que cambia** es la **fuente de autorización**:

| Antes (ADR-007) | Ahora (ADR-016) |
|-----------------|-----------------|
| Licencia pertenece a `org + register_ref` | Licencia se **resuelve** desde `Org → Entitlement → recurso` |
| License Manager por Caja | License Manager consulta Entitlement de la organización |
| Snapshot por Caja | Snapshot por Caja (sin cambios); contenido enriquecido con plan/features |

La Caja sigue siendo la **unidad de operación**: el snapshot se entrega por caja, la APK lo cachea por caja, el offline grace aplica por caja. Pero la **autorización** viene del Entitlement de la organización, no de una licencia "pegada" a la caja.

El contrato HTTP del provisioning se mantiene. Solo se adapta internamente la resolución de la licencia.

---

## Relación con ADR-014 (Subscription Registry)

ADR-014 queda vigente sin modificaciones. La tabla `ets_product_subscription` sigue respondiendo "¿qué productos tiene este tenant?".

El Entitlement se construye **encima** del Registry:

```text
Product Registry  →  "¿Qué productos existen?"
Subscription Registry (ADR-014)  →  "¿Qué productos tiene este tenant?"
Entitlement Engine (ADR-016)  →  "¿Qué puede hacer este tenant con este producto?"
```

---

## Relación con ADR-005 (Licenciamiento por POS)

ADR-005 se mantiene vigente en sus principios:

- El dominio no se limita por el plan comercial.
- EPosOne no contiene lógica de planes.
- Los dispositivos no son la unidad comercial.

La **unidad comercial** ya fue reemplazada por ADR-007 (Caja). Con ADR-016, la unidad de **autorización** pasa al Entitlement de la organización. Los recursos (POS, cajas, tablets) consumen cupo.

---

## Planes de ejemplo (referencia comercial — no código)

| Recurso | Starter | Professional | Enterprise |
|---------|---------|--------------|------------|
| POS | 1 | 3 | Ilimitado |
| Cajas | 1 | 10 | Ilimitado |
| Tablets | 1 | 10 | Ilimitado |
| Cajeros | 2 | 30 | Ilimitado |
| Offline | Sí | Sí | Sí |
| KDS | No | Sí | Sí |
| API | No | No | Sí |
| Dashboard | Básico | Completo | Completo |
| Facturación electrónica | No | Sí | Sí |
| Reportes avanzados | No | Sí | Sí |

Los planes se configuran en EN1 como **templates de entitlement**, no como lógica en EPosOne.

---

## Dashboard comercial del administrador

El administrador de la organización debería ver:

```
┌─────────────────────────────────────────┐
│  EPosOne Professional                   │
│  Estado: ACTIVE         Vence: 15 ago   │
│                                         │
│  POS         1 / 3                      │
│  Cajas       2 / 10                     │
│  Tablets     2 / 10                     │
│  Cajeros     4 / 30                     │
│                                         │
│  Features: Offline ✓  KDS ✓  API ✗      │
└─────────────────────────────────────────┘
```

Derivado del Entitlement. No se mantiene como contadores manuales.

---

## Enforcement (gating)

| Momento | Recurso | Consulta |
|---------|---------|----------|
| Crear POS | POS | `entitlement.has_capacity('pos')` |
| Crear caja | Register | `entitlement.has_capacity('registers')` |
| Aprovisionar tablet | Tablet | `entitlement.has_capacity('tablets')` |
| Crear cajero | Cashier | `entitlement.has_capacity('cashiers')` |
| Activar feature | Feature | `entitlement.has_feature('kds')` |

Respuesta de denegación:

```
"Su plan permite N [recursos]. Ha alcanzado el límite.
 Contacte a su proveedor para ampliar."
```

EPosOne solo muestra el resultado; **nunca** conoce el plan.

---

## Multi-producto

Esta jerarquía funciona para **cualquier producto** de EN1:

| Producto | Recursos licenciables |
|----------|-----------------------|
| EPosOne | POS, cajas, tablets, cajeros, features POS |
| Membership | Miembros, planes, integraciones |
| Educación | Programas, certificados, estudiantes |
| ePayroll | Empleados, nóminas, reportes |

El Entitlement Engine es **genérico**: `resource_limits` y `features` son JSONB. Cada producto define su vocabulario de recursos y features.

---

## Decisiones rechazadas

- Licenciar por dispositivo, usuario o instalación de APK.
- Mezclar Suscripción y Entitlement en una sola entidad (impide excepciones comerciales).
- Crear un plan nuevo para cada excepción (no escala).
- Poner lógica de planes dentro de EPosOne o cualquier app.
- Eliminar PAST_DUE o GRACE (ambos son necesarios para gestión de cobranza).
- Romper ADR-007 (offline/heartbeat/provisioning quedan intactos).
- Implementar facturación automática en este hito.

---

## Fuera de alcance de este hito

- Facturación automática y renovación con cobro.
- Portal Comercial (Marketplace).
- Precios y catálogo definitivo de SKUs.
- Implementación de License Store en la APK.
- Implementación de Grace Offline Window.
- Dashboard comercial UI (solo se define el modelo).
- Enforcement activo (gating). Se definen los hooks; se activan en un hito posterior.

---

## Orden recomendado de implementación

### Paso 1 — Modelo y servicio (este hito)

1. Tabla `ets_product_entitlement` + migración.
2. `EntitlementService`: crear, consultar, modificar overrides.
3. Plan templates (Starter/Professional/Enterprise como configuración, no código).
4. Hook de resolución: `entitlement.has_capacity(resource_type)` / `has_feature(feature)`.
5. Tests unitarios + integración con Subscription Registry.

### Paso 2 — Enforcement (siguiente hito)

1. Gating en creación de POS/caja/cajero/tablet.
2. Dashboard de uso en BO (barras de consumo).
3. Adaptar License Manager para resolver desde Entitlement.
4. Enriquecer snapshot de sync con plan/features.

### Paso 3 — Comercial (posterior)

1. Portal Comercial de autoservicio.
2. Facturación + pasarela + webhooks.
3. Renovación automática.
4. Dashboard SaaS (MRR, churn, conversión trial).

---

## Criterios de aceptación arquitectónica

La implementación cumple este ADR cuando:

1. Toda autorización comercial se resuelve desde `Organización → Producto → Suscripción → Entitlement`.
2. Los recursos (POS, cajas, tablets, cajeros) **consumen cupo** del Entitlement; nunca poseen derechos.
3. ADR-007 permanece intacto en offline/sync/heartbeat/provisioning.
4. ADR-014 permanece intacto; Entitlement se construye encima.
5. EPosOne (y cualquier app) **no** contiene lógica de planes ni límites.
6. Las excepciones comerciales se modelan como `overrides` del Entitlement, no como planes nuevos.
7. `subscription.status` y `entitlement.effective_state` son capas distintas con responsabilidades claras.
8. El mismo modelo funciona para EPosOne, Membership, Educación, ePayroll y futuros productos.
9. El enforcement no bloquea operaciones en curso (principio ADR-007 §10).
10. Toda transición de estado es auditable (actor, motivo, timestamps).

---

## Historial

| Fecha | Nota |
|-------|------|
| **2026-07-27** | GO — ADR aprobado. Modelo conceptual congelado. |
| **2026-07-27** | Paso 1 Dev: tabla `ets_product_entitlement` + `EntitlementService` + plan templates + tests. |
