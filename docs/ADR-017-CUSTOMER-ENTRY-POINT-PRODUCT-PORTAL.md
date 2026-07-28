# ADR-017 — Customer Entry Point & Product Portal

| Campo | Valor |
|-------|-------|
| ID | ADR-017 |
| Título | Customer Entry Point & Product Portal |
| Estado | **Aprobado (GO)** — 27 jul 2026 |
| Ámbito | EN1 Platform · Portal ETS · landings comerciales por producto · lanzador inteligente |
| Relacionados | [ADR-011](ADR-011-PORTAL-ETS-PUNTO-ENTRADA.md) · [ADR-012](ADR-012-ETS-ECOSYSTEM-ARCHITECTURE.md) · [ADR-013](ADR-013-PORTAL-ETS-PUNTO-ENTRADA.md) · [ADR-014](ADR-014-SUBSCRIPTION-REGISTRY.md) · [ADR-016](ADR-016-COMMERCIAL-LICENSING-V2-ENTITLEMENT.md) |
| Precedencia | **Unifica** la experiencia de entrada del cliente. No reemplaza ADR-011/013 (portal, Brand/ProductContext) ni ADR-014/016 (suscripción/entitlement). Los complementa con el flujo comercial público y el lanzador inteligente. |
| Alcance | Decisión arquitectónica y roadmap de la **Fase Comercial – Portal Público**. **No** implementa pantallas ni DNS en este ADR. |

---

## Pregunta rectora

> **¿Cuál es la puerta oficial por la que un cliente conoce, entra y usa un producto ETS?**

No es `appprd.easynodeone.com` (infraestructura).  
No es una landing temporal de campaña.  
No es WordPress por producto.

**Es una superficie comercial permanente dentro de EN1**, por host de producto, que conduce al Portal de cuenta y —con entitlement válido— al producto.

---

## Decisión 1 — Landing dentro de EN1 (no WordPress)

**Rechazado:**

```text
Landing (WordPress) → EN1
```

**Aprobado:**

```text
Landing (EN1) → Portal EN1 → Producto
```

Motivos:

- La landing es **parte del ecosistema del producto**, no una campaña desechable.
- Aparece en Google, Instagram, Ads, flyers, tarjetas y QR: es la **puerta oficial**.
- Reutiliza Host → BrandContext → ProductContext ya existente.
- Un solo despliegue, un solo repositorio, sin duplicar CTA/auth/marca.

**WordPress / blog corporativo:** permitido solo para contenido editorial SEO (p. ej. vía EM+Acción). **No** para landings de producto.

---

## Decisión 2 — Tres superficies, un solo backend

| Superficie | Host típico | Audiencia | Responsabilidad |
|------------|-------------|-----------|-----------------|
| **Portal Público del Producto** (landing) | `eposone.easytech.services`, `epayroll.easytech.services`, … | Anónimo / marketing | Hero, beneficios, capturas, planes, FAQ, Solicitar Demo, Entrar |
| **Portal ETS** (cuenta) | `app.easytech.services` (alias `portal.easytech.services`) | Autenticado | Login, registro, Mis Productos, suscripciones, licencias, facturación, soporte |
| **App de producto** | Mismo host del producto (sesión + entitlement) | Autenticado + derecho | Dashboard / operación del producto |

```text
                 INTERNET
                     │
     ┌───────────────┼───────────────┐
     ▼               ▼               ▼
eposone.…      epayroll.…     app.easytech.services
Landing        Landing         Portal de cuenta
     │               │               │
     └───────┬───────┘               │
             ▼                       ▼
        EN1 Platform  ←──────────────┘
   (auth · orgs · subscriptions · entitlements)
             │
             ▼
        Producto (EPosOne / EPayRoll / …)
```

**Infra vs comercial:**

| Host | Rol |
|------|-----|
| `appdev` / `apptst` / `appprd.easynodeone.com` | **Infraestructura** — no usar en marketing |
| `*.easytech.services` | **Superficie comercial y de producto** — flyers, Ads, QR |

---

## Decisión 3 — El Portal no pertenece a ningún producto

El **Portal ETS** pertenece a la **cuenta del cliente**, no a EPosOne, EPayRoll, EM+Acción ni ningún otro producto.

```text
Portal ETS
    │
    ├── EPosOne
    ├── EPayRoll
    ├── EM+Acción
    ├── EClassOne
    └── … futuros
```

Los productos **cuelgan** del Portal. El Portal **no** ejecuta lógica operativa de POS, nómina, etc. (refuerza [ADR-013](ADR-013-PORTAL-ETS-PUNTO-ENTRADA.md)).

