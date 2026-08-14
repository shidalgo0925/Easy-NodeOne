# EN1 ADR-038 F0 — Module & Domain Inventory

| Campo | Valor |
|-------|--------|
| ADR | [ADR-038](ADR-038-EN1-MODULAR-DOMAIN-ARCHITECTURE.md) |
| Fase | **F0** — Discovery / House Audit |
| Fecha | 2026-08-13 |
| Entorno inspeccionado | Dev EN1 `/opt/easynodeone/dev/app` · rama `develop` |
| Refactor F0 | Ninguno (solo documentación) |
| Estado | **F0 DONE** · **F1 DONE (Dev)** — F2–F8 OFF hasta GO |
| Código F1 | `models/module_registry.py` · `nodeone/core/platform/module_registry.py` |

---

## 1. Resumen ejecutivo

Hoy EN1 **no** tiene un Module Registry ADR-038. Opera con **tres catálogos paralelos**:

1. **SaaS** — `saas_module` + `saas_org_module` (toggle ON/OFF por org)
2. **ApplicationDescriptor** — `app_registry.py` + manifests (`emembership`, `eposone`, …)
3. **ProductRegistry** — productos ETS (`eposone`, `esecurebroker`, `epayroll`, …) + Subscription/Entitlement

Más: **RBAC** (quién) y **nav_menu** (visibilidad = SaaS ∧ RBAC ∧ endpoint).

No existen tablas `ModuleDefinition` / `OrganizationModule` con ese nombre en el legado. El equivalente operativo histórico es `SaasModule` / `SaasOrgModule`. **F1** añade `module_definition` / `organization_module` (aditivo; dual-write).

**Planilla/ePlanilla:** solo shell + licenciamiento/portal — **sin** dominio operativo de nómina en EN1 (alineado con ADR-038 §21).

---

## 2. Inventario de capas actuales

### 2.1 ApplicationDescriptor (`app_registry.py`)

| id | saas_codes | depends_on | Tipo ADR-038 |
|----|------------|------------|--------------|
| contacts | contacts, crm_contacts | — | EN1_NATIVE (shared) |
| emembership | memberships | — | EN1_NATIVE (legacy-heavy) |
| ecrm | crm, crm_contacts | contacts | EN1_NATIVE |
| eevents | events | contacts | EN1_NATIVE |
| ecertificates | certificates | eevents, emembership | EN1_NATIVE |
| eappointments | appointments | — | EN1_NATIVE |
| academic | academic | emembership | EN1_NATIVE (IIUS-heavy) |
| eposone | eposone | contacts | EN1_NATIVE control-plane + EXTERNAL APK |
| epayroll | epayroll | contacts | EXTERNAL_CONTROLLED (scaffold) |
| esales | sales | contacts | EN1_NATIVE |
| efactura | efactura | contacts, esales | EN1_NATIVE |
| emarketing | marketing_email | ecommunications | EN1_NATIVE |
| ecommunications | communications | — | EN1_NATIVE |
| eanalytics | analytics | — | EN1_NATIVE |

### 2.2 SaaS catalog (seed) — códigos extra / ERP

Presentes en seed y/o nav, **no** todos como ApplicationDescriptor:  
`payments` (core), `workshop`, `contador`, `operaciones`, `accounting`, `policies`, `office365`, `chatbot`, `qr_generator`, `security_matrix`, `rbac_matrix`, …

**Enable/disable:** fila `saas_org_module.enabled`; sin fila → `is_core`; código ausente del catálogo → OFF. Platform admin bypassa enforce.

**Deshabilitar hoy:** no borra datos (cumple espíritu ADR-038 §4 a nivel SaaS). No hay `disabled_at` formal ni audit de enable/disable unificado.

### 2.3 ProductRegistry (ETS)

| product | Tipo | EN1 ops |
|---------|------|---------|
| eposone | active | BO + domain + licensing |
| esecurebroker | active | commercial_bridge only |
| epayroll | active | home shell “En prueba” |
| portal / en1 | platform | entry |
| relatic / iius | legacy | freeze Carril 1 |

### 2.4 Paquetes filesystem (`nodeone/modules/`)

