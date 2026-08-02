# INSTRUCCIÓN PARA PROG1 (CODITO)

## Asunto

Revisión de la arquitectura comercial y de aprovisionamiento de EN1 como plataforma multiproducto  
**(No implementar código)**

| Campo | Valor |
|-------|--------|
| Estado | Instrucción abierta — análisis / propuesta |
| Alcance | Solo Dev EN1 (lectura + documento de arquitectura) |
| Relacionado | [`ADR-022-EN1-MULTIPRODUCT-COMMERCIAL-MODEL.md`](ADR-022-EN1-MULTIPRODUCT-COMMERCIAL-MODEL.md) (propuesta previa; no sustituye este análisis) |
| Entregable esperado | Documento de arquitectura (chat o `docs/EN1_MULTIPRODUCT_COMMERCIAL_ARCHITECTURE_REVIEW.md`) |

---

## Contexto

Durante la revisión del P0 de EPOSOne surgió una duda sobre el modelo comercial y el flujo de adquisición de productos.

La discusión inicial se centró en EPOSOne, pero **esa no es la pregunta correcta**.

La pregunta correcta es:

> ¿Cómo debe funcionar EN1 cuando un cliente compra uno o varios productos a lo largo del tiempo?

No queremos una respuesta enfocada únicamente en EPOSOne. Queremos validar que la arquitectura soporte una **plataforma SaaS multiproducto**.

Patrón de referencia (plataformas SaaS maduras: Microsoft 365, Salesforce, marketplaces SaaS):

- El producto **nunca** vende ni licencia por sí mismo.
- Todo pasa por un **portal central** de cuentas, suscripciones y licencias.

Flujo típico:

```text
Registro de cuenta
        ↓
Crear organización (tenant)
        ↓
Comprar producto
        ↓
Pago
        ↓
Suscripción activa
        ↓
Asignación de licencias/cupos
        ↓
Descargar / instalar producto
        ↓
Activación del dispositivo o usuario
```

**Microsoft 365:** no vende Word desde Word. El cliente crea tenant → compra Microsoft 365 → se asignan licencias → descarga Office → inicia sesión → Office consulta el servicio de licencias.

**Salesforce:** primero existe la Org; después se compran Sales Cloud, Service Cloud, etc. Todo se administra desde el portal de la organización.

**EN1 (hipótesis a validar o refutar):**

```text
Cliente
  ↓
Cuenta EN1
  ↓
Crear Organización
  ↓
Portal de Productos
  ↓
Comprar EPOSOne (u otro producto)
  ↓
Pago
  ↓
Suscripción activa
  ↓
Producto en "Mis Productos"
  ↓
Descargar APK / Abrir app
  ↓
Administrar producto en EN1
```

Dentro de EPOSOne en EN1 (después de suscripción): Sucursales → POS → Cajas → Generar código → Instalar tablet.

**Qué no mezclar:** catálogo operativo de ventas/servicios de una org (`/admin/services`, SKUs Contador, menú POS) **no** es el catálogo comercial de productos de plataforma.

---

## Escenario de negocio

Analiza el siguiente caso:

1. Un cliente nunca ha usado EN1.
2. Se registra por primera vez.
3. Compra **EPOSOne Business**.
4. Meses después compra **ePayroll**.
5. Un año después decide utilizar **EN1 Platform** (CRM, Agenda, Facturación, etc.).
6. Más adelante agrega **otro producto que aún no existe hoy**.

Restricciones de negocio del escenario:

- La organización debe seguir siendo **la misma**.
- Los usuarios deben seguir siendo **los mismos**.
- No deben duplicarse organizaciones.
- No deben duplicarse procesos de registro.
- No debe haber migraciones entre productos.

---

## Pregunta arquitectónica central

Antes de proponer flujos, responde explícitamente:

> ¿Cómo soporta el modelo actual (y el modelo recomendado) que un cliente se registre **una sola vez** en EN1, compre hoy EPOSOne, dentro de seis meses compre ePayroll y un año después active EN1 Platform, utilizando **la misma organización**, los **mismos usuarios** y el **mismo portal de productos**, sin duplicar organizaciones ni procesos de compra?

Esa respuesta debe revelar si la arquitectura está pensada como plataforma multiproducto o si todavía está centrada en EPOSOne.

---

## Lo que necesitamos analizar

No queremos propuestas basadas únicamente en el estado actual de EPOSOne.  
Queremos una **propuesta de arquitectura para toda la plataforma**.

Analiza y documenta:

### 1. Punto de entrada

- ¿El cliente debe comenzar siempre desde EN1?
- ¿O cada producto mantiene su propio flujo de registro?

Justificar la recomendación.

