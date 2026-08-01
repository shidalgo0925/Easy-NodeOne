# ADR-022 — Modelo comercial multiproducto EN1 (activo raíz)

| Campo | Valor |
|-------|--------|
| ID | ADR-022 |
| Título | Modelo comercial multiproducto — Organización como activo raíz |
| Estado | **Propuesto** — 1 ago 2026 · pendiente aprobación Prog1 + Ana / producto |
| Ámbito | EN1 Platform (todos los productos ETS) · Portal · Subscription / Entitlement |
| Relacionados | [ADR-014](ADR-014-SUBSCRIPTION-REGISTRY.md) · [ADR-016](ADR-016-COMMERCIAL-LICENSING-V2-ENTITLEMENT.md) · [ADR-017](ADR-017-CUSTOMER-ENTRY-POINT-PRODUCT-PORTAL.md) · [ADR-019](ADR-019-ADMINISTRATIVE-HIERARCHY.md) · [ADR-007](ADR-007-EPOSONE-COMMERCIAL-LICENSING-OFFLINE.md) (solo dominio EPosOne offline) · [ADR-021](ADR-021-EPOSONE-INSTALLATION-LIFECYCLE.md) |
| Precedencia | **Congela la narrativa comercial** multiproducto. No invalida ADR-016 (Producto→Suscripción→Entitlement→Recursos). Acota ADR-007: Caja = recurso/consumo de EPosOne, **no** objeto comercial de la plataforma. |
| No implementa | Billing, Cuenta multi-org en BD, UI de holding, pasarela de pago |

---

## Pregunta rectora

> **¿Cuál es el activo raíz de la plataforma comercial EN1?**

---

## Decisión (propuesta)

1. **La Organización (tenant) es el activo raíz comercial.**  
   Existe **independientemente** de si tiene EPosOne, ePayroll u otro producto.

2. **Los productos son capacidades que se suscriben sobre esa organización.**  
   Se agregan / quitan / suspenden sin recrear la organización ni migrar usuarios “porque cambió el producto”.

3. **Ningún producto es dueño de la organización.**  
   EPosOne, ePayroll, EM+Acción, Marketplace, CRM, Certificados, etc. administran solo su dominio operativo.

4. **Se vende Producto (+ plan / entitlement), no Caja ni Tablet.**  
   Los recursos (cajas, empleados, campañas…) **consumen cupo**; no poseen derechos (ADR-016).

5. **Cada producto define su propio árbol de recursos.**  
   Solo EPosOne usa Sucursal → POS → Caja → Tablet. Otros productos no pasan por Caja.

---

## Contexto — por qué este ADR

Una narrativa “todo termina en EPosOne → Caja → Tablet” y frases del tipo *“a la compañía se le crea una suscripción”* mezclan:

| Error | Efecto |
|-------|--------|
| Centrar el flujo en EPosOne | ePayroll / CRM / Certificados no encajan |
| Suscripción como si creara la org | Invierte el orden: org primero, productos después |
| Vender “Caja” | Confunde unidad operativa de un producto con unidad comercial de la plataforma |
| Product Registry como centro de negocio | El Registry solo responde *qué existe en el catálogo*, no *quién es el cliente* |

ADR-014/016/017 ya apuntan al modelo correcto; este ADR **congela el activo raíz** y el orden de creación para no seguir implementando onboarding EPosOne-first.

---

## Orden canónico (obligatorio en docs y flujos nuevos)

```text
Cuenta del cliente (login / facturación)     ← ver §Cuenta (gap)
        │
        ▼
Organización (tenant)                         ← activo raíz; puede existir sin productos
        │
        ▼
Producto(s) contratados                       ← catálogo: Product Registry
        │
        ▼
Suscripción  (ADR-014)                        ← (organization_id, product_code)
        │
        ▼
Entitlement  (ADR-016)                        ← plan, cupos, features, overrides
        │
        ▼
Recursos del producto                         ← dominio propio de cada producto
```

### Frase prohibida / frase correcta

| Prohibido (narrativa) | Correcto |
|----------------------|----------|
| “A la compañía se le crea una suscripción (y así nace).” | “La organización existe; las suscripciones se **agregan** conforme adquiere productos.” |
| “El cliente compra una Caja / Tablet.” | “El cliente compra un **producto**; el entitlement habilita cupos; los recursos consumen cupo.” |
| “EN1 = EPosOne.” | “EN1 = plataforma; EPosOne = un producto.” |

