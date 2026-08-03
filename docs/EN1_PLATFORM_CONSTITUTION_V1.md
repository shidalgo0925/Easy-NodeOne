# Constitución de Easy NodeOne Platform (EN1) — V1

| Campo | Valor |
|-------|--------|
| Documento | **Fundacional** — referencia obligatoria para todos los equipos |
| Estado | **Aprobado (GO)** — 1 ago 2026 · Ana / producto (chat) · referencia obligatoria para equipos |
| Ámbito | Núcleo de la plataforma EN1 (experiencia y modelo comercial de **toda** la plataforma, no solo EPosOne) |
| Precedencia | Congela la narrativa de plataforma. Si un ADR de producto contradice este documento en definición de EN1 / entidad raíz / producto / aplicación / compra, **prevalece esta constitución** tras aprobación. |
| No es | Constitución de EPosOne ([`EN1_POS_CONSTITUCION_V1.md`](EN1_POS_CONSTITUCION_V1.md) sigue siendo del dominio POS) |
| Relacionados | [`EN1_PLATFORM_MASTER_PLAN.md`](EN1_PLATFORM_MASTER_PLAN.md) · [ADR-012](ADR-012-ETS-ECOSYSTEM-ARCHITECTURE.md) · [ADR-013](ADR-013-PORTAL-ETS-PUNTO-ENTRADA.md) · [ADR-014](ADR-014-SUBSCRIPTION-REGISTRY.md) · [ADR-016](ADR-016-COMMERCIAL-LICENSING-V2-ENTITLEMENT.md) · [ADR-017](ADR-017-CUSTOMER-ENTRY-POINT-PRODUCT-PORTAL.md) · [ADR-019](ADR-019-ADMINISTRATIVE-HIERARCHY.md) · [ADR-022](ADR-022-EN1-MULTIPRODUCT-COMMERCIAL-MODEL.md) · [ADR-023 Trial/Grace](ADR-023-EPOSONE-TRIAL-SUBSCRIPTION-GRACE.md) · [ADR-024 Asistente de Inicio EPosOne](ADR-024-EPOSONE-START-ASSISTANT.md) · [`EN1_LICENSING_AUTHORITY_CONCEPT_FOR_LOCAL.md`](EN1_LICENSING_AUTHORITY_CONCEPT_FOR_LOCAL.md) |
| Restricción | Este documento **no implementa** código, endpoints ni UI. |
| Portal canónico | **`portal.easytech.services`** (preferido; evita `easytech.easytech.services`) |

---

## Frase constitutiva

> **EN1 es la plataforma de identidad, suscripciones y administración. Los productos son experiencias especializadas que comparten una única cuenta, una única organización y un único motor comercial. Los clientes no compran licencias; configuran una suscripción según sus necesidades. EN1 materializa esa configuración en entitlements, recursos y licencias técnicas. El cliente utiliza aplicaciones habilitadas por esas suscripciones.**

Esa frase resume la arquitectura completa y debe seguir siendo válida al agregar aplicaciones nuevas sin rediseñar el núcleo.

---

## Principios (congelados)

1. Una sola **cuenta**.  
2. Una sola **organización** (por contexto de negocio del tenant; ver §2).  
3. Dos **puertas de entrada** (EasyTech y EPosOne — u otras landings de producto).  
4. Un único **Portal** (`portal.easytech.services`).  
5. Un único **checkout** / motor comercial.  
6. El cliente **configura necesidades**, no planes.  
7. EN1 **recomienda** el plan.  
8. La **Organización existe antes del pago**.  
9. El pago (o el trial) crea/activa **Suscripción → Entitlement → Recursos**.  
10. Las **aplicaciones** consumen esos recursos.  
11. El **asistente** guía la configuración posterior al pago/trial operable.  
12. El **Dashboard completo** solo aparece cuando el onboarding ha finalizado.  
13. Solo EN1 es dueño del licenciamiento; las apps consumen la API.  
14. Producto nuevo = registro + planes + entitlements **sin** cambiar el modelo base.

---

