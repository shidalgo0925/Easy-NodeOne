# ADR-015 — Arquitectura de Navegación de EN1

| Campo | Valor |
|-------|--------|
| ID | ADR-015 |
| Título | Arquitectura de Navegación de EN1 |
| Estado | **Propuesta congelada** — 25 jul 2026 · **Fase 2 implementada en Dev** (`NODEONE_NAV_TAXONOMY`, default `v1`) |
| Ámbito | EN1 Platform · shell ERP · launcher classic / apps |
| Relacionados | [`nav_menu.py`](../backend/nodeone/core/nav_menu.py) · SaaS (`saas_module` / `saas_org_module`) · RBAC · manifests plataforma · [ADR-006](ADR-006-EPOSONE-OPERATION-VS-ADMIN.md) · [Sprint UX apps](EN1_PLATFORM_SPRINT_UX_TRANSICION_APPS.md) |
| Implementación | **Fase 2 en Dev** — `NODEONE_NAV_TAXONOMY=v1|v2` (+ overrides por org). Código: `nav_menu.py` · drop-in systemd Dev puede fijar `v2`. Default sin env: **v1**. |

---

## Frase de apertura

**La navegación es un contrato entre el producto y el usuario. El código puede evolucionar libremente; la experiencia del usuario debe permanecer consistente.**

---

## Decisión

La navegación de EN1 **no representa el código**.  
La navegación de EN1 **representa el modelo de negocio**.

Ese modelo de negocio debe ser **estable durante muchos años**.

Mañana podrá reescribirse un módulo completo sin que el usuario tenga que aprender de nuevo dónde están las cosas.

Este ADR define la **arquitectura de navegación** de EN1: principio, reglas de diseño, mapa de dominios, matriz de compatibilidad con la implementación actual, cutover seguro y criterios de aceptación.

**No** es una refactorización de dominio, ni una migración de datos, ni un cambio de rutas, permisos, SaaS, RBAC, endpoints, blueprints, modelos o base de datos.

El único cambio autorizado en la implementación futura de este ADR es la **organización visual y funcional del menú** (etiquetas, agrupación, orden, composición del sidebar, estado activo).

---

## Principio central

Cada entrada principal del launcher representa un **dominio funcional estable** y comprensible para el usuario, no la estructura técnica del repositorio.

Los agrupadores genéricos siguientes **desaparecen** de la navegación v2:

| Agrupador v1 (eliminar) | Motivo |
|-------------------------|--------|
| Comercial | Mezcla CRM, Ventas, Eventos, Membresías, Marketing |
| Operaciones | Agrupador técnico, no dominio de negocio |
| Finanzas | Ambiguo; el usuario busca Facturación / Cobros |
| Inteligencia | Analítica debe ser entrada directa |
| Sistema | Plataforma / Configuración deben ser entradas directas |

Esos nombres **no** son módulos licenciables ni términos que el usuario busque.

---

## Principios de diseño de la navegación

### Regla 1 — Dominios de negocio

La navegación representa **dominios de negocio**.

Nunca representa:

- nombres de paquetes  
- módulos Python  
- blueprints  
- namespaces  
- archivos  
- implementaciones técnicas  

### Regla 2 — Dominios estables

Los **dominios son estables**. Las **funcionalidades evolucionan dentro** de esos dominios.

Ejemplo — Inventario:

```text
2026
├── Productos para conteo
└── Conteos físicos

2027
├── Productos para conteo
├── Existencias
├── Movimientos
├── Transferencias
├── Lotes
└── Conteos físicos

2028
├── …
├── Almacenes
├── Picking
└── Auditorías
```

El usuario **nunca vuelve a aprender el menú** porque el nombre del dominio no cambia.

### Regla 3 — Sin dominios vacíos

Si un dominio no posee capacidades reales implementadas, **no aparece**.

### Regla 4 — Sin funcionalidades huérfanas

Toda funcionalidad pertenece a **exactamente un** dominio funcional.

Ejemplo: Conteos físicos pertenecen a **Inventario**. No existe un dominio llamado «Conteos».

### Regla 5 — No exponer deuda técnica

| Interno (código / SaaS) | Usuario ve |
|-------------------------|------------|
| `marketing_email` | Marketing |
| `contador` | Inventario |
| ítems bajo `finanzas` | Facturación **o** Cobros (según corresponda) |
| `accounting_core` (blueprint) | Nunca como nombre de menú; ver decisión Contabilidad |

### Regla 6 — Crecen las capacidades, no los nombres

