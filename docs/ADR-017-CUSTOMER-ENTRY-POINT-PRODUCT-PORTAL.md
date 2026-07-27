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

### Caso A — Un solo producto con entitlement usable

```text
eposone.easytech.services
        │
     Landing → Entrar → Login
        │
        ▼
 Dashboard EPosOne
```

No pasa por Mis Productos.

### Caso B — Varios productos (o entrada por Portal de cuenta)

```text
Login
  │
  ▼
Portal → Mis Productos → seleccionar → abrir producto
```

### Caso C — Entrada directa a `app.easytech.services`

Siempre Portal de cuenta (Mis Productos / suscripciones), aunque el cliente tenga un solo producto — salvo deep-link explícito a un producto.

### Regla del lanzador

```text
productos_usables = subscriptions ACTIVE|GRACE ∩ entitlements válidos ∩ RBAC

si len(productos_usables) == 1 y host_origen es ese producto:
    → abrir dashboard del producto
si no:
    → Mis Productos (Portal)
```

Comportamiento alineado a suites SaaS multiproducto modernas.

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
| `eposone.easytech.services` | `eposone` | Landing EPosOne | Lanzador → EPosOne o Portal |
| `epayroll.easytech.services` | `epayroll` | Landing EPayRoll | Lanzador → EPayRoll o Portal |
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

---

## Estado de implementación (resumen)

| Capacidad | Estado |
|-----------|--------|
| Landing EPosOne en EN1 (no WordPress) | **Hecho** — Host producto |
| Hero, beneficios, módulos, planes, FAQ, demo, Entrar | **Hecho** |
| Auth EN1 (sin segundo sistema) | **Hecho** |
| Lanzador 1 producto → dashboard / N → Portal | **Hecho** |
| `appprd` = infra (no marketing) | **Política** — endurecer DNS/marketing pendiente ops |
| Hito 3 Portal Comercial completo | **Pendiente** |
| Release oficial v1.0.0 | **RC** — ver ADR-018; GO LIVE pendiente de QA firmada |
