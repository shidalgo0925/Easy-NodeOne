# ADR-028 — Plan = defaults · Overrides comerciales · Onboarding sin precio

| Campo | Valor |
|-------|--------|
| ID | **ADR-028** |
| Título | Defaults de plan, ajustes comerciales auditados y `/start` sin precio |
| Estado | **Aceptado (diseño)** — 6 ago 2026 · propuesta Ana · formaliza CODITO · **sin GO implementación** |
| Fecha | 2026-08-06 |
| Producto | EPosOne (extensible a otros productos EN1) |
| Arquitectura | EN1 Core (Subscription + Entitlement) · Portal `/start` · Admin plataforma |
| Autor | ETS / CODITO (a partir de modelo Ana) |
| Relacionados | [ADR-014](ADR-014-SUBSCRIPTION-REGISTRY.md) · [ADR-016](ADR-016-COMMERCIAL-LICENSING-V2-ENTITLEMENT.md) · [ADR-022](ADR-022-EN1-MULTIPRODUCT-COMMERCIAL-MODEL.md) · [ADR-023](ADR-023-EPOSONE-TRIAL-SUBSCRIPTION-GRACE.md) · [ADR-024](ADR-024-EPOSONE-START-ASSISTANT.md) · [ADR-027](ADR-027-EPOSONE-ONBOARDING-UNIFICADO-V1.md) |
| Este GO | **GO diseño / contrato** (este documento). **No** autoriza código, migraciones ni deploy. |

---

## 1. Contexto

Ana propuso separar el **proceso comercial** del **proceso técnico** (install / caja / APK):

1. El cliente **elige un plan** (capacidad y beneficios).
2. EN1 crea Organización + Suscripción + entitlement con **defaults del plan**.
3. Gerencia revisa el contrato.
4. Si hay negociación, Admin aplica **ajustes** (POS, sucursales, features, vigencia) **sin cambiar el plan**.
5. En `/start` **no se muestra precio**; el precio vive en catálogo, cotización y contrato.

Esto es consistente con ADR-016 (`overrides` sobre defaults) y con ADR-024 (asistente comercial ≠ billing). Hoy el catálogo ya define cupos (`commercial_plans.py`: Business → POS 3, branches 1) y `EntitlementService.set_overrides` existe, pero:

- `/start` aún muestra precio;
- no hay pantalla Admin “Recursos del plan / Ajustes comerciales” con motivo + #contrato;
- no está cerrado el contrato de estados entre **trial self-serve** y **pendiente de activación** post-contrato.

---

## 2. Decisión

### 2.1 Principios

| Principio | Norma |
|-----------|--------|
| **Plan = defaults** | El `plan_code` define límites y features de catálogo. No se edita el plan “global” por cliente. |
| **Ajustes = overrides** | Toda excepción negociada vive en `ets_product_entitlement.overrides` (ADR-016). |
| **Efectivo** | `effective_limits = {**plan_defaults, **overrides}` (ya en `merge_limits_with_overrides`). |
| **Sin precio en onboarding** | UI `/start` y tarjetas de plan: beneficios + cupos incluidos; **cero** `USD` / price_label. |
| **Comercial ≠ técnico** | Overrides no sustituyen provisioning de device ni creación de cajero. |
| **Auditoría** | Todo override exige motivo + referencia de contrato (o “N/A — corrección interna”). |

### 2.2 Defaults de plan (EPosOne — alineado a catálogo vigente)

| Plan | POS por defecto | Sucursales por defecto | Notas |
|------|-----------------|------------------------|--------|
| Standalone | 1 | 1 | Modalidad standalone (ADR-027); no es “sin EN1” |
| Starter | 1 | 1 | Connected |
| Business | 3 | 1 | Connected |
| Enterprise | −1 (ilimitado) | −1 (ilimitado) | Connected · `multi_branch` |