Las capacidades pueden crecer. Los **dominios no cambian de nombre**.

### Regla 7 — Un solo estado activo

En el sidebar / subnav del módulo activo solo hay **un** ítem resaltado a la vez.

### Regla 8 — Compatible con SaaS y RBAC existentes

La visibilidad sigue siendo:

```text
visible = SaaS enabled ∧ permisos RBAC ∧ endpoint registrado ∧ (flags de contexto)
```

Este ADR **no reemplaza** el sistema de módulos SaaS ni RBAC; solo reorganiza **cómo se presenta**.

---

## Alcance obligatorio

### Sí (implementación futura bajo este ADR)

- Etiquetas visibles  
- Agrupación de áreas en el launcher  
- Orden del launcher  
- Composición del sidebar / subnav por dominio  
- Estado activo de navegación  
- Flag de cutover `NODEONE_NAV_TAXONOMY=v1|v2` (o equivalente por organización)  

### No

- URLs / rutas  
- Endpoints / blueprints  
- Modelos / base de datos  
- Permisos RBAC  
- Códigos SaaS / licencias / manifests  
- Lógica de negocio  
- Unificación de maestros (p. ej. Contactos ↔ Usuarios, catálogo Ventas ↔ catálogo Conteos)  

---

## Mapa actual (v1) — resumen

Fuente: `backend/nodeone/core/nav_menu.py`.

**Top-level:** Tienda · Contactos · EPosOne (atajo temporal).

**Grupos colapsables:**

| Grupo | Áreas |
|-------|--------|
| Comercial | CRM, Taller, Ventas, Membresías, Eventos, Email marketing |
| Operaciones | Agenda, Educación, Certificados, Mis Certificados, Contador *(grupo gated por SaaS `operaciones`)* |
| Finanzas | Finanzas *(Facturas, CxC, FE, Contabilidad)* |
| Inteligencia | Analítica |
| Sistema | Plataforma |

Configuración, Permisos y Matriz Odoo viven fuera del sidebar principal como áreas auxiliares.

---

## Mapa v2 — dominios visibles

Orden base sugerido para validación (puede ajustarse por producto/tenant **sin cambiar la taxonomía**):

```text
CRM
Contactos
Marketing
Ventas
Facturación
Cobros
Inventario
Tienda
EPosOne
Taller
Eventos
Membresías
Agenda
Certificados
Educación
Analítica
EPayroll
Configuración
Plataforma          ← siempre al final; solo admin de plataforma
```

### Tabla dominio → origen

| Dominio visible (v2) | Origen actual (`area_id`) | Criterio |
|----------------------|---------------------------|----------|
| CRM | `crm` | Mantener funcionalidades actuales |
| Contactos | `contactos` | Maestro de personas y organizaciones |
| Marketing | `marketing_email` | Solo capacidades existentes (email) |
| Ventas | `ventas` | Cotizaciones y catálogo **comercial** |
| Facturación | subconjunto de `finanzas` | Facturas + factura electrónica |
| Cobros | subconjunto de `finanzas` | Cuentas por cobrar (+ pagos solo si se reubican visualmente; ver matriz) |
| Inventario | `contador` | Productos para conteo + conteos físicos (Modecosa) |
| Tienda | `tienda` | Mantener |
| EPosOne | `eposone` | Independiente (app-producto) |
| Taller | `taller` | Independiente |
| Eventos | `eventos` | Independiente |
| Membresías | `membresias` | Independiente — **no** ligado a Eventos |
| Agenda | `agenda` | Según SaaS `appointments` + permisos |
| Certificados | `certificados` | Emisión + Plantillas + Mis Certificados (un dominio) |
| Educación | `educacion` | Independiente |
| Analítica | `analitica` | Entrada directa (sin grupo Inteligencia) |
| EPayroll | `epayroll` | **No** denominar «Recursos Humanos» completo |
| Configuración | `config` | Organización, acceso, fiscal transversal |
| Plataforma | `plataforma` | Solo administrador de plataforma |

**No mostrar aún:** Compras, Producción, Help Desk, Activos, RRHH genérico.

**Contabilidad:** no declarar dominio completo sin validación de producto y uso (sección dedicada).

---

## Reglas específicas de dominio

### Inventario

Inventario **no** es un rename cosmético de «módulo inventario completo».

- **Dominio funcional visible:** Inventario.  
- **Capacidad inicial real:** catálogo usado para conteos + conteos físicos (Modecosa).  
- **Identificador interno:** `contador` (sin cambio).  