## Por qué existe este documento

Si el concepto base no está claro en EN1, cada producto implementará una interpretación distinta.

EPosOne ha concentrado el desarrollo reciente; eso es normal. **EN1 no puede diseñarse desde EPosOne.** Debe diseñarse para que, en cinco años, se agregue un producto/aplicación nuevo sin replantear la arquitectura central.

**Pausa:** no implementar portal/checkout/aprovisionamiento en contra de este documento hasta su aprobación.

---

## 1. ¿Qué es EN1?

### Decisión

**EN1 (Easy NodeOne) es la plataforma SaaS de identidad, suscripciones y administración del ecosistema ETS.**

| ¿Es…? | Respuesta |
|-------|-----------|
| ¿Una plataforma SaaS? | **Sí.** Definición primaria. |
| ¿Un ERP? | **No como producto vendible.** Puede hospedar shell administrativo. |
| ¿Un marketplace de aplicaciones? | El Portal puede mostrar catálogo; eso no redefine EN1. |
| ¿Todo lo anterior? | **No.** |

**ETS** = marca / ecosistema con el que el cliente se relaciona comercialmente.  
**EN1** = infraestructura (cuenta, org, suscripciones, entitlements, licencias técnicas, Portal).  
**Productos / Aplicaciones** = experiencias especializadas.

### Qué NO es EN1

- No es EPosOne.  
- No es la landing comercial (las landings conducen al Portal).  
- No es dueño del dominio operativo de cada aplicación (cobro en caja, nómina, etc.).

---

## 2. Entidad raíz y capas de identidad

```text
Cuenta
    │
    ▼
Organización
    │
    ▼
Suscripciones          ← comerciales (producto + plan materializado)
    │
    ▼
Aplicaciones habilitadas   ← lo que el usuario utiliza día a día
```

| Capa | Rol |
|------|-----|
| **Cuenta** | Login, verificación de correo, facturación / métodos de pago |
| **Organización** | Identidad del **negocio** (tenant). Activo raíz. Existe **antes** del pago |
| **Suscripción** | Contrato comercial org ↔ producto (configurado por necesidades) |
| **Aplicación** | Experiencia que el usuario abre y usa (EPosOne, CRM, Agenda, …) |

### Organización antes del pago (obligatorio)

```text
Registro
  → Verificar correo
  → Crear Organización
  → Portal
  → Configurador  (o “Probar 15 días” / “Comprar ahora”)
  → Pago o Trial
  → Suscripción → Entitlement → Recursos
  → Asistente de configuración
  → (solo al terminar) Dashboard
```

**Prohibido:** crear la Organización como efecto del pago.

La Organización permite volver después, guardar cotización, iniciar trial y comprar otro producto más adelante **sin** re-registrarse.

### Ejemplo de vista (usuario)

```text
Organización: Mexican Food

Aplicaciones
  ✓ EPosOne
  ✓ CRM
  ✓ Agenda
  ○ ePayroll
  ○ Marketplace
```

✓ = habilitada por suscripción/entitlement.  
○ = disponible para contratar / no habilitada.

---

## 3. Producto vs Aplicación vs Módulo

| Término | Definición | Idioma |
|---------|------------|--------|
| **Producto** | Unidad **comercial** del catálogo (lo que se configura/compra/suscribe) | Interno + Portal “contratar” |
| **Aplicación** | Unidad **de uso**: lo que el usuario abre y opera | Usuario final |
| **Módulo** | Capacidad dentro de una app o del shell; no se vende sola salvo elevación a Producto | Interno |
| **Plan** | Escala comercial **recomendada por EN1** (Starter / Business / …) | Interno; el cliente no lo elige |
| **Entitlement** | Cupos y features efectivos | Interno |
| **Licencia técnica / recurso** | Resultado (cajas, códigos, dispositivos, …) | Interno; el cliente no “compra licencias” |
| **Catálogo operativo** (`/admin/services`, SKUs Contador) | Lo que la org vende a *sus* clientes | Operación; **no** catálogo ETS |