---

## Decisión 4 — Lanzador inteligente

Tras login válido, el sistema **no** fuerza siempre “Mis Productos”.

### Caso A — Entrada por host de producto (con entitlement de ese producto)

```text
eposone.easytech.services
        │
     Landing → Entrar → Login
        │
        ▼
 Dashboard EPosOne
```

No pasa por Mis Productos. **Aunque el tenant tenga N productos**, si el host es EPosOne y hay entitlement EPosOne → dashboard. Cambiar de producto = volver al Portal de cuenta.

### Caso B — Sin entitlement del producto del host (o entrada por Portal de cuenta)

```text
Login (host producto sin derecho)
  │
  ▼
302 → https://app.easytech.services/portal/products
```

```text
Login (host portal)
  │
  ▼
Portal → Mis Productos → seleccionar → abrir producto
```

### Caso C — Entrada directa a `app.easytech.services`

Siempre Portal de cuenta (Mis Productos / suscripciones), aunque el cliente tenga un solo producto — salvo deep-link explícito a un producto.

### Regla del lanzador

```text
productos_usables = subscriptions ACTIVE|GRACE ∩ entitlements válidos ∩ RBAC

si host_origen es producto P y P ∈ productos_usables:
    → abrir dashboard de P
si host_origen es producto P y P ∉ productos_usables:
    → Portal de cuenta canónico (app.easytech.services/portal/products)
si host_origen es portal:
    → Mis Productos
```

### Regla de superficie (enmienda 2026-07-28)

> **EN1 es el propietario del catálogo de productos.**  
> Los productos (EPosOne, EM1, Planilla, Relatic, etc.) no administran el catálogo ni conocen otros productos en su UX. Cada producto solo administra su dominio funcional. La selección y navegación entre productos pertenece exclusivamente al Portal EN1.

### Regla de responsabilidad de licenciamiento (explícita)

> **Un producto puede conocer únicamente su propio estado de licenciamiento (entitlement), pero nunca el catálogo completo de productos del cliente.**  
> Si necesita cambiar de producto o consultar otros productos contratados, debe **delegar** esa responsabilidad al Portal EN1.

| Quién | Puede | No puede |
|-------|--------|----------|
| **Producto** (p. ej. EPosOne) | Leer *su* entitlement (plan, cupos, features, `effective_state`) | Listar / navegar otros productos del tenant; servir Mis Productos; marketplace |
| **Portal EN1** | Catálogo contratado, Mis Productos, abrir producto, cuenta | Ejecutar dominio operativo del producto (POS, nómina, …) |
| **EN1 Core** | Subscriptions + Entitlements (fuente de verdad) | — |

Consecuencias UX:

- Mis Productos **no** se renderiza en `eposone.*` (ni en ningún host `surface=product`).
- `/portal/*` en host producto → **302** al Portal canónico.
- En el chrome del producto, «← Cambiar producto» apunta a `https://app.easytech.services/portal/products` (nunca un hub local).
- Cliente con **solo** EPosOne: login en `eposone.*` → Dashboard; **no** ve Mis Productos.

### Tres superficies (separación que escala)

```text
Landing  = vende el producto          (eposone.easytech.services/)
Portal   = administra cuenta y productos  (app.easytech.services/portal)
Producto = ejecuta solo su dominio    (/admin/eposone/…)
```

Flujos:

```text
Publicidad → eposone.* → Login → ¿entitlement EPosOne?
  Sí → Dashboard EPosOne
  No → Portal EN1 / Mis Productos

Dentro de EPosOne → Cambiar producto → Portal EN1 → Mis Productos → Abrir otro
```

---

## Decisión 5 — Nunca abrir producto sin entitlement

Cadena obligatoria:

```text
Login
  → Identity
  → Subscriptions          (ADR-014)
  → Entitlements           (ADR-016)
  → Abrir producto
```

**Prohibido:** deep-link a dashboard de producto sin validar suscripción/entitlement (salvo estados documentados GRACE según ADR-016).

---

## Decisión 6 — Resolución por host

Se mantiene el modelo existente:

```text
Host → BrandContext → ProductContext → Experiencia
```

| Host | `product_code` | Experiencia pública (anon) | Post-auth |
|------|----------------|----------------------------|-----------|
| `eposone.easytech.services` | `eposone` | Landing EPosOne | Dashboard EPosOne (si entitlement); si no → Portal canónico |
| `epayroll.easytech.services` | `epayroll` | Landing EPayRoll | Dashboard EPayRoll (si entitlement); si no → Portal canónico |
| `app.easytech.services` | `portal` | Login / marketing portal | Mis Productos |
| `appprd.easynodeone.com` | `en1` | Infra / ops | No es puerta comercial |