Submenú inicial (labels UX; mismos endpoints actuales):

```text
Inventario
├── Inicio
├── Productos para conteo      ← catálogo Contador
├── Sesiones de conteo
├── Conteos físicos
└── Importaciones
```

**Explícito:**

- El catálogo comercial de **Ventas** (`admin/services` / Productos del dropdown Catálogo) **no se mueve**.  
- El catálogo de **Conteos** sí se presenta bajo Inventario.  
- **No** se unifican modelos, datos ni maestros en este ADR.  

### Facturación y Cobros

Área actual `finanzas` se presenta como **dos áreas de navegación**:

```text
finanzas (área actual)
        ↓
Presentación v2:
├── Facturación   (area_id nav: facturacion)
└── Cobros        (area_id nav: cobros)
```

Ambas reutilizan los mismos `NavAreaItem`, endpoints, permisos y controles SaaS.  
**No** se duplica lógica ni se crean capacidades de negocio nuevas.

### Contactos y Usuarios

No fusionar administración de usuarios dentro de Contactos.

| Presentación | Contenido |
|--------------|-----------|
| **Contactos** | Personas y organizaciones |
| **Configuración** | Usuarios, Roles, Permisos, Accesos |

Evolución futura (fuera de este ADR): un contacto podrá vincularse a una cuenta de usuario.  
**No** se cambia el modelo ni se oculta la administración de accesos.

### Contabilidad (decisión pendiente con evidencia)

Hoy existe un ítem de menú **Contabilidad** → `accounting_core.entries_list`, visible si:

- permiso `payments.view`  
- cadena SaaS `accounting_core` (+ `sales`)  
- endpoint registrado  

Hallazgos en Dev (25 jul 2026, orientativos; **validar en cada silo antes de cutover**):

| Señal | Observación |
|-------|-------------|
| SaaS `accounting` | Habilitado en orgs de ejemplo (p. ej. 1, 2) |
| `journal_entry` | 0 filas en Dev al momento del análisis |
| Plan de cuentas | Tabla `account` con datos seed |

**El ADR no autoriza ocultar Contabilidad por suposición.**

Antes de la implementación v2, completar checklist:

1. Endpoints contables visibles hoy  
2. Permisos que los exponen  
3. Códigos SaaS involucrados  
4. Tenants con acceso en Dev / staging / Relatic / IIUS  
5. Uso real (asientos, favoritos, enlaces)  
6. Impacto de no mostrarlos en launcher v2  

Opciones de producto (elegir una tras el checklist):

| Opción | Descripción |
|--------|-------------|
| A | Permanecer temporalmente en compatibilidad v1 / ítem honesto («Asientos») |
| B | Oculto solo en navegación v2; rutas siguen activas |
| C | Visible bajo Configuración o Cobros con etiqueta honesta |
| D | Decisión posterior de producto — no cutover v2 global hasta resolver |

---

## Matriz de compatibilidad (label v2 ↔ implementación actual)

Leyenda SaaS: código en `saas_module` / guard efectivo. Permiso: el usado por el `visible` del ítem (puede haber más en subpantallas).

### Dominios launcher

