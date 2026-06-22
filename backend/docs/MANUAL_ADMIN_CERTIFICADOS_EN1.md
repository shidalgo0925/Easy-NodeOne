# Manual del administrador — Certificados EN1

**Easy NodeOne · Módulo Certificados**  
**Audiencia:** administrador de la organización (usuario final, sin conocimientos técnicos)  
**Versión:** 1.0 — junio 2026  
**Entorno de referencia:** `https://appdev.easynodeone.com` (Dev EN1)

---

## 1. Qué cubre este manual

Este documento explica **cómo configurar, diseñar y emitir certificados** desde el panel de administración de Easy NodeOne.

Incluye:

- Certificados de **eventos** (seminarios, congresos, talleres, etc.).
- Certificados de **membresía y registro** (tipos MEM y REG).
- El **editor visual** de la carátula (diseño del PDF).
- Carga de participantes, emisión, descarga, revocación y verificación pública.

**No aplica** a certificados del módulo **Educación / LMS** (cursos académicos Moodle), que tienen su propio flujo.

---

## 2. Antes de empezar

### 2.1 Permisos

Necesitás ingresar con un usuario que tenga rol de **administrador** de la organización (o administrador de plataforma).

### 2.2 Módulos activos

Tu organización debe tener habilitados, según lo que vayas a usar:

| Módulo SaaS | Para qué |
|-------------|----------|
| **Certificados** | Menú Certificados, formatos MEM/REG, plantillas |
| **Eventos** | Crear eventos, participantes y certificados de evento |

Si no ves el menú **Certificados** o **Eventos**, pedí a soporte o al administrador de plataforma que active esos módulos para tu empresa.

### 2.3 Dos tipos de certificado (importante)

EN1 maneja **dos familias distintas**. No las mezcles al configurar:

| Tipo | Uso típico | Dónde se diseña | Quién lo obtiene |
|------|------------|-----------------|------------------|
| **Certificado de evento** | Participó en un seminario/congreso | Editor visual (**Editar carátula**) | El admin lo **genera**; el participante lo **descarga** si su email coincide con su cuenta |
| **Certificado MEM / REG** | Membresía activa o solo estar registrado en la plataforma | Modal **Formatos de certificado** | El usuario lo **solicita** en Mis Certificados |

La pantalla **Formatos de certificado** muestra ambas familias en una sola tabla, pero las acciones son diferentes (ver sección 4 y 5).

---

## 3. Dónde está cada cosa en el menú

### 3.1 Administración — Certificados

| Menú | Ruta | Función |
|------|------|---------|
| **Operaciones → Certificados → Eventos** | `/admin/certificate-events` | Lista unificada de formatos; acceso a **Editar carátula** (eventos) y modal MEM/REG |
| **Operaciones → Certificados → Plantillas** | `/admin/certificate-templates` | Listado de plantillas visuales; crear plantilla nueva o duplicar |

### 3.2 Administración — Eventos

| Menú | Ruta | Función |
|------|------|---------|
| **Comercial → Eventos** | `/admin/events` | Crear y editar eventos |
| **Evento → Participantes** | `/admin/events/<id>/participants` | Alta, importación Excel, check-in, generar certificado por persona |
| **Evento → Certificados** | `/admin/events/<id>/certificates` | Emisión masiva, listado emitidos, revocar, regenerar PDF |

### 3.3 Portal (para probar como usuario)

| Menú | Ruta | Función |
|------|------|---------|
| **Operaciones → Mis Certificados** | `/certificates` | Vista del participante: descargar PDF de eventos y solicitar MEM/REG |

### 3.4 Verificación pública (sin login)

Cualquier persona con el código o el QR puede verificar en:

`https://<tu-dominio>/certificates/verify/<código>`

Ejemplo de código de evento: `EN1-2026-A1B2C3` (participación) o `REV-2026-…` (revisor).

---

## 4. Certificados de evento — flujo completo

Este es el flujo más habitual para congresos, diplomados cortos y seminarios.

### Paso 1 — Crear o abrir el evento