### Regla

- El cliente **compra/configura una suscripción** (sobre un Producto).  
- El cliente **utiliza Aplicaciones** habilitadas por esa suscripción (una suscripción puede habilitar una o varias apps).  
- **No** confundir catálogo operativo de la org con productos ETS.

### Tabla de clasificación

| Nombre | Comercial | Uso | Notas |
|--------|-----------|-----|--------|
| **EPosOne** | Producto | Aplicación | Landing + configurador propios |
| **ePayroll** | Producto | Aplicación | |
| **EN1 Platform** | Producto (paquete) | Habilita apps CRM, Agenda, Membresías, … | Hasta elevar apps a producto propio |
| **CRM** | (vía EN1 Platform u otro) | **Aplicación** | Usuario la ve como app |
| **Agenda / Citas** | (vía EN1 Platform u otro) | **Aplicación** | |
| **Membresías** | (vía EN1 Platform u otro) | **Aplicación** | |
| **Servicios** (`/admin/services`) | — | Módulo operativo | No es producto ETS ni app de catálogo Portal |
| **Marketplace** | Producto futuro o vitrina Portal | App / superficie | |
| **EM+Acción, EClassOne, Odoo** | Fuera o propio | — | No forzar modelo EPosOne |

---

## 4. Dos puertas, un solo proceso de compra

```text
Landing EPosOne          Landing EasyTech (u otra)
        │                        │
        └───────────┬────────────┘
                    ▼
           Crear cuenta EN1
                    ▼
           Verificar correo
                    ▼
           Crear Organización
                    ▼
        Portal Comercial EN1
        portal.easytech.services
```

A partir de ahí el usuario está autenticado; **solo cambia el contexto**:

| Origen | Qué ve |
|--------|--------|
| Landing **EPosOne** | Solo configurador / trial-compra de EPosOne. **No** ve ePayroll ni Marketplace en ese momento |
| Landing **EasyTech** | Catálogo de productos/aplicaciones → luego configurador del elegido |

Un solo Portal. Un solo checkout. Un solo motor comercial.

Dominio: **`portal.easytech.services`**. No usar `easytech.easytech.services`.

---

## 5. Configurador (idioma del comerciante)

### Reglas

1. **Nunca** preguntar lenguaje técnico interno (plan, entitlement, Standalone, POS hierarchy, etc.).  
2. El usuario **no elige** Starter / Business / Enterprise.  
3. EN1 **recomienda** el plan y el precio según la configuración.  
4. Modalidad de despliegue = opción de **dónde trabaja**, no un producto distinto.

### Pasos canónicos (EPosOne; el patrón aplica a otros productos)

**Paso 1 — ¿Qué tipo de negocio tienes?**  
Restaurante · Cafetería · Tienda · Farmacia · Otro  

**Paso 2 — ¿Cuántas cajas utilizarás al mismo tiempo?**  
1 · 2 · 3 · 4 · …  

**Paso 3 — ¿Cómo prefieres pagar?**  
Mensual · Anual  

**Paso 4 — ¿Dónde trabajarás?**  
- Solo en esta tablet  
- Sincronizado con EN1  

**No usar la palabra “Standalone”.**  
“Solo en esta tablet” = modalidad local.  
“Sincronizado con EN1” = modalidad integrada.  
Misma suscripción / mismo producto; distinta modalidad de despliegue.

**Paso 5 — Recomendación EN1 (no pregunta de plan)**  

```text
Te recomendamos:
  EPosOne Business
  3 cajas
  Pago anual
  USD xx.xx

[ Continuar ]
```

### Barra de progreso (usuario)

```text
1. Cuenta ✓
2. Organización ✓
3. Configuración
4. Pago
5. Instalar
```

---

## 6. Trial integrado

Después de organización (y contexto de producto), el usuario elige:

- **Probar 15 días**  
- **Comprar ahora**  

No obligar a pagar de inmediato. El trial crea/activa suscripción en estado trial + entitlement acotado + recursos mínimos según reglas del producto. Misma tubería que la compra; distinto disparador.