~75 directorios: apps de producto, ERP (`sales`, `workshop`, `appointments`, …), muchos `admin_*`, bridge comercial, portal ETS. **No** hay 1:1 módulo↔paquete↔saas_code.

### 2.5 Dominios Sales / Products / Inventory / Promotions (hoy)

| Dominio objetivo | Estado actual | Evidencia |
|------------------|---------------|-----------|
| Products | **Mezclado / informal** | Catálogo servicios/tienda, Odoo catalog client, productos EPosOne en BO — sin Module `products` único |
| Inventory | **Parcial / EP1-centrado** | `CoreStockMovement`, `eposone` stock/kardex, ADR-006 — no módulo Inventory genérico tenant |
| Sales | **Parcial** | `Quotation` / `QuotationLine` en `modules/sales`; nav Ventas; no Sale Order formal ADR-038 |
| Promotions | **Mezclado** | `DiscountCode` (+ product_codes ETS), descuentos eventos, membership discounts, admin product-discount-codes — no dominio Promotions aislado con snapshot |
| Payments | **Transversal legacy+cart** | `payment`, processors, yappy/stripe; bridge comercial aún sin ledger Attempt formal |
| Memberships | **Dual** | `Membership` + `Subscription` + org access membership — riesgo de fusión conceptual |

---

## 3. Dependencias

| Declarado | Dónde | ¿Enforced? |
|-----------|-------|------------|
| App `depends_on` | app_registry / manifests | Soft (launcher runtime) |
| `saas_module_dependency` | seed (pocos: office365→communications, academic→sales) | UI; **no** grafo completo |
| Nav compose | codes hardcoded | Solo visibilidad |

**Drift:** registry vs saas deps vs nav no coinciden (ej. academic→emembership en registry vs academic→sales en SaaS seed).

---

## 4. Matriz Current → Target (extracto prioritario)

| Componente | Dominio actual | Dominio objetivo | RELATIC | IIUS | EP1 | ESB | Acción |
|------------|----------------|------------------|---------|------|-----|-----|--------|
| `saas_module` / `saas_org_module` | Toggle ERP | Module Registry F1 | KEEP | KEEP | KEEP | — | **FORMALIZE** → ModuleDefinition |
| `ApplicationDescriptor` | App platform | Application Registry F8 | KEEP | KEEP | KEEP | — | **FORMALIZE** |
| `ProductRegistry` + Entitlement | Control plane ETS | Subscriptions/Licensing | LEGACY | LEGACY | KEEP | KEEP | **KEEP** / FORMALIZE |
| `commercial_bridge` | ESB M2M commercial | Integrations + Licensing | — | — | — | KEEP | **KEEP** / EXTERNALIZE ops |
| `emembership` + public_membership | Assoc + access mezclado | Memberships (assoc) | KEEP | KEEP | — | — | **LEGACY** + F7 |
| `Membership` vs `Subscription` | Dual SoR | Memberships / Payments | KEEP | KEEP | — | — | **FORMALIZE** (unificar concepto, no big-bang) |
| `certificates` | Shared | Certificates | KEEP | KEEP | — | — | **KEEP** |
| `academic` / enrollment | IIUS LMS | Academic / EXTERNAL | — | KEEP | — | — | **LEGACY** / MOVE-LATER |
| `eposone` BO + domain | Control plane | Inventory/Sales contracts + EXTERNAL APK | — | — | KEEP | — | **KEEP** / FORMALIZE |
| `epayroll` home | Shell | EXTERNAL_CONTROLLED Planilla | — | — | — | — | **EXTERNALIZE** / KEEP licensing |
| `sales` Quotation | Sales parcial | Sales F5 | soft | soft | soft | — | **FORMALIZE** |
| `DiscountCode` / promos ETS | Promos mezclado | Promotions F6 | soft | soft | — | KEEP | **SPLIT** / FORMALIZE |
| Event discounts | Events | Events (no Promotions genérico) | KEEP | soft | — | — | **KEEP** |
| `payments` + checkout | Payments cart | Payments | KEEP | KEEP | soft | — | **KEEP** / FORMALIZE ledger |
| `workshop` | Taller | Ops / Inventory-adj | soft | — | — | — | **LEGACY** / FORMALIZE later |
| `nav_menu.py` hardcodes | Nav | Nav F2 from modules | KEEP | KEEP | KEEP | — | **FORMALIZE** |
| `if brand/org` Relatic/IIUS | Compat | Documented legacy | KEEP | KEEP | — | — | **LEGACY-COMPAT** |
| Carril 1 freeze Relatic/IIUS | Deploy | Protection gate | KEEP | KEEP | — | — | **KEEP** |