1. Ir a **Comercial → Eventos**.
2. Crear evento nuevo o abrir uno existente.
3. En la sección **Certificación** (acordeón del formulario):
   - Activar el interruptor **«Este evento incluye certificado»**.
   - Opcional: escribir **instrucciones** para el participante (cómo obtiene el certificado).
   - El campo **«Plantilla o referencia»** es de uso interno del sistema; **no hace falta completarlo manualmente**.
4. Guardar el evento.

Al guardar con certificado activado, el sistema crea (o repara) automáticamente una **plantilla visual** vinculada a ese evento.

### Paso 2 — Diseñar la carátula del PDF

La carátula es el diseño visual del certificado: fondo, logos, textos, nombre del participante, código y QR.

**Formas de abrir el editor:**

- **Certificados → Eventos** → fila del evento → botón **Editar carátula**.
- **Certificados → Plantillas** → **Editar** en la plantilla marcada como evento.
- **Eventos → Certificados** del evento → enlace **Editar plantilla** (icono paleta).

Se abre el **Editor de plantilla** (`/admin/certificate-templates/editor/<id>`).

#### 2.1 Elementos del editor

| Herramienta (panel izquierdo) | Qué hace |
|-------------------------------|----------|
| **Texto** | Texto fijo que no cambia entre certificados (ej. «Otorga el presente certificado a») |
| **Imagen** | Logo, sello decorativo, firma escaneada |
| **Variable…** + **Añadir variable** | Campo dinámico que se rellena al emitir (nombre, fechas, código, etc.) |
| **QR verificación** | Código QR que apunta a la página pública de verificación |
| **Imagen de fondo** | Fondo completo del certificado (detrás de todo) |
| **Quitar fondo** | Elimina la imagen de fondo del lienzo |
| **Eliminar seleccionado** | Borra el objeto marcado en el lienzo |
| **Subir / Bajar capa**, **Al frente / Al fondo** | Orden de superposición (lo de arriba tapa lo de abajo) |

#### 2.2 Variables más usadas

**Datos de la carátula / institución**

- `institution` — Nombre de la institución  
- `partner_organization` — Organización asociada (pie o convenio)  
- `rector_name`, `academic_director_name` — Firmantes  
- `duration_hours` — Horas académicas  
- `start_date`, `end_date`, `event_dates` — Fechas del evento  

**Imágenes de formato** (si las configuraste en el formato o en el evento)

- `background_url`, `logo_left_url`, `logo_right_url`, `seal_url`

**Datos del titular y emisión** (se rellenan al generar cada certificado)

- `participant_name` — Nombre completo del participante  
- `document_id` — Cédula o documento  
- `program_name` — Título del evento  
- `body_text` — Párrafo de participación  
- `hours_line` / `hours` — Línea o número de horas  
- `issue_date`, `issue_date_legal` — Fecha de emisión  
- `certificate_code` — Código único del certificado  
- `verification_url` — URL de verificación (también va en el QR)

#### 2.3 Panel de propiedades (derecha)

Al hacer clic en un objeto del lienzo:

- Elegir **fuente**, **tamaño**, **negrita / cursiva / subrayado**, **color**.
- **Alineación** del texto.
- **Bloquear posición** — evita mover el objeto por error al seguir editando.
- En imágenes: ancho y alto en píxeles.
- En QR: tamaño del código.

#### 2.4 Guardar

1. Escribir un **nombre** de plantilla en la barra superior (ej. «Certificado Seminario 2026»).
2. Clic en **Guardar**.

Los certificados **nuevos** y los **regenerados** usarán esta versión de la plantilla.

#### 2.5 Vista previa

Desde **Formatos de certificado** (solo filas MEM/REG) existe **Vista previa** en el modal. Para eventos, la prueba real es **generar un certificado de prueba** con un participante de prueba y descargar el PDF.

### Paso 3 — Cargar participantes

Ir a **Eventos → [tu evento] → Participantes**.

**Opciones de carga:**

| Método | Cómo |
|--------|------|
| **Alta manual** | Botón agregar participante; completar nombre, apellidos, documento, email, teléfono |
| **Importar Excel** | Subir archivo `.xlsx` o `.xls` (plantilla «LISTA PARA CERTIFICADOS») |
| **Desde inscripciones** | Agregar desde registros confirmados del evento (si hay inscripciones con pago confirmado) |