---

## 7. Después del pago o al activar trial operable

### Prohibido

Mostrar el **Dashboard completo** como primera pantalla.

### Obligatorio

Mostrar el **asistente de onboarding** hasta completar:

```text
Bienvenido. Comencemos.

✓ Organización
□ Crear sucursal
□ Crear POS
□ Crear Caja
□ Instalar EPosOne   (código de aprovisionamiento + descarga)
```

(Los pasos concretos son del dominio EPosOne; otros productos tendrán su propio asistente con el mismo principio.)

Solo cuando el onboarding está **finalizado** aparece el Dashboard completo.

Los códigos de aprovisionamiento existen **después** de suscripción + recursos (p. ej. caja), no en el checkout.

---

## 8. Qué compra el cliente (lenguaje)

| El cliente dice / hace | EN1 materializa |
|------------------------|-----------------|
| Configura necesidades (rubro, cajas, ciclo, dónde trabaja) | Recomienda plan |
| Prueba 15 días o paga | Suscripción + Entitlement |
| — | Recursos y **licencias técnicas** |
| Usa | **Aplicaciones** habilitadas |

> El usuario no compra una licencia. Configura una suscripción. La licencia técnica es el resultado.

---

## 9. Dueño del licenciamiento

**Solo EN1** es SSOT de suscripciones, entitlements, cupos y licencias técnicas.

Las aplicaciones pueden mostrar “Mi plan / Mis cajas / Agregar capacidad”, pero **solicitan** a EN1; no crean ni amplían licencias por sí solas.

> La interfaz puede vivir en la aplicación. La decisión vive en EN1.

---

## 10. Incorporar producto / aplicación nueva

Sin modificar el modelo base:

1. Registrar **Producto** (si se vende) en Product Registry.  
2. Registrar **Aplicación(es)** técnicas (App Registry).  
3. Mapear Producto → Aplicaciones que habilita.  
4. Definir reglas del configurador (preguntas en idioma del cliente → recomendación de plan).  
5. Planes → entitlements (cupos/features del dominio).  
6. Suscribir orgs; materializar entitlements y recursos.  
7. Portal: catálogo + Mis aplicaciones / Mis productos.  
8. Asistente post-activación propio del dominio.  
9. Consumir solo API de licenciamiento EN1.  
10. No inventar un segundo motor comercial ni org “del producto”.

---

## 11. Niveles administrativos (ADR-019)

```text
ETS Super Admin → Plataforma EN1 → Organización → Suscripciones / Apps → Operación
```

---

## 12. Relación con ADRs

| Documento | Rol |
|-----------|-----|
| ADR-012 / 013 / 017 | Ecosistema, Portal, entrada — alineados; dominio preferido **portal.easytech.services** |
| ADR-014 / 016 | Suscripción / Entitlement — alineados; licencia = resultado |
| ADR-022 | Org como raíz — **ratificado** por §2 |
| Constitución EN1-POS | Solo dominio EPosOne |
| Master Plan | Roadmap; no redefine §1–§8 en contra |

---

## 13. Criterio de aprobación

**Cumplido (GO 1 ago 2026).** Quedó confirmado:

1. Frase constitutiva y principios §.  
2. Cuenta → Org → Suscripciones → **Aplicaciones**.  
3. Org antes del pago; trial integrado.  
4. Configurador sin planes ni jerga técnica; EN1 recomienda.  
5. Asistente post-pago/trial; Dashboard solo al terminar onboarding.  
6. Un Portal, dos puertas, un checkout.

Estado operativo: **Aprobado**. Todos los diseños de portal, checkout, licenciamiento y onboarding deben alinearse a este documento. Implementación de código solo con GO explícito de tarea.

---

## 14. Próximo paso

Formalizar (opcional) ADR comercial corto: *Commercial Entry, Configurator & Onboarding*. **Sin código** hasta GO de implementación de una tarea concreta.

---

*Aprobado 1 ago 2026 — constitución de experiencia de plataforma EN1. Sin implementación en este GO.*
