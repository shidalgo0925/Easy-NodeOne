# Manual operativo Relatic — Certificados de eventos

**Plataforma:** [apps.relatic.org](https://apps.relatic.org)  
**Audiencia:** administradores / equipo operativo Relatic  
**Versión:** 1.0 (Nivel 1 — uso con envío manual)  
**Validación técnica:** smoke GO 2026-06-08 en producción Relatic

---

## Antes de empezar

### Requisitos

- Usuario con permisos de **administrador** en Relatic.
- Módulo **Eventos** habilitado para la organización.
- Participantes cargados como **Participantes del evento** (`EventParticipant`), no solo como inscripciones de pago.

### Aclaraciones importantes

1. **Solo pueden recibir certificado** los participantes que cumplan **asistencia confirmada**:
   - estado **Check-in** / **Attended**, **o**
   - tipo **reviewer** (revisor), según el evento.

2. **Descarga directa del participante y envío automático por correo no están habilitados** en esta versión.
   - El **administrador** genera el certificado, **descarga el PDF** y lo **comparte manualmente** (correo, WhatsApp, etc.).

3. Los **cursos académicos** (`/inscripcion/…`) **no** usan este flujo. Este manual es solo para **eventos**.

---

## Flujo operativo (8 pasos)

### 1. Crear o abrir evento

1. Entrar a **apps.relatic.org** con cuenta admin.
2. Menú **Eventos** → listado de eventos.
3. **Crear** un evento nuevo o **abrir** uno existente (**Editar evento**).
4. En el evento, activar la opción de **certificado** si aplica (pestaña / sección de certificado en la ficha del evento).
5. Guardar cambios.

**Ruta directa:** `/admin/events`

---

### 2. Registrar participantes

Los certificados se emiten sobre **Participantes del evento**, no sobre el listado de inscripciones de pago.

1. Desde el evento, ir a **Participantes**.
2. Elegir una vía:
   - **Nuevo** — alta manual (nombre, documento, email, teléfono, tipo).
   - **Importar Excel** — plantilla tipo «LISTA PARA CERTIFICADOS» (columnas A–G; opcional H–J).

**Ruta:** `/admin/events/<id>/participants`

> Un participante **no necesita** tener usuario EN1 para recibir certificado.

---

### 3. Marcar asistencia

1. En el listado de participantes, localizar a la persona.
2. Usar los botones de asistencia:
   - **Check-in** — asistencia confirmada (habilita certificado).
   - **Ausente** — no asistió.
   - **Pendiente** — aún sin definir.

**Filtro útil:** desplegable **Asistencia** (Todos / Pendiente / Check-in / Ausente).

Solo con **Check-in** (o tipo **reviewer**) aparecerá el botón para generar certificado.

---

### 4. Generar certificado

**Por participante (recomendado)**

1. En la fila del participante elegible, pulsar **Certif.**
2. Confirmar mensaje de éxito.

**Masivo**

1. Ir a **Certificados** (botón amarillo desde Participantes).
2. **Generar todos los elegibles** — solo quienes tienen check-in o son reviewer y aún no tienen certificado activo.
3. O **Generar seleccionados** — indicar IDs de participantes separados por coma.

**Ruta:** `/admin/events/<id>/certificates`

Si no se genera, revisar: sin check-in, certificado ya emitido, o participante ausente.

---

### 5. Descargar PDF

1. Desde **Participantes** → botón **PDF** en la fila (si ya hay certificado).
2. O desde **Certificados del evento** → **PDF** en la tabla de emitidos.
3. O desde **Certs.** (vista de certificados de un participante).

El archivo se descarga con nombre tipo `EN1-2026-XXXXXX.pdf` o `REV-2026-XXXXXX.pdf` (revisores).

---

### 6. Enviar manualmente

1. Adjuntar el PDF al correo o enviarlo por **WhatsApp** / canal acordado con el participante.
2. Opcional: incluir el **código** del certificado y la **URL de verificación** (ver paso 7).

No hay botón «Enviar certificado por email» en la plataforma en esta versión.

---

### 7. Validar QR / código

Cada certificado incluye:

- **Código** único (ej. `EN1-2026-736191`).
- **QR** en el PDF que apunta a la verificación pública.
- **URL pública:**  
  `https://apps.relatic.org/certificates/verify/<código>`

**Comprobar validez**

1. Abrir la URL en el navegador (o escanear el QR).
2. Debe mostrar estado **Válido**, nombre del participante y nombre del evento.
3. Si el certificado fue **revocado**, mostrará estado revocado/anulado.

---

### 8. Revocar (si aplica)

Usar cuando hubo error de datos, fraude o reemisión necesaria.

1. Ir a **Certificados del evento**.
2. En el certificado activo, **Revocar** (opcional: motivo).
3. El estado pasa a **revocado**; la verificación pública lo refleja.
4. Para emitir uno nuevo: corregir datos del participante (paso 2 / Editar), revocar el anterior y **generar de nuevo** (paso 4).

No existe botón «Regenerar» en un solo clic; el flujo es **revocar + generar**.

---

## Resumen rápido

| Paso | Acción | ¿Quién? |
|------|--------|---------|
| 1 | Evento creado/abierto | Admin |
| 2 | Participantes cargados | Admin |
| 3 | Check-in confirmado | Admin |
| 4 | Certificado generado | Admin |
| 5 | PDF descargado | Admin |
| 6 | PDF enviado al participante | Admin (manual) |
| 7 | QR/código verificado | Admin o tercero |
| 8 | Revocación si hay error | Admin |

---

## Limitaciones actuales (Nivel 1)

| Función | Estado |
|---------|--------|
| Generar PDF con código y QR | Disponible |
| Verificación pública por URL/QR | Disponible |
| Descarga admin | Disponible |
| Descarga directa del participante | No disponible |
| Envío automático por email | No disponible |
| Plantilla con logo y firma institucional | PDF básico (sin diseño a medida) |
| Certificados de cursos académicos | No disponible (otro módulo) |

---

## Backlog Nivel 2 (solo si el cliente lo exige)

Desarrollo futuro, no incluido en el cierre operativo actual:

- Plantilla visual institucional (logo, firma, fondo).
- Email automático al emitir certificado.
- Portal de descarga para el participante.
- Botón «Regenerar certificado» (revocar + nuevo en un paso).
- Certificados para **cursos / programas académicos**.

---

## Cierre funcional Relatic

Con este manual, Relatic queda **operativo para certificados de eventos** en modo administrador: generar, descargar, compartir y validar.

No se requiere desarrollo adicional salvo que el cliente solicite explícitamente algún ítem del **Nivel 2**.

---

*Documento operativo — Easy NodeOne / Relatic Panamá. Actualizar si cambia la UI o se implementa Nivel 2.*