Cupo **≠** “crear N cajas en el alta”. El alta `/start` sigue materializando el **mínimo instalable** (p. ej. 1 branch / 1 POS / 1 register + código). El plan autoriza **hasta** N recursos; Gerencia puede ampliar vía override antes o después del primer device.

### 2.3 Dos capas visibles (obligatorio en Admin)

```text
┌─────────────────────────────────────────┐
│ Plan                                    │
│   Business                              │
│                                         │
│ Recursos del plan (solo lectura)        │
│   POS: 3                                │
│   Sucursales: 1                         │
│   Features: …                           │
│─────────────────────────────────────────│
│ Ajustes comerciales (editables)         │
│   POS: 5          ← override            │
│   Sucursales: 2   ← override            │
│   Motivo: …                             │
│   Contrato: #2026-0017                  │
│   Quién / cuándo (audit)                │
│                                         │
│ Efectivo: POS 5 · Sucursales 2          │
└─────────────────────────────────────────┘
```

**Prohibido** en UI: editar “los recursos del plan” como si fueran el catálogo. Solo overrides.

---

## 3. Contrato de estados — `trial` vs `pending_activation`

No se inventa un enum paralelo al Registry. Se reutiliza `subscription.status` (ADR-014 / ADR-016) y se aclara política EPosOne.

### 3.1 Estados relevantes (suscripción)

| Status | Nombre de producto | Significado |
|--------|--------------------|-------------|
| `PENDING` | **Pendiente de activación** | Alta creada; Gerencia aún no liberó operación (o venta asistida esperando contrato). |
| `TRIAL` | Trial | Self-serve o post-activación en evaluación (ADR-023 · 15 días). |
| `ACTIVE` | Activa | Relación comercial al día. |
| `PAST_DUE` / grace / `SUSPENDED` / … | (sin cambio) | ADR-023 / ADR-016. |

### 3.2 Dos caminos de entrada (oficiales)

```text
                    ┌── A. Self-serve (/start)
Cliente ────────────┤
                    └── B. Venta asistida / contrato primero
```

#### Camino A — Self-serve (comportamiento actual, se mantiene)

```text
/start elige plan (sin precio)
  → org + subscription TRIAL + entitlement (defaults del plan)
  → código EN1-02 disponible
  → cliente puede instalar tablet
  → Gerencia puede aplicar overrides después (contrato firmado a posteriori)
```

**Motivo:** no romper demos ni el embudo ya en prod.

#### Camino B — Pendiente de activación (venta / Gerencia)

```text
Alta (portal asistido o /start con flag comercial)
  → org + subscription PENDING + entitlement (defaults)
  → Admin: revisar contrato · aplicar overrides · motivo + #contrato
  → Admin: «Activar» → TRIAL o ACTIVE (según política de esa venta)
  → recién entonces: emitir / renovar código · register device
```

### 3.3 Matriz de capacidad (contrato)

| Acción | `PENDING` | `TRIAL` | `ACTIVE` |
|--------|-----------|---------|----------|
| Ver org en Admin | Sí | Sí | Sí |
| Editar **ajustes comerciales** (overrides) | Sí | Sí | Sí |
| Emitir código de aprovisionamiento | **No** (default) | Sí | Sí |
| `POST /devices/register` | **No** (default) | Sí | Sí |
| Crear cajeros / operar POS | No | Sí | Sí |
| Cambiar `plan_code` | Sí (Admin; raro) | Sí | Sí |

Excepción documentada: un flag de plataforma `allow_provision_while_pending` (solo soporte ETS) puede habilitar install en `PENDING` para pilots; default **off**.

### 3.4 Activación

Acción Admin **«Activar suscripción»**:

1. Valida entitlement + overrides coherentes.
2. Transición `PENDING` → `TRIAL` (si aplica ventana de prueba) **o** `PENDING` → `ACTIVE` (si el contrato ya es pago / sin trial).
3. Registra audit: actor, timestamp, destino, ref contrato.
4. Habilita emisión de códigos.

