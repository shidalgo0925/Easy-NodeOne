# ADR-038 — EN1 Modular Domain Architecture & Domain Boundaries

| Campo | Valor |
|-------|--------|
| ID | **ADR-038** |
| Título | EN1 Modular Domain Architecture & Domain Boundaries |
| Estado | **Propuesto** — 13 ago 2026 · listo para revisión / ACCEPT · **F0 autorizado** (inventario) · **F1–F8 OFF** hasta GO explícito |
| Ámbito | Easy NodeOne — plataforma modular · fronteras de dominio · protección RELATIC / IIUS · control plane ESB / EP1 / Planilla |
| Autores | CODITO (EN1) |
| Relacionados | [ADR-014](ADR-014-SUBSCRIPTION-REGISTRY.md) · [ADR-016](ADR-016-COMMERCIAL-LICENSING-V2-ENTITLEMENT.md) · [ADR-018](ADR-018-RELEASE-MANAGEMENT.md) · [ADR-031](ADR-031-EN1-COMMERCIAL-DOMAIN-ARCHITECTURE.md) · [ADR-032](ADR-032-PRODUCT-IMPLEMENTATION-MODEL.md) · [ADR-037](ADR-037-INTEGRATIONS-M2M-CREDENTIALS-OPERATIONS.md) · [EN1_PLATFORM_MASTER_PLAN.md](EN1_PLATFORM_MASTER_PLAN.md) · [EN1_PLATFORM_CARRILES_Y_SOPORTE.md](EN1_PLATFORM_CARRILES_Y_SOPORTE.md) · F0: [EN1_ADR038_F0_MODULE_DOMAIN_INVENTORY.md](EN1_ADR038_F0_MODULE_DOMAIN_INVENTORY.md) |
| Implementación | **F0 = inventario (sin refactor).** F1–F8 requieren GO por fase. PROD solo con GO específico. |

---

## 1. Contexto

EN1 ha crecido incorporando capacidades comerciales, membresías, pagos, productos, promociones, certificados, licencias, integraciones y funcionalidades específicas de diferentes productos/verticales.

Parte de estas capacidades se encuentran correctamente aisladas y otras han quedado mezcladas por evolución histórica.

Antes de continuar ampliando EN1 se decide formalizar sus fronteras.

**El objetivo NO es ejecutar un refactor masivo.**

El objetivo es establecer:

- qué es un módulo;
- qué responsabilidad pertenece a cada módulo;
- qué módulos puede activar una organización;
- qué dependencias existen;
- qué funcionalidades deben salir de EN1 hacia productos independientes;
- cómo proteger RELATIC e IIUS;
- cómo EN1 actúa como control plane para productos externos como ESB, EP1 y Planilla.

---

## 2. Principio arquitectónico

EN1 será una plataforma modular.

Una capacidad funcional deberá pertenecer a un dominio claramente definido.

Modelo:

```text
ORGANIZATION → MODULES → FEATURES → ENTITLEMENTS → RBAC
```

Las responsabilidades son distintas.

| Concepto | Definición |
|----------|------------|
| **Module** | Capacidad funcional instalada/disponible (CRM, Products, Inventory, Sales, Promotions, Memberships…) |
| **Feature** | Capacidad concreta dentro de un módulo (ej. `Sales.quotations`) |
| **Entitlement** | Si el contrato/licencia de la organización permite la capacidad |
| **RBAC** | Si el usuario específico está autorizado |

---

## 3. Regla de activación

Los módulos deberán poder habilitarse / deshabilitarse por Organization cuando corresponda.

Estados: `ENABLED` / `DISABLED`.

Opcionalmente después: `AVAILABLE` / `INSTALLED` (disponibilidad global vs activación tenant).

---

## 4. Deshabilitar NO elimina

> Desactivar un módulo nunca elimina sus datos históricos.

Un módulo deshabilitado: desaparece de navegación cuando corresponda; no permite nuevas operaciones; conserva datos, auditoría y referencias; puede reactivarse sin reconstruir información.

**No** usar `DELETE` para implementar desactivación.

---

## 5. Dependencias

Todo módulo deberá declarar dependencias explícitas.

Ejemplos: `Inventory → Products` · `Sales → Products` · `Promotions → Products` · `Sales → CRM/Customer`.

Verificar dependencias **antes** de habilitar. No dependencias ocultas vía imports incidentales.

---

## 6–14. Catálogo objetivo de dominios

### 6.1 Identity / Access