---

## Dominios de recursos por producto (ejemplos)

| Producto | Recursos típicos (no exhaustivo) |
|----------|----------------------------------|
| **EPosOne** | Sucursal → POS → Caja → Device/Tablet · cajeros · catálogo |
| **ePayroll** | Empleados → contratos → planillas |
| **CRM** | Cuentas / contactos → oportunidades |
| **EM+Acción / Certificados** | Eventos → participantes → certificados |
| **Marketplace / futuros** | Según su dominio; **sin** forzar Caja |

EPosOne **solo después** de tener suscripción/entitlement operable crea su jerarquía operativa. Provisioning de tablet (EN1-02) e Installation Lifecycle (ADR-021) siguen siendo del **canal EPosOne**, no del modelo comercial de plataforma.

---

## Relación con ADR-007 (Caja)

| Concepto | Dueño | Rol |
|----------|-------|-----|
| Suscripción EPosOne | EN1 Platform (ADR-014/016) | Derecho comercial al producto |
| Entitlement (p. ej. 3 cajas) | EN1 Platform | Capacidad |
| Caja concreta + License Engine por register | EPosOne (ADR-007) | **Consumo** de cupo + continuidad offline |

No se “vende la Caja” en el Portal. Se vende **EPosOne Business** (o plan X) que **incluye** N cajas de cupo.

---

## Cuenta del cliente (gap — decisión explícita pendiente)

ADR-017 habla de **Portal de cuenta**. Hoy el cableado comercial dominante es:

```text
Usuario ↔ Organization  →  productos suscritos
```

Ana / producto proponen:

```text
Cuenta cliente  →  N Organizaciones  →  productos por org
```

Ej.: una misma cuenta administra Easy Technology, Mexican Food y Holding XYZ sin duplicar login/pago.

| Opción | Significado |
|--------|-------------|
| **A — Congelar V1** | Activo raíz = Organización. “Cuenta” = usuario(s) de esa org + Portal. Multi-org holding = **fuera de V1**. |
| **B — Objetivo V2** | Introducir entidad **Customer Account** (billing/login) 1→N `saas_organization`. |

**Este ADR (propuesto) asume A para no bloquear onboarding**, y deja **B** como backlog obligatorio antes de facturación multi-empresa.

Criterio de aceptación de B (futuro): un pago / un login puede asociarse a varias orgs sin migrar datos ni recrear tenants.

---

## Implicaciones para implementación (sin GO de código aquí)

1. Onboarding comercial nuevo: **crear/asegurar Organización antes** de suscribir productos.  
2. Portal Mis Productos: lista suscripciones de la **org de sesión**, no “el producto EPosOne crea la org”.  
3. No diseñar checkout que cree solo “caja + licencia” sin fila de suscripción de producto.  
4. Docs de handoff / resúmenes a negocio: usar el orden canónico de este ADR.  
5. Simulaciones Dev: válidas solo si demuestran org → producto → entitlement → (opcional) recursos del producto.

---

## Fuera de alcance

- Precios, SKUs comerciales, pasarela (Stripe/Yappy).  
- UI de holding multi-org (opción B).  
- Cambios de wire APK / License Engine por caja.  
- Reescribir ADR-016; se **referencia** y se alinea narrativa.

---

## Criterio de aceptación de este ADR

- [ ] Prog1 + Ana: acuerdo en activo raíz = Organización.  
- [ ] Acuerdo: suscripciones son aditivas; org no depende de EPosOne.  
- [ ] Acuerdo: Caja = recurso EPosOne, no objeto comercial de plataforma.  
- [ ] Elección explícita A vs B para Cuenta multi-org (V1 vs V2).  
- [ ] Ningún flujo comercial nuevo se documenta EPosOne-first.

---

## Resumen ejecutivo

> La Organización (tenant) es el activo raíz. Los productos son capacidades suscritas sobre esa organización. Cada producto consume y administra sus propios recursos; ninguno es dueño de la organización. EPosOne es un producto más — no el centro de EN1.

---

*Propuesto 1 ago 2026 — a partir de revisión de modelo comercial multiproducto (Ana / Prog1). No implementar sin aceptación.*