---

## 5. Mapa RELATIC

| Pieza | Clasificación |
|-------|----------------|
| Freeze + silo `relatic` + tag | **KEEP** |
| Host map `apps.relatic.org` | **KEEP** |
| saas `memberships` + emembership | **KEEP** / F7 |
| `Membership` + payment → `Subscription` | **FORMALIZE** (cuidado) |
| Tier pricing events/services | **LEGACY-COMPAT** |
| Certificates + events | **KEEP** |
| Deploy `develop` a Relatic | **Prohibido** (Carril 1) |

**Impacto F1 Module Registry:** bajo si solo se **añade** capa sin quitar saas toggles (compat).

**Impacto F7 Memberships:** **alto** — gate RELATIC obligatorio.

---

## 6. Mapa IIUS

| Pieza | Clasificación |
|-------|----------------|
| Freeze + host dedicado + brand preset | **KEEP** |
| academic + appointments + memberships | **KEEP** |
| certificates (shared capability) | **KEEP** |
| Classic launcher org ids | **LEGACY-COMPAT** |
| Seeds/scripts `*iius*` | **MOVE-LATER** (paquete maint) |

**Impacto F1:** bajo (additive).  
**Impacto F7 / certificados:** alto — gate IIUS.

---

## 7. Mapa EP1 (EPosOne)

| Pieza | Clasificación |
|-------|----------------|
| ADR-006 Op vs Admin | **KEEP** |
| `eposone` module + `eposone_domain` | **KEEP** / FORMALIZE Inventory contracts |
| Connected provisioning | **KEEP** (ADR-034) |
| Standalone `/start` | **KEEP** (ADR-033) — no ops module |
| APK offline | **EXTERNALIZE** |

**Impacto F3–F5:** medio — Products/Inventory/Sales deben respetar contratos Connected.

---

## 8. Mapa ESB

| Pieza | Clasificación |
|-------|----------------|
| `commercial_bridge` | **KEEP** |
| Plans / quote / checkout / entitlement | **KEEP** |
| ADR-037 M2M | **KEEP** (gate ESB) |
| Ops seguros | **EXTERNALIZE** |

**Impacto F1:** nulo si no se toca bridge.  
**Impacto F6 Promotions:** medio (DiscountCode product-scoped ya usado en checkout).

---

## 9. Planilla / EPayRoll dentro de EN1

| Existe | Detalle |
|--------|---------|
| Product + saas `epayroll` | Sí |
| Nav ePlanilla | Sí → home |
| Cálculo nómina / empleados / períodos | **No** |
| Modelos Payroll | **No** |

**Acción:** **EXTERNALIZE** ops · **KEEP** licensing/portal · **no** crecer planilla operativa en EN1 (ADR-038 §21).

---

## 10. Candidatos por acción (rollup)

| Acción | Ejemplos |
|--------|----------|
| **KEEP** | commercial_bridge, Carril 1 freezes, payments core, certificates capability, ADR-006 |
| **FORMALIZE** | ModuleRegistry sobre SaaS, nav desde modules, Quotation→Sales, Dual membership SoR |
| **SPLIT** | DiscountCode ETS vs event discounts vs membership discounts → Promotions |
| **LEGACY** | Relatic/IIUS white-label paths, classic launcher, epayroll placeholder UX |
| **EXTERNALIZE** | ESB ops, EP1 APK, Planilla ops |
| **DEPRECATE** | (ninguno urgente en F0; listar en F1 si aparece dead saas code) |
| **MOVE** | IIUS seeds/scripts packaging; Relatic-only docs |

---

## 11. Tests actuales (caracterización)