| Label v2 | `area_id` (nav) | SaaS code(s) | Permiso / guard principal | Endpoints reutilizados (representativos) | Visible para | Observaciones |
|----------|-----------------|--------------|---------------------------|------------------------------------------|--------------|---------------|
| CRM | `crm` | `crm` | CRM / reports según ítem | `admin_crm_*` | Tenant con CRM on | Sin cambio de rutas |
| Contactos | `contactos` | `contacts` | endpoint contacts | `contacts_admin.contacts_*` | Módulo contacts | Maestro; no es Usuarios |
| Marketing | `marketing_email` | `marketing_email` | endpoint marketing | `admin_marketing` | Marketing email on | Label UX; id interno igual |
| Ventas | `ventas` | `sales` | `payments.view` (área) | `admin_sales_quotations`, catálogo admin | Sales on | Incluye Catálogo **comercial** |
| Facturación | `facturacion` *(nuevo id nav)* | `sales`, `efactura` | `payments.view` / efactura | `admin_accounting_invoices*`, `efactura_admin.efactura_emissions` | Según ítem | Split visual desde `finanzas` |
| Cobros | `cobros` *(nuevo id nav)* | cadena `accounting_core`+`sales` | `payments.view` + CxC | `accounting_core.receivables_*` | CxC visible hoy | No inventar «Pagos» aquí si siguen en Config |
| Inventario | `contador` | `contador` | `contador.*` | `contador.contador_*` | Contador on | Labels UX; no inventario completo |
| Tienda | `tienda` | `appointments` *(guard tienda)* | endpoint services | `services.list` | Según `_v_tienda` | Top-level hoy |
| EPosOne | `eposone` | `eposone` | eposone | `eposone.*` | EPosOne on | App independiente |
| Taller | `taller` | `workshop` | workshop | workshop admin | Workshop on | Independiente |
| Eventos | `eventos` | `events` | `reports.view` | events / admin_events | Events on | Independiente |
| Membresías | `membresias` | `memberships` | `memberships.view` | `admin_memberships`, `admin_plans`, … | Memberships on | Independiente |
| Agenda | `agenda` | `appointments` | appointments | appointments / admin_appointments | Appointments on | |
| Certificados | `certificados` | `certificates` (+ portal con `events`∨`certificates`) | admin / portal | `admin_certificate_*`, `certificates_page.*` | Tenant / usuario | Dominio único: Emisión, Plantillas, Mis Certificados |
| Mis Certificados | `mis_certificados` *(sin sidebar)* | — | — | mismos endpoints portal | — | Highlight → `certificados` |
| Educación | `educacion` | `academic` | academic nav | `academic_admin.*` | Academic on | |
| Analítica | `analitica` | `analytics` | `analytics.view` | `admin_analytics*` | Analytics on | Sin grupo Inteligencia |
| EPayroll | `epayroll` | `epayroll` | epayroll | `epayroll.epayroll_home` | EPayroll on | No llamar RRHH |
| Configuración | `config` | varios | `system.settings.view` + | `admin_company_setup`, taxes, `payments_admin.admin_payments`, users… | Admin tenant | Usuarios/accesos aquí |
| Plataforma | `plataforma` | — | platform admin | `admin_organizations_*`, `admin_saas_*`, … | Solo platform admin | Siempre al final |

### Ítems clave dentro de dominios (detalle)

| Label v2 (ítem) | Dominio | Endpoint(s) | SaaS / permiso | Observaciones |
|-----------------|---------|-------------|----------------|---------------|
| Cotizaciones | Ventas | `admin_sales_quotations` | `sales` | |
| Productos (comercial) | Ventas → Catálogo | `admin_services_catalog.admin_services` | services / appointments según guard catálogo | **No** mover a Inventario |
| Facturas | Facturación | `admin_accounting_invoices` | `sales` + `payments.view` | Hoy bajo Finanzas → Cobro |
| Fact. electrónica | Facturación | `efactura_admin.efactura_emissions` | `efactura` | |
| Cuentas por cobrar | Cobros | `accounting_core.receivables_list` | accounting_core + sales | |
| Pagos (admin) | Configuración (hoy) | `payments_admin.admin_payments` | `payments` + `payments.manage` | Hoy en Config → Fiscal; **no inventar** en Cobros en v2 salvo decisión explícita posterior |
| Contabilidad / Asientos | *pendiente* | `accounting_core.entries_list` | accounting_core + sales + `payments.view` | Ver sección Contabilidad |
| Productos para conteo | Inventario | `contador.contador_catalogo` | `contador` | |
| Sesiones / Conteos | Inventario | `contador.contador_sesiones` (+ detalle) | `contador` | |
| Importaciones | Inventario | `contador.contador_importar*` | `contador.admin` | |
| Campañas | Marketing | `admin_marketing` | `marketing_email` | |

---

## Elementos renombrados / divididos / eliminados (solo UI)

| Tipo | v1 | v2 |
|------|----|----|
| Rename label | Email marketing | Marketing |
| Rename label | Contador | Inventario |
| Split área | Finanzas | Facturación + Cobros |
| Eliminar agrupador | Comercial | — |
| Eliminar agrupador | Operaciones | — *(dejar de usar SaaS `operaciones` como taxonomía de grupo)* |
| Eliminar agrupador | Finanzas | — |
| Eliminar agrupador | Inteligencia | — |
| Eliminar agrupador | Sistema | — |
| Entrada directa | Analítica (bajo Inteligencia) | Analítica |
| Entrada directa | Plataforma (bajo Sistema) | Plataforma |

---

## Estrategia de implementación (sin código en este ADR)

### Cutover

```text
NODEONE_NAV_TAXONOMY=v1   # default: menú actual
NODEONE_NAV_TAXONOMY=v2   # dominios funcionales
```

Equivalente por organización permitido (misma taxonomía, distinto orden/activación).