### 3.5 Relación con entitlement.effective_state

| subscription.status | effective_state típico |
|---------------------|----------------------|
| `PENDING` | No entitled a operar device (tratado como no operativo para install) |
| `TRIAL` | `TRIAL` |
| `ACTIVE` | `ACTIVE` |

Entitled comercialmente para **operar POS** sigue siendo `TRIAL` · `ACTIVE` · `PAST_DUE` (ADR-016). **`PENDING` no es entitled operativo.**

---

## 4. Modelo de overrides (extensión de ADR-016)

### 4.1 Payload efectivo (contrato de servicio)

```json
{
  "plan_code": "business",
  "plan_limits": { "pos": 3, "branches": 1 },
  "overrides": { "pos": 5, "branches": 2 },
  "effective_limits": { "pos": 5, "branches": 2 },
  "commercial_adjustment": {
    "reason": "Contrato firmado — ampliación POS/sucursales",
    "contract_ref": "2026-0017",
    "updated_by_user_id": 12,
    "updated_at": "2026-08-06T18:00:00Z"
  }
}
```

### 4.2 Reglas

1. Claves de override ⊆ claves de `resource_limits` / features permitidas (lista blanca).
2. Valor `-1` = ilimitado (mismo semántica que catálogo).
3. Override **no** puede bajar el efectivo por debajo del **uso actual** sin confirmación explícita de riesgo (UI: warning).
4. Cambiar de plan (`set_plan`) puede `keep_overrides=true` (default) o limpiar overrides con confirmación.
5. Audit mínimo por cambio: actor, before/after effective_limits, reason, contract_ref.

### 4.3 Persistencia (fase implementación — no este GO)

Hoy: `overrides_json` + `updated_by_user_id`.  
Falta (backlog): `override_reason`, `contract_ref`, o tabla `ets_entitlement_override_event` para historial. Hasta existir columnas, Admin puede exigir reason/contract en API y persistir en audit log de plataforma.

---

## 5. Cambios UX `/start` (contrato de pantalla)

### Antes (evitar)

```text
Business
USD 39.95
[Continuar]
```

### Después (norma)

```text
EPOSOne Business
Ideal para restaurantes, cafeterías y comercios en crecimiento.

• Hasta 3 POS incluidos
• Administración central
• Sincronización
• Reportes

[Seleccionar este plan]
```

Sin mencionar precios. El catálogo interno conserva `price_*` para cotización, landing de marketing (fuera de `/start`) y facturación futura.

Wireframes detalle: §7 y carpeta `docs/eposone-start-assistant/` (actualizar en GO implementación UI).

---

## 6. Wireframe Admin — Organización → Plan / Ajustes

**Audiencia:** Admin plataforma / Gerencia comercial ETS (no cajero).  
**Ruta conceptual:** Admin org → producto EPosOne → **Plan comercial**  
(Implementación de ruta exacta: GO código posterior.)

### 6.1 Pantalla — resumen

```text
Organización: Mexican Food                         Producto: EPosOne

┌─ Plan ──────────────────────────────────────────┐
│  Plan actual:  Business                         │
│  Estado suscripción:  TRIAL | ACTIVE | PENDING  │
│  [Cambiar plan…]     [Activar…] (solo PENDING)  │
└─────────────────────────────────────────────────┘

┌─ Recursos del plan (solo lectura) ──────────────┐
│  POS: 3                                         │
│  Sucursales: 1                                  │
│  Cajeros: …   Features: …                       │
│  Origen: catálogo commercial_plans / ADR-016    │
└─────────────────────────────────────────────────┘

┌─ Ajustes comerciales ───────────────────────────┐
│  POS:        [ 5 ]                              │
│  Sucursales: [ 2 ]                              │
│  Motivo *:   [ Contrato Comercial #2026-0017  ] │
│  Contrato *: [ 2026-0017 ]                      │
│                                                 │
│  Efectivo: POS 5 · Sucursales 2                 │
│  Uso actual: POS 1 · Sucursales 1               │
│                                                 │
│  [Guardar ajustes]                              │
└─────────────────────────────────────────────────┘

┌─ Historial (auditoría) ─────────────────────────┐
│  2026-08-06 18:04  ana@…  POS 3→5  #2026-0017   │
│  2026-08-06 17:50  sistema  alta plan Business  │
└─────────────────────────────────────────────────┘
```