Fuente de verdad de hosts: `backend/nodeone/core/platform/data/host_product_map.json` + `product_registry.json`.

---

## Fase Comercial – Portal Público (roadmap oficial)

### Objetivo

Separar la **identidad comercial** de los productos de la **infraestructura técnica** EN1, sin partir el backend.

| Hito | Nombre | Entregable |
|------|--------|------------|
| **1** | Portal Público del Producto | Landing por host: hero, CTA, planes, demo, FAQ |
| **2** | Portal de Cuenta | Login, registro, recuperación, perfil (superficie Portal) |
| **3** | Portal Comercial | Mis Productos, suscripciones, licencias, facturación, descargas, soporte |
| **4** | Lanzador Inteligente | 1 producto → abrir directo; N → Mis Productos |
| **5** | Portal Multiproducto | Landings + lanzamiento EPosOne, EPayRoll, EM+Acción, EClassOne, … |

Orden de implementación sugerido: **Hito 1 (EPosOne primero)** → 2 → 4 (valor UX rápido) → 3 → 5.

---

## Qué NO decide este ADR

- Copy, diseño visual ni precios de planes.
- Proveedor de pagos / facturación electrónica del Portal.
- Implementación de Marketplace completo.
- Migración DNS de dominios legacy (Relatic, IIUS) — fuera de alcance comercial ETS genérico.
- Sustituir white-labels existentes.

---

## Criterio de hecho (DoD arquitectónico)

1. Documentado: landings = EN1; Portal ≠ producto; infra ≠ marketing URL.
2. Lanzador inteligente especificado (Casos A/B/C).
3. Cadena Identity → Subscription → Entitlement → Open obligatoria.
4. Roadmap Fase Comercial con 5 hitos adoptado como referencia de producto.
5. Referenciado desde AGENTS.md junto a ADR-011…016.

---

## Historial

| Fecha | Nota |
|-------|------|
| **2026-07-27** | Aprobado (GO) — unifica entrada cliente, landings EN1, Portal de cuenta, lanzador inteligente; WordPress descartado para landings de producto |
| **2026-07-27** | **Hito 1 implementado (Dev):** `GET /` en Host `surface=product` → landing EN1 (`product_landing/`, EPosOne completo). Infra (`appdev`/`appprd`) sigue yendo a login. |
| **2026-07-27** | **Hito 2 + Hito 4 (Dev):** auth con piel Portal ETS en Host portal; lanzador inteligente 1→producto / N→Mis Productos; `/portal/*` permitido en Host product. |
| **2026-07-27** | **Producción comercial EPosOne:** landing en `eposone.easytech.services` (planes Starter/Business/Enterprise). Release Management: [ADR-018](ADR-018-RELEASE-MANAGEMENT.md) · paquete [`releases/EN1_RELEASE_v1.0.0.md`](releases/EN1_RELEASE_v1.0.0.md). |
| **2026-07-28** | **Enmienda superficie:** Host producto no sirve Mis Productos; `/portal/*` en producto → 302 Portal canónico; post-login con entitlement del host → dashboard aunque haya N productos. |
| **2026-07-28** | **Regla de responsabilidad:** producto solo conoce su entitlement; catálogo / cambio de producto solo en Portal EN1. Chrome: «Cambiar producto». |
| **2026-07-28** | **Retiro `app.easytech.services`:** Portal canónico = `appprd.easynodeone.com`; Mis Productos same-host en producto; hosts `app`/`portal.easytech` fuera del `host_product_map` (nginx 301 → appprd). |

---

## Estado de implementación (resumen)

| Capacidad | Estado |
|-----------|--------|
| Landing EPosOne en EN1 (no WordPress) | **Hecho** — Host producto |
| Hero, beneficios, módulos, planes, FAQ, demo, Entrar | **Hecho** |
| Auth EN1 (sin segundo sistema) | **Hecho** |
| Lanzador: host producto + entitlement → dashboard (N ok) / sin derecho → Portal canónico | **Hecho** (2026-07-28) |
| Mis Productos same-host en producto + canónico `appprd` | **Hecho** (2026-07-28) — `app.easytech` retirado |
| `appprd` = Portal de cuenta EN1 | **Hecho** |
| Hito 3 Portal Comercial completo | **Pendiente** |
| Release oficial v1.0.0 | **Publicado** (`v1.0.0` = `d20bee4`) — QA operativa humana pendiente en checklist del paquete |