| Área | Ubicación típica | Nota F0 |
|------|------------------|---------|
| SaaS / platform | `tests/platform/` | Mantener como regresión F1 |
| Commercial bridge | `test_commercial_bridge_esb.py` | Gate ESB |
| Nav ADR-019 | `test_adr019_admin_hierarchy_nav.py` | Nav F2 |
| EPosOne | tests eposone / occ | Gate EP1 |
| Memberships / payments | payments + membership tests | Gate RELATIC |

F0 **no** añadió tests nuevos (solo inspección). F1 deberá ampliar tests de ModuleRegistry sin romper los anteriores.

---

## 12. Riesgos

1. **Tres catálogos** → confusión Module vs App vs Product; F1 debe mapear, no reemplazar a ciegas.  
2. **Membership dual** → tocar sin F7 + gates Relatic/IIUS rompe verticales.  
3. **Promos mezcladas** → extraer (F6) sin snapshots puede reescribir históricos.  
4. **Nav hardcoded** → F2 prematuro sin F1 estable.  
5. **epayroll shell** → marketing sugiere ops inexistente; riesgo de scope creep nómina en EN1.  
6. **Deps drift** → enable module sin validar grafo real.  
7. **Carril 1** → cualquier “limpieza modular” no debe desplegarse a Relatic/IIUS sin GO freeze.

---

## 13. Propuesta concreta F1 — **IMPLEMENTADO (Dev EN1)**

**Objetivo F1:** Module Registry **aditivo** sin mover dominios legacy.  
**GO:** recibido en chat (2026-08-13).

### Entregables F1

| # | Entregable | Estado |
|---|------------|--------|
| 1 | `ModuleDefinition` + `OrganizationModule` | Sí — `models/module_registry.py` + DDL |
| 2 | Seed desde `SAAS_CATALOG_MODULES` | Sí — `ensure_module_registry` |
| 3 | Sync desde `saas_org_module` | Sí — no borra SaaS |
| 4 | `is_module_enabled` / `enable` / `disable` + deps | Sí — `nodeone/core/platform/module_registry.py` |
| 5 | Dual-write a `saas_org_module` | Sí — admin API delega |
| 6 | Admin UI | Capa encima `/api/admin/saas/modules` (`module_key`); sin rewrite nav (F2) |
| 7 | Tests | `tests/platform/test_module_registry_f1.py` |
| 8 | Matriz `saas_code` ↔ `module_key` | Sí — **identidad F1** (ver abajo) |

### Matriz mapeo F1

| saas_code | module_key | Notas |
|-----------|------------|--------|
| *(todos los de `SAAS_CATALOG_MODULES`)* | == saas_code | Identidad 1:1 en F1 |
| App Registry `id` (emembership, eevents, …) | *no es module_key* | Ver `APP_ID_TO_SAAS_CODES` en module_registry; formalizar apps = **F8** |

### Criterio de hecho F1

- Registry operativo en Dev (bootstrap llama `ensure_module_registry`).
- SaaS legacy sigue mandando guards/nav hasta **F2**.
- Disable ≠ DELETE.
- **No** Relatic/IIUS silo; **no** F2–F8 sin GO.

**Siguiente gate:** `GO ADR-038 F2` (nav/auth consumen module + entitlement + RBAC).

---

## 14. Entregables F0 (checklist ADR-038 §37)

| # | Entregable | Estado |
|---|------------|--------|
| 1 | Inventario módulos actuales | Sí §2 |
| 2 | Matriz Current → Target | Sí §4 |
| 3 | Dependencias | Sí §3 |
| 4 | Módulos mezclados | Sí §2.5 |
| 5 | Mapa RELATIC | Sí §5 |
| 6 | Mapa IIUS | Sí §6 |
| 7 | Mapa EP1 | Sí §7 |
| 8 | Mapa ESB | Sí §8 |
| 9 | Planilla en EN1 | Sí §9 |
| 10 | KEEP/FORMALIZE/… | Sí §10 |
| 11 | Tests actuales | Sí §11 |
| 12 | Riesgos | Sí §12 |
| 13 | Propuesta F1 | Sí §13 |

---

## 15. STOP (F0)

**F0 cerrado en documentación.**  
**F1 Module Registry:** implementado en Dev tras GO (ver §13).  
**No iniciar F2–F8** hasta **GO ADR-038 F\<n\>** explícito.