### 2. Organización

Determinar cuál es el activo raíz.

- ¿La organización existe **antes** de comprar productos?
- ¿O nace al comprar un producto?

Justificar.

### 3. Productos

Analizar cómo debe administrarse el catálogo de productos. Ejemplos:

- EPOSOne
- ePayroll
- Marketplace
- EN1 Platform
- futuros productos

Todos deben seguir **el mismo modelo**.

Aclarar qué **no** es el catálogo comercial:

- No confundir con catálogo operativo de ventas/servicios de una org (`/admin/services`, SKUs Contador, menú POS, etc.).
- El catálogo comercial es el de **productos de plataforma** que se compran/contratan.

### 4. Suscripciones

Determinar:

- dónde viven,
- cómo se crean,
- cómo se relacionan con la organización.

### 5. Entitlements

Determinar cómo representar capacidades. Ejemplos:

| Producto | Capacidades (ejemplos) |
|----------|-------------------------|
| EPOSOne | cantidad de cajas, sucursales, usuarios |
| ePayroll | empleados, planillas |
| Marketplace | publicaciones, vendedores |

**No asumir** que todos los productos utilizan “cajas”.

### 6. Aprovisionamiento (solo EPOSOne, y solo análisis)

Responder:

- ¿Cuándo debe generarse el código de aprovisionamiento?
- ¿Debe existir antes o después del pago?
- ¿Debe ser de un solo uso?
- ¿Debe expirar?
- ¿Debe quedar asociado a una caja?
- ¿Cómo se reprovisiona un dispositivo?

Hipótesis de negocio a validar o refutar (no implementar):

- No debería existir antes de comprar.
- Se genera después de que existen: organización + suscripción + caja.
- Debe ser: un solo uso, asociado a una caja específica, con expiración, consumido en el primer registro exitoso.

### 7. Portal

Evaluar si el flujo correcto debería ser:

```text
Registro EN1
    ↓
Crear Organización
    ↓
Portal de Productos
    ↓
Comprar Producto
    ↓
Pago
    ↓
Suscripción Activa
    ↓
Producto aparece en "Mis Productos"
    ↓
Administrar Producto
    ↓
Generar Aprovisionamiento (cuando aplique)
    ↓
Instalar Cliente / Abrir App
```

Justificar ventajas y desventajas.

Principio: **el producto no vende ni licencia por sí mismo**; todo pasa por un portal central de cuentas, suscripciones y licencias.

### 8. Comparativa

Investigar y comparar cómo resuelven este flujo plataformas SaaS multiproducto consolidadas. Referencias sugeridas:

- Microsoft 365
- Salesforce
- Atlassian
- Google Workspace
- Zoho
- Odoo SaaS

No copiar su diseño; identificar **patrones comunes**.

---

## Entregables

Presentar un documento de arquitectura que incluya:

1. Modelo conceptual de la plataforma.
2. Flujo comercial recomendado.
3. Flujo de activación de productos.
4. Flujo de aprovisionamiento (**solo donde aplique**).
5. Relación entre Organización, Productos, Suscripciones y Entitlements.
6. Riesgos del modelo actual.
7. Recomendación final.
8. Respuesta explícita a la **pregunta arquitectónica central** (arriba).

Formato sugerido del entregable:

- Nombre: `docs/EN1_MULTIPRODUCT_COMMERCIAL_ARCHITECTURE_REVIEW.md`
- Estado: **análisis / propuesta** — no contrato HTTP, no ADR de implementación todavía.

---

## Restricciones (obligatorias)

- **No** modificar código.
- **No** modificar endpoints.
- **No** modificar contratos HTTP.
- **No** asumir cambios en EPOSOne.
- **No** diseñar una solución específica solo para EPOSOne.
- **No** implementar UI, checkout, ni aprovisionamiento.
- **No** “arreglar” el flujo actual con parches de EPOSOne.

El objetivo es definir un modelo que sirva para **todos** los productos actuales y futuros de EN1.

---

## Criterio de hecho

La tarea está completa cuando el documento:

1. Responde la pregunta multiproducto (misma org / mismos usuarios / mismo portal a lo largo del tiempo).
2. Separa claramente: **cuenta → org → catálogo comercial → pago → suscripción → entitlements → app/producto → aprovisionamiento (si aplica)**.
3. No centra el diseño en “empezar desde EPOSOne”.
4. No propone implementación ni cambios de código.

---

## Fuera de alcance

- Implementación de checkout / pasarela de pago.
- Cambios en APK.
- Cambios en lifecycle de instalación de dispositivos.
- Registro de SKUs en catálogo operativo de ventas de una organización.
- Cualquier “GO” de código de producto.
