# ADR-032 — Modelo de Implementación de Productos

| Campo | Valor |
|-------|--------|
| ID | **ADR-032** |
| Título | Implementación Autogestionada (Standalone) e Implementación Asistida (Connected) |
| Estado | **PROPOSED** — pendiente revisión / aprobación Arquitectura |
| Versión | 1.0 |
| Fecha | Agosto 2026 |
| Autor | Arquitectura EN1 / EPosOne |
| Impacto | EN1 · Portal ETS · EPosOne APK |
| Implementación de código | **NO autorizada** — documento de arquitectura únicamente |
| Complementa | [ADR-031](ADR-031-EN1-COMMERCIAL-DOMAIN-ARCHITECTURE.md) (dominio comercial) |
| Relacionados | [ADR-027](ADR-027-EPOSONE-ONBOARDING-UNIFICADO-V1.md) · [ADR-024](ADR-024-EPOSONE-START-ASSISTANT.md) · [ADR-021](ADR-021-EPOSONE-INSTALLATION-LIFECYCLE.md) · [ADR-001](ADR-001-EPOSONE-STANDALONE.md) · [EN1_MODELO_COMERCIAL_V1.md](EN1_MODELO_COMERCIAL_V1.md) |

---

## 1. Objetivo

Definir el **modelo oficial de implementación** de los productos comercializados por Easy Technology Services (ETS).

Este ADR complementa el [ADR-031](ADR-031-EN1-COMMERCIAL-DOMAIN-ARCHITECTURE.md) (Modelo Comercial) y establece **cómo un producto contratado se convierte en un producto operativo**.

---

## 2. Problema

Hasta ahora EN1 asumía que registrar un cliente implicaba iniciar inmediatamente la implementación técnica.

Ejemplo histórico:

```text
Registro → Organización → Provisioning → Bootstrap → Operación
```

Ese modelo obliga a todos los clientes a seguir el mismo flujo, independientemente de la modalidad contratada.

Esto genera complejidad innecesaria para clientes **Standalone**.

---

## 3. Principio arquitectónico

### Comercial ≠ Implementación

El **registro comercial** finaliza cuando el cliente obtiene:

```text
Cliente → Organización → Contrato → Suscripción → Licencia
```

La **implementación** comienza únicamente cuando el producto contratado debe ponerse en operación.

---

## 4. Estrategias de implementación

Todo producto deberá definir una **estrategia de implementación**.

Actualmente se definen dos:

| Estrategia | Modalidad típica (EPosOne) | Responsable principal |
|------------|----------------------------|------------------------|
| **Autogestionada** | Standalone | Cliente |
| **Asistida** | Connected | Easy Technology Services |

---

## 5. Implementación Autogestionada

### Aplica para

EPosOne **Standalone**.

### Responsable principal

El **cliente**.

Easy Technology Services únicamente proporciona:

- licencia  
- activación  
- documentación  
- soporte (opcional)  

### Flujo

```text
Landing EPosOne
  → Seleccionar Standalone
  → Registro
  → Verificación de correo
  → Contrato
  → Suscripción
  → Licencia
  → QR de activación
  → Descarga APK
  → Escanear QR
  → Activación
  → Asistente local
  → Operación
```

### El asistente local

La APK deberá permitir configurar completamente el negocio.

Como mínimo:

- Empresa  
- Moneda  
- Impuestos  
- Categorías  
- Productos  
- Clientes (opcional)  
- Caja inicial  
- Cajero administrador  
- Impresora  
- Configuración general  

Una vez completado el asistente, el cliente podrá comenzar a vender.

### EN1 NO crea (Standalone)

En modalidad Standalone **NO** deberán crearse automáticamente:

- sucursales  
- POS  
- cajas  
- cajeros  
- inventario cloud  
- bootstrap cloud  

La Organización existe únicamente como **entidad comercial** (ADR-031).

### Recursos de ayuda

El asistente ofrecerá:

**Recursos gratuitos**

- Manual PDF  
- Videos  
- Base de conocimiento  
- Preguntas frecuentes  

**Servicios profesionales**

- Instalación remota  
- Instalación presencial  
- Migración de datos  
- Capacitación  

