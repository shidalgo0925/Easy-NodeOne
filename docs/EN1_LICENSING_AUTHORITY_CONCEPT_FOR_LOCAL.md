# Concepto de licenciamiento EN1 → consumo desde productos (instrucción para Local / Prog2)

| Campo | Valor |
|-------|--------|
| Estado | Concepto / instrucción — **no implementar** |
| Audiencia | Local (Prog2) — EPosOne cliente / APK / runtime local |
| Relacionado | [`EN1_MULTIPRODUCT_COMMERCIAL_ARCHITECTURE_INSTRUCTION.md`](EN1_MULTIPRODUCT_COMMERCIAL_ARCHITECTURE_INSTRUCTION.md) · [`ADR-022-EN1-MULTIPRODUCT-COMMERCIAL-MODEL.md`](ADR-022-EN1-MULTIPRODUCT-COMMERCIAL-MODEL.md) |
| Alcance | Arquitectura y responsabilidades EN1 ↔ productos |

---

## Comentario de arquitectura (resumen)

**Sí:** el usuario debe poder **administrar** licencias/cupos desde la UI del producto (p. ej. EPosOne → Mi Plan).  
**No:** el producto **no es dueño** de la licencia ni decide ampliaciones, cobros ni cupos.

| Rol | Quién |
|-----|--------|
| Plataforma SaaS / Single Source of Truth | **EN1** |
| Productos (EPosOne, ePayroll, Marketplace, …) | **Consumidores** de la API de licenciamiento de EN1 |
| UI “Mi Plan / Licencias” en el producto | Vista especializada sobre datos de EN1 |
| Decisión (¿puede crear caja? ¿ampliar plan?) | **Solo EN1** |

Regla corta:

> **La interfaz vive en el producto. La decisión vive en EN1.**

---

## 1. EN1 no es “el producto”

EN1 es la **plataforma SaaS**. Dentro de EN1 viven:

- Cuentas  
- Organizaciones (tenants)  
- Catálogo de productos  
- Suscripciones  
- Facturación  
- Pagos  
- Licencias  
- Entitlements  
- Portal del cliente  

Los productos son **aplicaciones que consumen** esa plataforma.

---

## 2. Producto ≠ Licencia (conceptos distintos)

La licencia **no reemplaza** al producto. La jerarquía correcta es:

```text
Organización
        │
        ├── Producto: EPOSOne
        │      ├── Suscripción
        │      ├── Entitlement
        │      └── Licencias / cupos
        │
        ├── Producto: ePayroll
        │      ├── Suscripción
        │      ├── Entitlement
        │      └── Licencias / cupos
        │
        ├── Producto: EN1 Platform
        │      ├── Suscripción
        │      ├── Entitlement
        │      └── Licencias / cupos
        │
        └── Producto: …
```

### Por qué

Una organización puede comprar productos distintos en momentos distintos.

Ejemplo — **Mexican Food**:

| Producto | Estado |
|----------|--------|
| EPOSOne Business | ✓ contratado |
| ePayroll Starter | ✓ contratado |
| Marketplace | ✗ no |
| EM+Acción | ✗ no |
| EN1 Platform | ✗ no |

Cada uno tiene: su propio plan, vigencia, límites y licencias/consumo.

### La licencia depende del producto

No existe una licencia genérica de plataforma “para todo”.  
Existe licencia **por producto** (y por plan de ese producto).

**EPOSOne**

- Producto: EPOSOne  
- Plan: Business  
- Licencia / cupos (ejemplo): 3 cajas · 10 usuarios · 2 sucursales  

**ePayroll**

- Producto: ePayroll  
- Plan: Starter  
- Licencia / cupos (ejemplo): 150 empleados · 2 planillas · portal de empleados  

**EN1 Platform**

- Producto: EN1 Platform  
- Plan: Enterprise  
- Licencia / capacidades (ejemplo): CRM · Marketing · Agenda · Facturación  

### Jerarquía de conceptos (orden correcto)

```text
Producto
    ↓
Suscripción
    ↓
Plan
    ↓
Entitlement
    ↓
Licencia / Recursos
```

| Concepto | Significado |
|----------|-------------|
| **Producto** | Qué compró / puede comprar el cliente (EPOSOne, ePayroll, …) |
| **Suscripción** | Contrato vigente para ese producto en esa org |
| **Plan** | Starter, Business, Enterprise, etc. |
| **Entitlement** | Capacidades a las que tiene derecho |
| **Licencia / Recursos** | Consumo concreto (cajas, empleados, usuarios, dispositivos, …) |

Así se agregan productos futuros **sin cambiar el modelo de datos**.

---

## 3. Qué debe mostrar “Mis Productos” (Portal EN1)

**No** hacer que “Productos” dependa de la licencia.

Mostrar el catálogo comercial / estado de contratación de la organización, por ejemplo:

```text
Mis Productos

EPOSOne          Estado: Activo
ePayroll         Estado: Activo
EN1 Platform     Estado: No contratado
Marketplace      Estado: Disponible
EM+Acción        Estado: Disponible
```

