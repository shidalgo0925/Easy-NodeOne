# ADR-033 — Standalone Onboarding Assistant

| Campo | Valor |
|-------|--------|
| ID | **ADR-033** |
| Título | Asistente de onboarding local — EPosOne Standalone (Autogestionado) |
| Estado | **PROPOSED** — pendiente revisión / aprobación Arquitectura · handoff LOCAL |
| Versión | 1.0 |
| Fecha | Agosto 2026 |
| Autor | Arquitectura EN1 / EPosOne |
| Impacto | EPosOne APK (LOCAL) · consumo de token de activación (EN1) |
| Implementación de código | **NO autorizada** — documento de arquitectura / especificación de producto |
| Responsable de análisis APK | **LOCAL** |
| Complementa | [ADR-032](ADR-032-PRODUCT-IMPLEMENTATION-MODEL.md) (§ Autogestionada) · [ADR-031](ADR-031-EN1-COMMERCIAL-DOMAIN-ARCHITECTURE.md) |
| Relacionados | [ADR-001](ADR-001-EPOSONE-STANDALONE.md) · [ADR-027](ADR-027-EPOSONE-ONBOARDING-UNIFICADO-V1.md) · [ADR-021](ADR-021-EPOSONE-INSTALLATION-LIFECYCLE.md) · [ADR-024](ADR-024-EPOSONE-START-ASSISTANT.md) (registro comercial web, no este asistente) |

---

## 1. Objetivo

Definir el **asistente de configuración local** que la APK ejecuta en modalidad **Standalone** (implementación **Autogestionada**, ADR-032).

**Única responsabilidad de este ADR:** pantallas y pasos del onboarding operativo en el dispositivo **después** de la activación.

No define quién implementa (eso es ADR-032) ni el dominio comercial (ADR-031) ni el provisioning Connected (ADR-034).

---

## 2. Precondiciones

1. Registro comercial completado en EN1 (Cliente → Org → Contrato → Suscripción → Licencia).  
2. El cliente posee un **Token de activación** (entregado por QR, correo, enlace o copia manual — ADR-032 §7).  
3. APK instalada.  
4. La activación con el token determina modalidad **Standalone** / estrategia **Autogestionada**. La APK **no** pregunta la modalidad.

EN1 **no** ha creado sucursal / POS / caja / cajero / bootstrap cloud (ADR-032).

---

## 3. Flujo del asistente

```text
Bienvenida
  → Activación (ingreso / escaneo de token)
  → Empresa
  → Impuestos (y moneda / fiscal básico)
  → Categorías
  → Productos
  → Caja inicial
  → Cajero administrador
  → Impresora
  → Finalizar
  → Operación (vender)
```

Pasos opcionales o diferibles (según UX LOCAL, sin romper el mínimo operable):

- Clientes (maestro)  
- Configuración general avanzada  

---

## 4. Pantallas (contrato funcional)

| # | Pantalla | Propósito | Mínimo |
|---|----------|-----------|--------|
| 1 | **Bienvenida** | Contexto Standalone; qué va a configurar; acceso a ayuda | Obligatoria |
| 2 | **Activación** | Ingresar token (pegar / escanear QR / deep link). Validar firma/vigencia. Persistir licencia local | Obligatoria |
| 3 | **Empresa** | Nombre comercial, datos básicos del negocio | Obligatoria |
| 4 | **Impuestos** | Régimen / tasas; moneda de operación | Obligatoria |
| 5 | **Categorías** | Al menos una categoría de catálogo | Obligatoria |
| 6 | **Productos** | Al menos un producto vendible | Obligatoria |
| 7 | **Caja** | Caja inicial local (no cloud EN1) | Obligatoria |
| 8 | **Cajero** | Cajero administrador + PIN/credencial local | Obligatoria |
| 9 | **Impresora** | Selección / prueba / omitir con aviso | Recomendada (omitible) |
| 10 | **Finalizar** | Resumen; checklist; CTA “Empezar a vender” | Obligatoria |

Al completar **Finalizar**, el negocio queda operable en el dispositivo.

---

## 5. Activación (pantalla 2)

- Entrada: **token** (no “el QR como orden”). El QR es solo un medio (ADR-032).  
- Salida: licencia/entitlement local usable; modalidad fijada a Standalone.  
- Errores: token inválido, expirado, ya usado (si aplica política de un solo uso), producto incorrecto.  
- Tras éxito: no volver a pedir modalidad; avanzar al asistente de negocio.

Detalle criptográfico / HTTP del token: **ADR de Activación** (planificado). Hasta entonces, LOCAL asume contrato provisional acordado con CODITO.

---

## 6. Ayuda y soporte (en el asistente)

### Recursos gratuitos

- Manual PDF  
- Videos  
- Base de conocimiento  
- Preguntas frecuentes  

### Servicios profesionales (CTA / deep links)

- Instalación remota  
- Instalación presencial  
- Migración de datos  
- Capacitación  

Pueden estar incluidos en el plan o contratarse después (ADR-032 §10). No bloquean el asistente.

---

## 7. Qué NO hace este asistente

- Crear infraestructura operacional en EN1 (sucursal/POS/caja cloud).  
- Pedir al usuario “¿Standalone o Connected?”.  
- Sustituir el registro comercial web (`/start` / Portal — ADR-024 / 031).  
- Ejecutar bootstrap Connected ni sync cloud operativa.

---

## 8. Relación con otros ADR

| ADR | Relación |
|-----|----------|
| **031** | Prerrequisito comercial |
| **032** | Estrategia Autogestionada; este ADR es el detalle LOCAL |
| **024** | Alta comercial web; distinto del asistente APK |
| **027** | Standalone = registrado en EN1 sin sync; este ADR materializa el setup local |
| **001** | Producto Standalone; onboarding de usuario aquí |
| **021** | Estados de instalación APK; alinear tras aprobación |

---

## 9. Impacto

### LOCAL

**Analizar / diseñar** (sin implementar hasta GO):

- Wireframes de las 10 pantallas  
- Persistencia local post-activación  
- UX de token (pegar / QR / enlace)  
- Omitir impresora sin romper “Finalizar”  

### CODITO

- Emitir y validar token compatible con esta activación (ADR Activación / 031)  
- No crear árbol ops en el alta Standalone  

---

## 10. Fuera de alcance

Código APK o EN1; Connected provisioning (ADR-034); modelo formal de firma del token; cambios a `/start`.

---

## 11. Estado

**PROPOSED**

Documento de referencia para LOCAL. Requiere aprobación Arquitectura + **GO de implementación** por fases antes de código.