### 6.2 Microcopy

| Elemento | Texto |
|----------|--------|
| Título bloque defaults | Recursos del plan |
| Título bloque overrides | Ajustes comerciales |
| Hint | El plan no se modifica; estos ajustes aplican solo a esta organización. |
| Error sin motivo | Indicá el motivo y la referencia de contrato. |
| Warning cupo &lt; uso | El uso actual supera el nuevo límite. ¿Continuar? |

### 6.3 Permisos

- Lectura: roles que ya ven suscripción/plan de la org.
- Escritura overrides + Activar: rol comercial / platform admin (definir en RBAC en GO implementación).

---

## 7. Flujo extremo a extremo (producto)

```text
Cliente
  │
  ▼
Selecciona plan (Starter | Business | Enterprise | Standalone)
  — sin precio —
  │
  ▼
EN1 crea Organización
  │
  ▼
EN1 crea Suscripción + Entitlement (defaults del plan)
  │     Camino A → TRIAL (+ código)
  │     Camino B → PENDING (sin código hasta Activar)
  │
  ▼
Gerencia revisa contrato
  │
  ├─ Sin negociación → defaults quedan
  └─ Con negociación → Ajustes comerciales (overrides + audit)
  │
  ▼
(Si PENDING) Activar → TRIAL | ACTIVE
  │
  ▼
Proceso técnico (sin mezclar): código → APK register → bootstrap → cajero PIN
```

---

## 8. Fuera de alcance (este ADR)

- Pasarela de pago / checkout.
- Cambio de precios de listado.
- Loop de instalación APK (Gate 2 / LOCAL).
- Crear N POS físicos automáticamente al elegir Business.
- Soft-delete de organizaciones de prueba.

---

## 9. Criterios de hecho (cuando haya GO implementación)

| # | Criterio |
|---|----------|
| 1 | `/start` no muestra `price_label` / USD en tarjetas de plan |
| 2 | Admin muestra bloques **Recursos del plan** vs **Ajustes comerciales** |
| 3 | Guardar override exige reason + contract_ref y queda auditado |
| 4 | `effective_limits` respetan defaults ⊕ overrides en enforcement de cupos |
| 5 | Camino B: `PENDING` bloquea issue-code/register hasta Activar |
| 6 | Camino A (`TRIAL` desde `/start`) sigue permitiendo install |
| 7 | Docs ADR-016/024 enlazan aquí; pack onboarding menciona “sin precio” |

---

## 10. Plan de GOs siguientes

| Señal | Trabajo |
|-------|---------|
| **GO docs** (este) | ✅ ADR-028 |
| **GO implementación UI `/start` sin precio** | Solo front catálogo público del asistente |
| **GO implementación Admin ajustes** | Pantalla + API reason/contract_ref + audit |
| **GO camino B PENDING** | Flag alta + gate provision + Activar |
| **GO deploy** | Solo tras validar en Dev EN1 |

---

## 11. Consecuencias

**Positivas**

- Comercial y técnico separados.
- Auditoría y renovaciones claras.
- Reutiliza ADR-016 en lugar de planes custom por cliente.

**Riesgos**

- Confundir cupo POS con licencia de caja → mitigar copy Admin.
- Activar camino B sin flag rompe demos → default self-serve = TRIAL.

---

*Si hay conflicto con ADR-016 sobre la fórmula de overrides, prevalece ADR-016; este ADR fija UX, estados PENDING vs TRIAL y la norma “sin precio en `/start`”.*