Usuarios, autenticación, organizations, memberships de acceso organizacional, roles, permisos, sesiones, scopes.

**No** confundir organization membership con membresía comercial/asociativa (RELATIC).

### 6.2 CRM / Contacts

Personas, empresas, contactos, relaciones comerciales, leads/oportunidades. Consumible por otros dominios.

### 6.3 Products

**Qué vende/ofrece** una organización: SKU, categorías, unidades, impuestos/referencias, precio base, activo/inactivo, atributos. Puede ser inventariable, servicio o licencia/digital.

Products **NO** administra cantidades físicas.

### 7. Inventory

**Cuánto / dónde / cómo se movió:** almacenes, stock, movimientos, entradas/salidas, ajustes, transferencias, reservas, kardex, trazabilidad.

Invariante: el stock es **consecuencia de movimientos**. Depende de Products. Un producto puede existir sin Inventory.

### 8. Sales

Proceso comercial: `QUOTATION → SALE ORDER → FULFILLMENT/DELIVERY → INVOICE/PAYMENT`.

Núcleo inicial: cotizaciones (cliente, líneas, precios, impuestos, descuentos, vigencia, estados DRAFT→SENT→ACCEPTED→SALE_ORDER; EXPIRED/REJECTED/CANCELLED).

No eliminar cotización confirmada para representar cambios de estado.

### 9. Promotions

Dominio propio: cupones, descuentos temporales, condiciones, vigencias, elegibilidad, campañas.

**No** es Products ni Sales. Sales consulta Promotions. Aplicación → **snapshot** en la operación; cambiar la promo después no altera históricos.

### 10. Pricing

Separar **precio** vs **promoción**. Preparar precio base / listas (Retail, Distributor, Enterprise…). Una lista **no** es una promoción. Pricing Engine avanzado no es obligatorio en F1.

### 11. Purchases (futuro)

`Supplier → Purchase Order → Receipt → Inventory`. No mezclar compras dentro de Inventory.

### 12. Payments

Dominio transversal: intentos, transacciones, medios, estados, conciliación, procesadores. **No** es Sales. Consumido por Sales / Memberships / Subscriptions.

### 13. Subscriptions / Licensing

Contratos, planes, suscripciones, licencias, entitlement, vigencia, activación, suspensión, renovación, provisioning/control plane — fundamental para productos externos.

### 14. Memberships

| Tipo | Significado |
|------|-------------|
| **Organization Membership** | `User ↔ Organization` (acceso / RBAC) |
| **Business/Association Membership** | Afiliación (ej. RELATIC): miembro, vigencia, categoría, beneficios |

**NO** fusionar ambos conceptos.

---

## 15–17. Boundaries RELATIC / IIUS

### RELATIC — Compatibility Boundary

ADR-038 **NO** autoriza refactor destructivo de RELATIC. Mantener compatibilidad de API/comportamiento productivo.

Antes de modificar Memberships: inventariar modelos, tablas, endpoints, servicios, jobs, pagos, vigencia, integraciones → clasificar KEEP / FORMALIZE / LEGACY-COMPAT / MOVE-LATER / DEPRECATE-LATER.

Normalización **incremental**. No big-bang.

### IIUS — Isolation Boundary

Vertical protegida. Antes de tocar memberships / certificados / pagos / usuarios / orgs: impacto IIUS. No fusionar lógica IIUS en módulos generales sin razón + migración certificada.

---

## 18–23. Productos externos vs módulos EN1

| Tipo | Definición |
|------|------------|
| **EN1 Module** | Capacidad ejecutada dentro de EN1 |
| **External Product** | Dominio, runtime, BD, UX propios; EN1 = control plane |

**ESecureBroker:** dominio/runtime/DB propios. EN1: identidad/control comercial, contrato, sub, entitlement, M2M. EN1 **no** absorbe seguros.

**EPosOne:** producto independiente; Connected consume EN1 según contratos. Offline-first en APK. EN1: control plane / licensing / catálogo-inventario central cuando Connected lo determine.

### Planilla / Nómina — NUEVA DECISIÓN

> Planilla/Nómina **NO** será un módulo operativo de EN1.

Patrón ESB: producto propio (dominio, web, runtime, BD, UX, reglas laborales, cálculo, empleados, reportes).

EN1 solo ciclo comercial: Cliente → Contrato → Suscripción → Licencia → Entitlement → Planilla habilitada (+ plan, vigencia, límites, health).

