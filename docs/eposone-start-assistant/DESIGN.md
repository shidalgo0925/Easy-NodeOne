# Asistente de Inicio EPosOne — Paquete de Diseño (Fase B)

| Campo | Valor |
|-------|--------|
| GO | **GO diseño** |
| ADR | [`ADR-024-EPOSONE-START-ASSISTANT.md`](../ADR-024-EPOSONE-START-ASSISTANT.md) |
| Estado | Entregado para revisión — **no es implementación** |
| Preview | Abrir [`wireframes/index.html`](wireframes/index.html) en el navegador |
| Branding | EPosOne — primario `#FF6600` · oscuro `#001A4B` · fondo `#F7F8FC` |

---

## 1. Objetivo del diseño

Experiencia **Asistente de Inicio EPosOne** (no registro, no onboarding POS, no EN1 visible): recomendar modalidad+plan, crear acceso y negocio, legal, código, guía Play. Config operativa del POS **fuera**.

---

## 2. Etapas de progreso (UI)

No “Paso 1 de 9” rígido. Cuatro etapas:

1. **Tu negocio** — bienvenida + tipo  
2. **Tu recomendación** — recomendación (+ otras opciones)  
3. **Tu acceso** — cuenta + datos negocio + resumen legal  
4. **Todo listo** — WOW + guía Play  

---

## 3. Flujo de navegación

```text
[1 Bienvenida]
    → Comenzar
[2 Tipo de negocio]
    → Continuar (requiere selección)
[3 Recomendación]
    → Usar esta recomendación → [5]
    → Ver otras opciones → [4]
[4 Otras opciones] (opcional)
    → Continuar con esta opción → [5]
    → Atrás → [3]
[5 Crear tu acceso]
    → Continuar → [6]
[6 Datos del negocio]
    → Continuar → [7]
[7 Resumen y aceptación]
    → Preparar mi EPosOne (legal checked) → [8]
[8 Confirmación WOW]
    → Descargar en Google Play → [9]
    → Ver mi código (modal/panel)
[9 Guía de instalación]
    → Abrir EPosOne (si deep link)
    → Fin del asistente web (handoff Local)
```

Atrás permitido en 2–7 si no hay inconsistencia. Tras crear negocio (post-7), atrás no debe duplicar creación (idempotencia).

---

## 4. Copy comercial por pantalla

### 1 — Bienvenida
- **Título:** Empieza con EPosOne  
- **Sub:** Prepara tu negocio y descarga tu punto de venta en pocos minutos.  
- **CTA:** Comenzar  

### 2 — Tipo de negocio
- **Título:** ¿Qué tipo de negocio tienes?  
- **Sub:** Así te recomendamos la mejor forma de empezar.  
- **Opciones:** Restaurante · Cafetería · Bar · Tienda · Mini súper · Farmacia · Servicios · Otro  
- **CTA:** Continuar  

### 3 — Recomendación
- **Eyebrow:** Recomendado para ti  
- **Título patrón:** Para una {tipo} como la tuya recomendamos **EPosOne {Plan}**.  
- **Sub patrón (conectado):** Administra tu negocio desde cualquier lugar · {precio}/mes · {trial copy}  
- **Sub patrón (local):** Opera localmente desde un solo punto de venta · USD 15.00/mes · Activación al contratar  
- **CTA primario:** Usar esta recomendación  
- **CTA secundario:** Ver otras opciones  

### 4 — Otras opciones
- **Título:** Elige cómo quieres empezar  
- Cards: Standalone 15.00 · Starter 29.95 · Business 39.95 · Enterprise 79.95  
- Beneficio en una línea cada una; badge “15 días gratis” o “Activación inmediata”  
- **CTA:** Continuar con esta opción  

### 5 — Crear tu acceso
- **Título:** Crea tu acceso  
- **Sub:** Solo lo necesario para entrar a EPosOne.  
- Campos: Nombre · Correo · Contraseña  
- **CTA:** Continuar  

### 6 — Datos del negocio
- **Título:** ¿Cómo se llama tu negocio?  
- Campos: Nombre del negocio · País (default Panamá) · (tipo ya elegido, solo lectura)  
- **CTA:** Continuar  

### 7 — Resumen y aceptación
- **Título:** Confirma y prepara EPosOne  
- Resumen: negocio, modalidad (beneficio), plan, precio, trial/activación  
- Checkboxes (no pre-checked): Términos · Privacidad · EULA · (Standalone/Trial si aplica)  
- **CTA:** Preparar mi EPosOne  

### 8 — WOW
- **Título:** ¡Bienvenido a EPosOne!  
- **Sub:** Tu negocio ya está preparado.  
- Checks: Acceso creado · Negocio preparado · Plan activado o Trial iniciado · Código listo  
- **CTA primario:** Descargar en Google Play  
- **CTA secundario:** Ver mi código de instalación  