Estos servicios podrán estar:

- incluidos en el plan  
- contratados posteriormente  

---

## 6. Implementación Asistida

### Aplica para

EPosOne **Connected**.

### Responsable principal

**Easy Technology Services**.

### Flujo

```text
Registro
  → Correo verificado
  → Contrato
  → Suscripción
  → Licencia
  → Asignación a implementación
  → Configuración EN1
  → Sucursal
  → POS
  → Caja
  → Cajeros
  → Código de activación
  → Descarga APK
  → Provisioning
  → Bootstrap
  → Operación
```

---

## 7. Código / QR de activación

El QR deja de representar únicamente un código.

Representa una **orden de activación**.

Debe indicar como mínimo:

| Campo | Rol |
|-------|-----|
| producto | qué producto se activa |
| modalidad | Standalone / Connected |
| estrategia de implementación | Autogestionada / Asistida |
| licencia | derecho de uso |
| código | token de activación |
| expiración | vigencia de la orden |
| firma | integridad / autenticidad |

### Ejemplo lógico

**Standalone**

```text
Producto: EPosOne
Modalidad: Standalone
Implementación: Autogestionada
```

**Connected**

```text
Producto: EPosOne
Modalidad: Connected
Implementación: Asistida
```

---

## 8. Comportamiento de la APK

La APK **NO** preguntará al usuario qué modalidad utilizar.

La modalidad será determinada por la **activación**.

Según esa información la APK ejecutará automáticamente el flujo correspondiente.

---

## 9. Responsabilidades

### Cliente

- Instalar APK  
- Completar asistente Standalone  
- Mantener su información  
- Solicitar soporte cuando lo requiera  

### Easy Technology Services

- Administrar clientes  
- Administrar contratos  
- Emitir licencias  
- Proveer documentación  
- Brindar soporte  
- Ejecutar implementaciones asistidas cuando correspondan  

---

## 10. Servicios profesionales

La implementación es un **servicio independiente** del producto.

Puede estar:

- incluida en determinados planes  
- contratada posteriormente  

Esto permite ofrecer distintos niveles de acompañamiento **sin modificar el producto**.

---

## 11. Beneficios

### Standalone (Autogestionada)

- instalación inmediata  
- menor costo  
- sin intervención de EasyTech  
- escalable  
- onboarding sencillo  

### Connected (Asistida)

- implementación profesional  
- integración completa con EN1  
- sincronización  
- multi-sucursal  
- administración centralizada  

---

## 12. Principios

1. Todo producto define su estrategia de implementación.  
2. La implementación puede ser **Autogestionada** o **Asistida**.  
3. El registro comercial finaliza **antes** de iniciar cualquier implementación.  
4. La APK determina automáticamente el flujo de implementación a partir de la activación.  
5. Standalone **no** requiere infraestructura operacional en EN1 para comenzar a operar.  
6. Connected requiere implementación previa antes del aprovisionamiento.  
7. Los servicios de implementación son independientes del licenciamiento del producto.  

---

## 13. Impacto esperado

### CODITO (EN1)

**Analizar** (no implementar):

- modelo de activación  
- emisión del QR  
- información contenida en la licencia  
- separación entre activación e implementación  
- integración con ADR-031  

### LOCAL (EPosOne)

**Analizar** (no implementar):

- asistente Standalone  
- activación mediante QR  
- flujo autogestionado  
- comportamiento según modalidad  
- integración futura con el nuevo contrato de activación  

---

## 14. Fuera de alcance

Este ADR **no autoriza**:

- cambios en `/start`  
- cambios en bootstrap  
- cambios en provisioning  
- eliminación de código  
- refactorizaciones  
- modificaciones de ADR anteriores  

Su único propósito es definir el **modelo arquitectónico de implementación** para que CODITO y LOCAL trabajen sobre una misma visión.

---

## 15. Estado

**PROPOSED**

Pendiente de revisión y aprobación por Arquitectura antes de cualquier implementación de código.

Tras la aprobación formal: enmiendas derivadas (si aplica) a ADR-024 / 027 / 021 y contrato de activación — **solo con GO explícito**.