- **Activo / contratado** → hay suscripción (trial o paga).  
- **Disponible / no contratado** → existe en catálogo, aún no comprado.  
- La **licencia** se ve al entrar al producto o en detalle de plan — no sustituye la fila del producto.

---

## 4. ¿Administrar licencias desde el producto base?

**Sí administrar en UI del producto. No ser dueño de la licencia.**

El usuario piensa en el producto:

- Entra a EPOSOne.  
- Quiere ver cajas, agregar caja, reemplazar tablet, generar código, ver dispositivos.  

Es natural que eso viva en el módulo EPOSOne.

Pero al pulsar **Agregar caja**:

1. EPOSOne **no** crea una licencia.  
2. EPOSOne **solicita a EN1**: “necesito ampliar / consumir recursos de este producto”.  
3. EN1 valida: plan, pago, cupos, facturación, suscripción.  
4. EN1 responde permitir / denegar / exigir upgrade.  

Mismo patrón para ePayroll (empleados/planillas) y cualquier producto futuro.

### Ejemplo UX (EPosOne)

```text
Mi Plan
  Business
  3 cajas · 2 en uso · 1 disponible
  [Agregar Caja]  [Generar Código]  [Ver Dispositivos]
```

- Capacidad disponible → EN1 autoriza → caja creada.  
- Sin cupo → EN1 indica ampliar plan / comprar.

---

## 5. Arquitectura de autoridad

```text
EN1 Platform
│
├── Cuentas
├── Organizaciones
├── Productos          ← catálogo comercial de plataforma
├── Suscripciones
├── Licencias
├── Entitlements
├── Pagos
├── Facturación
└── API de Licenciamiento
        │
        ├── EPOSOne
        ├── ePayroll
        ├── Marketplace
        ├── EM+Acción
        └── futuros productos
```

Cada producto **consume** la API de licenciamiento.  
Ningún producto es dueño de la licencia.

---

## 6. Instrucción para Local (Prog2)

### Asunto

Consumo del servicio de licenciamiento de EN1 desde EPosOne (cliente local / APK)  
**(No implementar código)**

### Contexto

Estamos revisando el modelo de licenciamiento de EN1 para soportar una plataforma **multiproducto**. El objetivo no es resolver únicamente EPOSOne, sino definir una arquitectura válida para todos los productos actuales y futuros.

### Principios

1. EN1 es la plataforma SaaS y la **única fuente de verdad** para: cuentas, organizaciones, productos, suscripciones, pagos, facturación, licencias y entitlements.  
2. Los productos **no son dueños** de las licencias; son consumidores de los servicios de licenciamiento de EN1.  
3. Cada producto puede tener pantalla “Mi Plan” o “Licencias”, pero es una **vista especializada** sobre información administrada por EN1.  
4. Producto ≠ Plan ≠ Entitlement ≠ Licencia/cupos (ver §2).  

### Objetivo

Analizar cómo debe consumir **EPosOne** (y, por extensión, cualquier cliente local) el servicio de licenciamiento de EN1.

**No** queremos duplicar lógica de negocio dentro de la APK.

### Analizar

1. Qué información necesita EPosOne para operar.  
2. Qué operaciones puede solicitar (consultar plan, generar código de aprovisionamiento, reemplazar dispositivo, etc.).  
3. Cuáles de esas operaciones deben ejecutarse **exclusivamente en EN1**.  
4. Qué datos pueden almacenarse localmente como **caché** y cuáles deben consultarse siempre a EN1.  
5. Cómo mantener funcionamiento **offline** sin perder la autoridad de EN1 sobre las licencias.  

### Entregable esperado

Propuesta de arquitectura y de responsabilidades entre EN1 y EPosOne (documento o análisis en chat), incluyendo:

- Matriz: operación → quién decide / quién muestra UI / qué se cachea.  
- Modelo offline: qué se permite sin red y qué queda bloqueado hasta sync con EN1.  
- Aprovisionamiento de dispositivo: cuándo se pide código a EN1 y qué valida EN1.  
- Qué **no** debe vivir en la APK (precios, upgrade, facturación, creación de cupos).  

### Restricciones

- **No** implementar código.  
- **No** modificar contratos HTTP.  
- **No** cambiar endpoints.  
- Presentar **únicamente** propuesta de arquitectura y responsabilidades.  

### Criterio de hecho

Queda claro que:

1. EN1 es SSOT de licencias.  
2. EPosOne solo consume y presenta.  
3. Offline no otorga autoridad de licencia.  
4. El modelo sirve para ePayroll y productos futuros sin inventar un motor de licencias por app.

---

## 7. Recomendación final

El usuario **sí** administra licencias desde la interfaz del producto (experiencia natural).  
La **autoridad** y la lógica de negocio permanecen en EN1.

Esa separación permite que todos los productos compartan un único motor de licenciamiento y facturación, sin duplicar reglas de negocio.