**No** replicar datos sensibles de nómina en EN1 salvo IDs mínimos de licenciamiento/soporte/auditoría de integración. EN1 **no** es SoR de nómina.

---

## 24–25. Application Registry

Registro de aplicaciones: RELATIC, IIUS, EPosOne, ESecureBroker, Planilla, …

Campos: `application_key`, nombre, tipo, owner, runtime, integración, módulos EN1, entitlements, estado, ambientes.

Tipos mínimos: `EN1_NATIVE` · `EXTERNAL_CONTROLLED`.

---

## 26–29. Navegación, Module Registry, no hardcode

Navegación progresiva desde: módulos habilitados × features × entitlements × RBAC.

`ModuleDefinition` + `OrganizationModule` (unique org+module_key); enable/disable con auditoría; dependencias explícitas.

**Prohibido** nuevas reglas `if org == RELATIC|IIUS|XYZ` para arquitectura. Legacy documentado temporalmente.

---

## 30–32. Auditoría previa y migración

Antes de mover código: **EN1 MODULE & DOMAIN INVENTORY** (F0).

Matriz: Componente | Dominio actual | Dominio objetivo | RELATIC | IIUS | EP1 | ESB | Acción (KEEP/FORMALIZE/MOVE/SPLIT/LEGACY/DEPRECATE/EXTERNALIZE).

Reglas: no big-bang; no romper rutas; no renombrar tablas sin necesidad; no borrar legacy sin reemplazo certificado; adapters > migraciones arriesgadas; preservar IDs/auditoría; rollback; tests; PROD solo con GO.

---

## 33. Fases

| Fase | Contenido | Gate |
|------|-----------|------|
| **F0** | Discovery / House Audit — sin refactor | Autorizado con este ADR + GO F0 |
| **F1** | Module Registry (Definition + OrgModule + deps + enable/disable + tests) | GO explícito |
| **F2** | Nav / auth consumen module + entitlement + RBAC | GO |
| **F3** | Products formalization | GO |
| **F4** | Inventory formalization | GO |
| **F5** | Sales formalization (Quotation→Order→Fulfillment) | GO |
| **F6** | Promotions extraction + snapshots | GO |
| **F7** | Membership compatibility (RELATIC + IIUS certified) | GO + gates |
| **F8** | External Application Registry (ESB, EP1, Planilla) | GO |

---

## 34. Gates de protección

| Gate | Regla |
|------|--------|
| RELATIC | No deploy Memberships si falla flujo Relatic |
| IIUS | No deploy que altere IIUS sin prueba específica |
| EP1 | No cambiar contratos Connected sin ADR/GO |
| ESB | No cambiar M2M fuera de ADR-037 |
| Planilla | No implementar dominio operativo de nómina en EN1 |

---

## 35. Invariantes

1. Module ≠ Feature ≠ Entitlement ≠ RBAC  
2. Organization Membership ≠ Association Membership  
3. Product ≠ Inventory · Price ≠ Promotion · Sales ≠ Payments  
4. Stock = consecuencia de movimientos  
5. Deshabilitar ≠ borrar  
6. Vertical/Product ≠ módulo necesariamente  
7. ESB y Planilla independientes; EN1 controla licencia de Planilla, no operación  
8. RELATIC/IIUS compatibilidad; no big-bang  

---

## 36. Resultado objetivo

EN1 como plataforma modular (Identity, CRM, Products, Inventory, Sales, Promotions, Payments, Subscriptions/Licensing, Memberships, Certificates, Integrations…).

Cada Organization activa solo lo requerido.

ESB / EPosOne / Planilla = aplicaciones con dominio propio; EN1 = control plane según contratos.

---

## 37. GO autorizado ahora

**NO** autorizar F1–F8 todavía.

**Sí** autorizar:

### GO ADR-038 F0 — EN1 Module & Domain Inventory

Reglas F0:

- inspección + documentación (+ tests de caracterización si necesarios);
- **cero** refactor funcional / eliminación / DDL destructivo / cambio de comportamiento;
- PROD solo lectura/inspección segura si se permite explícitamente.

Entregable F0: [EN1_ADR038_F0_MODULE_DOMAIN_INVENTORY.md](EN1_ADR038_F0_MODULE_DOMAIN_INVENTORY.md).

**STOP después de F0.** No refactor hasta revisión + GO F1.

---

## Changelog

| Fecha | Nota |
|-------|------|
| 2026-08-13 | Propuesto. F0 inventory autorizado. Decisión Planilla = EXTERNAL_CONTROLLED (no módulo ops EN1). |