#### Columnas del Excel (A–J)

| Columna | Campo | Obligatorio |
|---------|-------|-------------|
| A | Primer nombre | Sí |
| B | Segundo nombre | No |
| C | Primer apellido | Sí |
| D | Segundo apellido | No |
| E | Documento (cédula/pasaporte) | Recomendado |
| F | Email | Recomendado (necesario para que el usuario descargue solo en Mis Certificados) |
| G | Teléfono | No |
| H | Tipo participante | No (`external`, `reviewer`, `member`, `invited`, `speaker`, `staff`) |
| I | Estado de pago | No (`pending`, `paid`, `complimentary`, `waived`, `not_required`) |
| J | Notas | No |

**Lista de revisores:** si importás un archivo de revisores, dejá marcada la casilla correspondiente en la pantalla de importación. Si la columna H viene vacía, se asigna tipo **revisor** automáticamente.

La primera fila puede ser encabezado; el sistema la detecta y la omite.

### Paso 4 — Marcar asistencia (elegibilidad)

Un participante **solo puede recibir certificado** si cumple **una** de estas condiciones:

- Tiene **check-in** o asistencia marcada como **asistió** (`attended`), **o**
- Es de tipo **revisor** (`reviewer`).

**Cómo marcar check-in:**

En la lista de **Participantes**, usar las acciones de asistencia en cada fila (check-in, ausente, pendiente).

Los **revisores** importados con la plantilla de revisores suelen ser elegibles **sin** check-in.

### Paso 5 — Generar certificados

**Opción A — Pantalla Certificados del evento**

1. **Eventos → [evento] → Certificados**.
2. Revisar el resumen: emitidos, pendientes elegibles, revocados, total participantes.
3. Elegir una acción:
   - **Generar todos los elegibles** — procesa a todos los que cumplen condiciones y aún no tienen certificado activo.
   - **Marcar casillas** en la tabla de pendientes → **Generar seleccionados**.
   - **IDs manuales** — escribir IDs separados por coma (ej. `12, 15, 20`) → **Generar por ID**.

**Opción B — Desde la fila del participante**

En **Participantes**, botón de certificado en la fila (cuando es elegible y aún no tiene certificado activo).

**Qué ocurre al generar:**

- Se asigna un **código único** (ej. `EN1-2026-XXXXXX` o `REV-2026-…` para revisores).
- Se crea el **PDF** con la plantilla visual vigente.
- Se incrusta un **QR** con enlace de verificación pública.
- El participante pasa a estado **certificado emitido**.

### Paso 6 — Entregar el certificado al participante

| Canal | Requisito |
|-------|-----------|
| **Admin descarga PDF** | En Certificados emitidos → icono PDF; enviar por email u otro medio |
| **Usuario en Mis Certificados** | El **email del participante** debe coincidir con la cuenta EN1 del usuario (o estar vinculado por `user_id`) |
| **Verificación** | Compartir código o QR; cualquiera puede validar en `/certificates/verify/<código>` |

### Paso 7 — Acciones sobre certificados ya emitidos

En **Eventos → Certificados → tabla Emitidos**:

| Icono | Acción |
|-------|--------|
| **Sincronizar (regenerar)** | Vuelve a crear el PDF con la **plantilla actual** (útil si corregiste el diseño) |
| **PDF** | Descargar archivo |
| **Escudo** | Abrir página de verificación pública |
| **Usuario** | Ir al detalle del participante |
| **Prohibido (revocar)** | Invalida el certificado; deja de ser válido en verificación y en Mis Certificados |

Tras **revocar**, podés generar un certificado nuevo para el mismo participante si hace falta corregir datos.

### Paso 8 — Exportar listado

Desde **Certificados del evento**, botón **Exportar Excel** para obtener un archivo con los certificados emitidos (códigos, participantes, fechas).

---

## 5. Certificados de membresía y registro (MEM / REG)

Sirven para certificar que una persona **está registrada** en la plataforma (REG) o tiene **membresía activa** (MEM).