### 9 — Guía Play
- **Título:** Instala EPosOne  
- Pasos numerados: Descarga · Instala · Inicia sesión · Escanea o ingresa tu código · Espera la configuración inicial  
- **CTA:** Abrir EPosOne (cuando exista) · Rever código  

---

## 5. Motor de recomendación (mapa de diseño)

| Tipo de negocio | Recomendación inicial (orientativa) | Modalidad |
|-----------------|-------------------------------------|-----------|
| Cafetería / Restaurante / Bar | Business USD 39.95 | Conectado |
| Tienda / Mini súper / Farmacia | Starter USD 29.95 | Conectado |
| Servicios / Otro | Starter USD 29.95 | Conectado |
| (Usuario elige en otras opciones) | Standalone / cualquier plan | Según elección |

Razones copy cortas en wireframe. Reglas **evolucionables** sin cambiar estructura UI (ADR-024 §13).

---

## 6. Estados de error (copy)

| Caso | Mensaje |
|------|---------|
| Correo ya registrado | Ya existe un acceso con este correo. Inicia sesión o recupera tu contraseña. |
| Validación campos | Revisa los campos marcados e intenta de nuevo. |
| Fallo al preparar | No pudimos completar este paso. Tu información está guardada. Intenta nuevamente. |
| Código no disponible | Tu código se está generando. Espera un momento o actualiza. |
| Sin conexión | Sin conexión. Revisa tu internet e intenta otra vez. |
| Servicio caído | EPosOne no está disponible temporalmente. Intenta en unos minutos. |

Nunca mostrar stack traces ni nombres de tablas.

---

## 7. Estados de abandono

| Punto | Comportamiento de diseño |
|-------|--------------------------|
| Antes de acceso | Guardar tipo + recomendación en storage local; retomar en Bienvenida→último paso |
| Tras acceso | Vincular progreso a cuenta; email de continuación (diseño; envío = GO implementación) |
| Post-negocio pre-Play | WOW recuperable; código recuperable en “Ver mi código” |
| Post-Play sin código | Guía + código visible; no recrear negocio |

---

## 8. Mapa de integración (servicios existentes — sin modelos nuevos)

| Paso UI | Servicio EN1 existente (conceptual) |
|---------|-------------------------------------|
| Crear acceso | Auth / registro de usuario existente |
| Crear negocio | Organización / tenant existente |
| Modalidad + plan | Product Registry + commercial_plans + Subscription Registry |
| Trial | create_trial / ADR-023 |
| Standalone activación | activate / pago (pago real = backlog comercial) |
| Entitlement | EntitlementService / plantillas de plan |
| Código | Provisioning / installation codes existentes |
| Legal | `/legal/*` + registro de consentimiento (versión documento) |
| Host | ProductContext EPosOne |

**Confirmación de diseño:** no se proponen tablas nuevas en este paquete. Si hace falta persistir progreso de asistente, se evaluará en `GO implementación` con el mínimo esquema o storage existente — **sin** motor de licencias paralelo.

---

## 9. Contrato Codito → Local (diseño)

Local recibe: usuario autenticable, negocio, modalidad, plan, trial/suscripción válida, entitlement, código de instalación, branding EPosOne.

Código: un solo uso o política del provisioning actual; expiración; regeneración desde Portal; no segundo sistema de códigos.

---

## 10. Checklist de exclusiones (QA de diseño)

El diseño **no** incluye pantallas de: productos, impresoras, cajeros, impuestos, mesas, KDS, inventario, promociones, hardware, Dashboard EN1, estados TRIAL/GRACE internos, jerga EN1.

---

## 11. Checklist legal (diseño)

Enlaces a `/legal/terms`, `privacy`, `eula`, `refunds`, `data-deletion`. Checkboxes no pre-checked. Evidencia de aceptación en implementación futura.

---

## 12. Checklist seguridad (diseño)

CSRF en forms POST futuros · rate limit registro · host EPosOne · no filtrar códigos en URLs públicas · no logs de contraseña · aislamiento org.

---

## 13. Eventos de analítica (diseño)

Ver ADR-024 §24. Wireframes asumen `data-event` hooks; implementación de tracking = GO implementación / no bloqueante V1.

---

## 14. Precios / Trial confirmados en diseño

Standalone 15.00 (sin trial auto) · Starter 29.95 · Business 39.95 · Enterprise 79.95 · Trial 15 días conectados · Grace 7 días (ADR-023).

---

## 15. Criterio “diseño listo para implementación”

Cumple ADR-024 §37 (criterios de aceptación de diseño).  
**Siguiente fase:** solo con **`GO implementación`** explícito (Dev EN1). Local y deploy requieren sus propios GO.

---

## 16. Archivos de este paquete

| Archivo | Contenido |
|---------|-----------|
| `DESIGN.md` | Este documento |
| `wireframes/index.html` | Preview navegable móvil-first (9 pantallas) |
| `wireframes/styles.css` | Estilos branding EPosOne del preview |

No son rutas de producción. Solo abrirse como archivos estáticos.