Debe permitir:

- activar v2 por tenant  
- volver a v1 **sin migraciones**  
- comparar ambos menús  
- despliegue gradual  

### Orden sugerido de validación de tenants

1. Galenus  
2. Easy Technology Services  
3. Relatic  
4. IIUS  

El orden final depende del riesgo tras revisar uso real (especialmente Contabilidad y Contador/Inventario).

### Fases

| Fase | Entregable |
|------|------------|
| 1 | Este ADR + matriz (hecho) |
| 2 | Implementar taxonomía v2 detrás del flag (solo `nav_menu` / shell) |
| 3 | Cutover tenant a tenant |
| 4 | Default v2; v1 como rollback |

Cada dominio nuevo futuro (Compras, RRHH, Producción, Help Desk, Activos, …) **debe cumplir estas reglas** antes de aparecer en el menú.

---

## Riesgos

| Riesgo | Mitigación |
|--------|------------|
| Usuarios acostumbrados a Comercial/Finanzas | Flag v1; capacitación corta; cutover gradual |
| Contabilidad oculta por error | Checklist obligatorio; opciones A–D |
| Confundir Inventario con catálogo Ventas | Texto explícito en ADR + labels «Productos para conteo» |
| SaaS `operaciones` huérfano | Documentar deprecación como interruptor de grupo; no bloquear v2 |
| Favoritos a rutas | Rutas no cambian — riesgo bajo |
| Modo launcher `apps` vs `classic` | Misma taxonomía de dominios; shell apps sigue ADR-015 |

---

## Rollback

1. `NODEONE_NAV_TAXONOMY=v1` (global o por org).  
2. Sin migraciones, sin cambios de datos.  
3. Criterio: menú v1 idéntico al pre-cutover.  

---

## Criterios de aceptación

1. El usuario encuentra **Facturación** sin entrar a Finanzas.  
2. El usuario encuentra **CRM, Marketing, Ventas e Inventario** directamente.  
3. **Inventario** muestra únicamente capacidades reales de conteo.  
4. No aparecen dominios vacíos.  
5. Desactivar un módulo SaaS sigue ocultando su entrada.  
6. No cambia ninguna URL.  
7. No cambia ningún permiso.  
8. No se crean secciones sin elementos visibles.  
9. Solo existe un estado activo en el sidebar.  
10. Eventos, Membresías, Taller, Tienda/EPosOne y Educación no pierden visibilidad cuando correspondan.  
11. La navegación v1 puede restaurarse inmediatamente.  

---

## Decisiones pendientes

| ID | Tema | Owner |
|----|------|--------|
| D-1 | Destino final del ítem Contabilidad / Asientos (opciones A–D) | Producto + evidencia por silo |
| D-2 | ¿Reubicar visualmente «Pagos» (`payments_admin`) hacia Cobros en una fase 2b? | Producto (hoy permanece en Configuración) |
| D-3 | Deprecación formal del SaaS code `operaciones` como gate de grupo | Plataforma |
| D-4 | Orden por defecto vs overrides por tenant/producto | Plataforma |
| D-5 | Fecha de default v2 en Dev / staging / clientes | Ops + Producto |

---

## Consecuencias

### Positivas

- Contrato estable usuario ↔ producto durante años.  
- Nuevos módulos se agregan **dentro** de dominios sin reorganizar el menú.  
- Alineado con multi-tenant y SaaS existente.  
- Bajo riesgo técnico (solo capa de navegación).  

### Negativas / costos

- Doble mantenimiento v1/v2 durante el cutover.  
- Requiere disciplina de producto (no crear dominios vacíos ni labels engañosos).  
- Contabilidad y Pagos exigen cierre de D-1 / D-2 antes del cutover amplio.  

---

## Referencia de implementación actual

| Artefacto | Rol |
|-----------|-----|
| `backend/nodeone/core/nav_menu.py` | Definición v1 de `APP_AREAS` y `_SIDEBAR_LAUNCHER_GROUPS` |
| `backend/nodeone/services/saas_catalog_defaults.py` | Catálogo SaaS |
| `backend/nodeone/core/platform/launcher.py` | Modo classic / apps; mapa área → app |
| `/admin/saas-modules` | Activación por tenant |

Cualquier PR que implemente v2 debe citar este ADR y limitar el diff a navegación + flag de cutover.

---

*Documento congelado como estándar de arquitectura de navegación EN1. Implementación de código: fuera de este ADR; requiere GO explícito de implementación.*