### 5.1 Formatos precargados

Al activar el módulo, la organización suele tener ya:

| Nombre | Prefijo | Requisito para el usuario |
|--------|---------|---------------------------|
| Certificado por Registro | `REG` | Cualquier usuario con cuenta |
| Certificado de Membresía | `MEM` | Membresía activa en la organización |

Los ves en **Certificados → Eventos**, sección **Membresía y registro (MEM / REG)**.

### 5.2 Crear o editar un formato MEM/REG

1. **Certificados → Eventos**.
2. **Nuevo formato** (o botón engranaje **Editar** en una fila MEM/REG).

**Campos del modal:**

| Campo | Descripción |
|-------|-------------|
| **Nombre del certificado** | Título que verá el usuario (obligatorio) |
| **Prefijo código** | Inicio del código (ej. `REG`, `MEM`, `REL`) |
| **Institución** | Nombre que aparece en el certificado |
| **Organización partner** | Texto de convenio o entidad asociada |
| **Nombre rector / Directora académica** | Firmantes |
| **Duración (horas)** | Horas académicas si aplica |
| **Fechas inicio / fin** | Vigencia o periodo del programa |
| **Fondo, logos, sello** | Elegir archivo → **Subir** (PNG, JPG, GIF, WebP, SVG) |
| **Plan requerido** | Opcional: exigir un plan de membresía concreto |
| **Activo** | Si está desactivado, el usuario no lo ve |
| **Verificación habilitada** | Permite validar el código en la web pública |
| **Plantilla visual** | Elegir una plantilla creada en **Plantillas** (recomendado) |
| **HTML plantilla** | Solo si no usás plantilla visual; para usuarios avanzados |

3. **Vista previa** — ver cómo quedará con datos de ejemplo.
4. **Guardar**.

### 5.3 Cómo lo usa el participante

1. Ingresa a **Mis Certificados** (`/certificates`).
2. En la sección de membresía/registro, ve los tipos disponibles.
3. Si cumple requisitos, pulsa **Solicitar**.
4. Cuando el sistema genera el PDF, aparece **Descargar**.

El administrador **no** genera estos certificados uno por uno; el usuario los solicita (salvo pruebas con tu propia cuenta).

---

## 6. Pantalla Plantillas — gestión general

**Certificados → Plantillas** (`/admin/certificate-templates`)

| Acción | Descripción |
|--------|-------------|
| **Nueva plantilla** | Crea un diseño reutilizable sin vincular aún a un evento |
| **Editar** | Abre el editor visual |
| **Duplicar** | Copia la plantilla para variantes (ej. otro evento similar) |
| **Vincular evento** | Pide el ID del evento y asocia la plantilla (alternativa al flujo automático) |
| **Eliminar** | Solo plantillas **generales**; las ligadas a un evento activo no conviene borrarlas sin revisar |

En el listado verás:

- **General** — plantilla libre.
- **Evento** — vinculada a un evento concreto (badge «Activa evento #N»).

---

## 7. Editor visual — buenas prácticas

1. **Nombre del participante** — Usá la variable `participant_name` con fuente grande y centrada; es el elemento principal.
2. **QR** — Colocalo en una esquina inferior; tamaño recomendado 100–150 px.
3. **Código** — Variable `certificate_code` cerca del QR o en el pie.
4. **Fondo** — Imagen en alta resolución (aprox. 1056×816 px o proporción carta horizontal); evita textos incrustados en el fondo que choquen con variables.
5. **Capas** — Logos y sellos encima del fondo; textos encima de logos si hace falta.
6. **Bloquear posición** — En elementos ya alineados (firmas, QR), activá **Bloquear posición** antes de guardar.
7. **Probar** — Generá un certificado de prueba, descargá el PDF y escaneá el QR antes de una emisión masiva.
8. **Regenerar** — Si cambiás el diseño después de emitir, usá **Regenerar** en cada fila o volvé a emitir tras revocar (según política de tu organización).

---

## 8. Pantalla Participantes — referencia rápida

| Columna | Contenido |
|---------|-----------|
| Participante | Nombre, documento, tipo (Miembro / Revisor / Externo), badge si está vinculado a cuenta EN1 |
| Contacto | Email y teléfono |
| Asistencia | Pendiente / Check-in / Ausente |
| Certificado | Emitido con código, o Pendiente |
| Acciones | Check-in, editar, ver certificados, generar, descargar PDF, verificar, eliminar |

---

## 9. Verificación pública

Cada certificado emitido tiene una URL del tipo:

```
https://<tu-sitio>/certificates/verify/<código>
```

La página indica si el certificado es **válido** o **revocado**, y muestra datos básicos (participante, evento).

El **QR del PDF** apunta a esa misma URL.

Si tenés el módulo **Generador QR** activo, también podés crear QRs independientes desde **Herramientas → Generador QR** con esa URL.

---

## 10. Problemas frecuentes y soluciones

| Problema | Causa probable | Qué hacer |
|----------|----------------|-----------|
| No aparece **Certificados** en el menú | Módulo SaaS desactivado | Pedir activación de `certificates` (y `events` si aplica) |
| No puedo generar certificado | Participante sin check-in y no es revisor | Marcar check-in o verificar tipo `reviewer` |
| «Ya existe un certificado activo» | Ya se emitió uno para esa persona y evento | Revocar el anterior o usar regenerar |
| El usuario no ve el PDF en Mis Certificados | Email del participante ≠ email de la cuenta | Corregir email en participante o que use la cuenta correcta |
| El PDF sale con diseño viejo | Plantilla cambiada después de emitir | **Regenerar** desde Certificados del evento |
| No hay fila del evento en Formatos de certificado | Evento sin certificado activado o sin plantilla vinculada | Activar «incluye certificado» en el evento y guardar; abrir **Editar carátula** al menos una vez |
| Vista previa MEM/REG en blanco | Falta plantilla o assets | Asignar plantilla visual o subir fondo/logos |
| Código REV en lugar de EN1 | Participante tipo revisor | Comportamiento esperado; revisores usan prefijo `REV` |
| Certificado revocado sigue apareciendo al usuario | Caché del navegador o PDF descargado antes | Usuario debe verificar en web; revocados no son válidos |

---

## 11. Checklist operativo (evento con certificado)

Usá esta lista antes de una emisión masiva:

- [ ] Evento creado y publicado.
- [ ] **«Este evento incluye certificado»** activado.
- [ ] Carátula diseñada y **guardada** en el editor visual.
- [ ] Participantes cargados (Excel o manual).
- [ ] Emails correctos para quienes deben descargar solos.
- [ ] Check-in marcado (excepto revisores).
- [ ] Certificado de prueba generado y PDF revisado (nombre, fechas, QR).
- [ ] Emisión masiva o por lotes.
- [ ] Comunicación a participantes (enlace a Mis Certificados o envío de PDF).
- [ ] Export Excel de respaldo si tu organización lo requiere.

---

## 12. Resumen de responsabilidades

| Tarea | Administrador | Participante |
|-------|:-------------:|:------------:|
| Diseñar carátula / formato | Sí | No |
| Cargar participantes | Sí | No |
| Marcar asistencia | Sí | No |
| Generar certificado de evento | Sí | No |
| Solicitar certificado MEM/REG | No (prueba con su cuenta) | Sí |
| Descargar PDF de evento | Sí | Sí (Mis Certificados) |
| Revocar certificado | Sí | No |
| Verificar autenticidad (web/QR) | Sí | Sí |

---

## 13. Documentos relacionados

| Documento | Contenido |
|-----------|-----------|
| `docs/EN1_ARCHITECTURE.md` | Arquitectura técnica (para desarrolladores) |
| `docs/RELATIC_CERTIFICADOS_PORTAL_USUARIO_2B.md` | Detalle del portal Mis Certificados |
| `tools/build_manual_certificados_docx.py` | Genera `MANUAL_USUARIO_RELATIC_CERTIFICADOS.docx` (versión Relatic en Word) |

---

*Manual redactado para administradores de organización en Easy NodeOne (EN1). Para cambios de módulos SaaS, permisos o incidencias de plataforma, contactá al equipo de soporte o al administrador de plataforma.*
