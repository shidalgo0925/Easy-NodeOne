# EN1 — Contexto técnico: certificados de eventos

**Para:** IA, programadores y operación en Dev EN1.  
**Última actualización:** 2026-06-24  
**Rama / commit de referencia:** `develop` · `1d878d4` (`fix(certificates): editor único de formato y retorno al evento`)

> Comentario: este archivo es la **fuente de verdad de contexto** para chats y tareas sobre certificados de **eventos** (seminarios). No sustituye `AGENTS.md` ni `REGLAS-DE-TRABAJO.md` para protocolo Git/entornos.

---

## 1. Entorno de trabajo (Dev EN1)

| Concepto | Valor |
|----------|--------|
| Código | `/opt/easynodeone/dev/app` |
| Rama | `develop` |
| BD | `easynodeone_dev` @ `127.0.0.1:5432` (`/opt/easynodeone/dev/.env`) |
| Servicio | `easynodeone-dev` · puerto **9101** |
| URL | https://appdev.easynodeone.com |
| Org de prueba clon Relatic | **#3** «Relatic Panama Dev» |

**Después de cambiar Python en certificados:** `sudo systemctl restart easynodeone-dev` (los workers importan rutas al arrancar; los templates HTML se leen del disco en cada request).

---

## 2. Modelo de tres capas (no confundir)

Un certificado de evento usa **tres piezas**. No son duplicados: cada una tiene tabla y responsabilidad distinta.

```
Event (has_certificate=true)
    │
    ├─► certificate_events  ──► FORMATO institucional (metadatos)
    │       event_required_id = event.id
    │       institution, rector, logos URL, fechas, code_prefix EVT
    │
    ├─► certificate_templates ──► PLANTILLA visual (diseño PDF)
    │       json_layout, editor /admin/certificate-templates/editor/<id>
    │       Vinculada en event.certificate_template → {"visual_template_id": N}
    │
    └─► event_certificate ──► PDF EMITIDO por participante
            participant_id, certificate_number, certificate_url, QR
```

### Reglas de negocio acordadas (obligatorias)

| Pieza | Automático | Manual operador | Prohibido |
|-------|------------|-----------------|-----------|
| **Formato** (`certificate_events`) | Sí: al marcar certificado y guardar/abrir editar | Editar en Eventos→Certificados→**Formato** (abre editor único en `/admin/certificate-events`) | Borrar si está vinculado |
| **Plantilla** (`certificate_templates`) | Solo **crear** si no existe | Elegir en formulario evento o **Plantilla** (editor) | **Sobrescribir** `json_layout` si ya tiene contenido de usuario |
| **PDF** (`event_certificate`) | **No** | Check-in + **Generar** en Eventos→Certificados | — |

### Motor de render (un solo PDF final)

Archivo: `backend/nodeone/modules/events/services/certificates.py` → `_render_event_certificate_pdf_bytes`.

1. Si hay plantilla visual vinculada → `render_pdf_from_json_layout` (diseño del editor).
2. Si no → `render_institutional_pdf` (layout clásico con datos del formato).

**No hay dos plantillas activas a la vez**; hay formato (datos) + plantilla visual (diseño opcional pero habitual).

---

## 3. Código único — dónde está cada cosa

### Punto único de garantía (formato + plantilla)

**`backend/nodeone/services/certificate_assets.py`**

| Función | Cuándo se llama |
|---------|-----------------|
| `ensure_certificate_assets_for_event(db, event)` | Núcleo: crea/reutiliza formato + plantilla + enlace `template_id` |
| `sync_event_certificate_on_save(...)` | POST create/edit evento (desde `routes.py`) |
| `event_certificate_ui_context(...)` | GET editar evento, pantalla Certificados, preview |
| `ensure_all_event_certificate_formats(db)` | Reparación masiva sin filtro org |
| `repair_certificates_job(db)` | Cron / script manual por organización |
| `find_event_certificate_format(...)` | Busca por **`event_required_id`** primero (no solo `organization_id`) |

### Rutas eventos

**`backend/nodeone/modules/events/routes.py`**

| Hook | Función |
|------|---------|
| POST create/edit | `_save_event_certificate_assets` → `sync_event_certificate_on_save` |
| GET edit (tab certificado) | `_event_certificate_form_context(..., ensure=True)` |
| `/admin/events/<id>/certificates` | `event_certificate_ui_context(..., ensure=True)` |
| Duplicar evento | `ensure_certificate_assets_for_event` si `has_certificate` |

### API admin formatos MEM/REG + listado EVENTO

**`backend/nodeone/modules/certificates/api_routes.py`** (shim: `certificate_routes.py`)

- `GET /api/admin/certificate-events` devuelve MEM/REG **y** filas `kind: event_seminar` (formatos con `event_required_id`).
- Los formatos de evento **no** se crean desde el modal «Nuevo formato» (rechazo anti-huérfanos); se crean al guardar el evento.
- `_certificate_event_for_admin_api(event_id)`: GET/PUT por id acepta formatos del scope admin **o** vinculados por `event_required_id` (org del evento puede ≠ scope catálogo admin).

### Vistas admin certificados (páginas HTML)

**`backend/nodeone/modules/admin_certificate_pages/routes.py`**

- `/admin/certificate-events` — editor único de formato (modal `#eventModal`).
- `/admin/certificate-templates/editor/<id>` — editor visual plantilla.
- `_admin_certificate_return_url()` — valida query `?return=` (path interno `/admin/...`) para flujo anidado desde evento.

### Emisión PDF

**`backend/nodeone/modules/events/services/certificates.py`**

- `create_event_certificate`, `regenerate_event_certificate`, `generate_bulk_for_event`
- `_write_certificate_pdf_file`: si la ruta legada no es escribible, guarda en `uploads/certificates/<org_id>/<event_id>/`
- Render visual: `nodeone.services.certificate_render.render_pdf_from_json_layout`

### Motor render y HTTP compartido (fase refactor 2)

| Módulo | Rol |
|--------|-----|
| `nodeone/services/certificate_render.py` | JSON layout → HTML → PDF (WeasyPrint) |
| `nodeone/services/certificate_http.py` | `certificate_base_url()`, `certificates_upload_dir()` |
| `nodeone/core/admin_api.py` | `admin_required_json` para APIs admin certificados |

### Reparación manual

```bash
cd /opt/easynodeone/dev/app/backend
source /opt/easynodeone/dev/venv/bin/activate
NODEONE_ROOT=/opt/easynodeone/dev/app python repair_certificates_job.py
```

---

## 4. UI — botones en Eventos → Certificados

| Botón | Color / icono | Qué hace | Tabla |
|-------|---------------|----------|-------|
| **Formato** | Azul, engranaje | Enlace a **editor único** `/admin/certificate-events?edit=<format_id>&return=/admin/events/<id>/certificates` | `certificate_events` |
| **Plantilla** | Amarillo, paleta | Editor visual `/admin/certificate-templates/editor/<id>?return=...` | `certificate_templates` |
| **Vista previa** | Celeste, ojo | PDF de ejemplo (no guarda en BD) | — |

**No hay modal duplicado** en `templates/admin/events/certificates.html` (eliminado jun 2026). Formato y Plantilla reutilizan las pantallas globales de certificados.

### Navegación con contexto de evento (`?return=`)

Problema resuelto: al salir de Formato/Plantilla el operador no debe quedar en el catálogo global sin rastro del evento.

| Origen | URL destino | Al guardar / volver / cerrar modal |
|--------|-------------|-------------------------------------|
| Eventos → Certificados → **Formato** | `/admin/certificate-events?edit=N&return=/admin/events/E/certificates` | Vuelve a certificados del evento E |
| Eventos → Certificados → **Plantilla** | `/admin/certificate-templates/editor/T?return=...` | Botón «Volver a certificados» y guardar redirigen al evento |

En **Formatos de certificado** con `return`: breadcrumb Eventos → Certificados del evento → Formato; botón «Volver a certificados del evento» en cabecera y en pie del modal.

Sin `return` (entrada desde menú admin): comportamiento clásico del módulo certificados.

En **editar evento** (pestaña certificado): alerta verde con **Formato #N** si ya existe; enlace a vista previa y emitir PDFs.

En **`/admin/certificate-events`**: filas **EVENTO** con mismos enlaces; el ojo de filas MEM/REG usa otra API (`/api/admin/certificate-events/preview`).

---

## 5. Flujo operativo resumido

1. Evento → activar **Este evento incluye certificado** → **Guardar** → redirect a pestaña certificado + flash `Formato creado: #XX`.
2. Opcional: **Plantilla** → editor visual → **Guardar**.
3. **Participantes** → importar / alta → **check-in** (o tipo `reviewer`).
4. **Certificados** → Generar todos los elegibles o por participante.
5. Regenerar PDF si cambió la plantilla (botón sync en listado emitidos).

**Elegibilidad:** `attendance_status` en `checked_in`/`attended` **o** `participant_type == reviewer`.

---

## 6. Historial de incidentes y fixes (jun 2026)

| Síntoma | Causa | Fix |
|---------|-------|-----|
| 500 en `/admin/events/N/certificates` | Gunicorn sin reiniciar; ruta `preview` no registrada | `systemctl restart easynodeone-dev` |
| «No se crea el formato» | Plantilla validada antes que `ensure` → rollback; formato existía pero no se mostraba | Refactor `sync_event_certificate_on_save`; flash + redirect `?tab=certopts` |
| Formato no visible en admin | `/admin/certificate-events` solo listaba MEM/REG | API + UI filas EVENTO |
| 500 al **regenerar** PDF | Sync Relatic: archivos `dev:nodeone`, ACL grupo sin escritura; Gunicorn `nodeone` | `chown nodeone:nodeone` en `static/uploads/certificates/`; `_write_certificate_pdf_file` con fallback de ruta |
| Rutas PDF `certificates/1/3/...` en org 3 | Certificados clonados con path org 1 | Regenerar reescribe; nuevos usan `organization_id_for_event(event)` |
| Botón **Formato** no hace nada | JS ejecutaba `bootstrap.Modal` antes de cargar Bootstrap (`defer`) | Eliminado modal local; enlace al editor único |
| Dos UIs editando el mismo formato | Modal recortado en Eventos→Certificados + modal completo en Formatos | Un solo editor; `?edit=` abre modal en `/admin/certificate-events` |
| Operador perdido al salir de Formato/Plantilla | Sin `return` al módulo global | `?return=/admin/events/<id>/certificates` + breadcrumb y redirección |

---

## 7. Estado BD Dev (post-sync Relatic → org 3, jun 2026)

Eventos con certificado (ejemplo):

| Evento | Formato `certificate_events` | Plantilla visual |
|--------|------------------------------|------------------|
| #2 | #23 | #2 |
| #3 | #24 | #4 |
| #5 | #25 | #8 |

Verificación: eventos con `has_certificate=true` sin fila `event_required_id` → ejecutar `repair_certificates_job.py`.

---

## 8. Commits relevantes (certificados eventos)

| Commit | Descripción |
|--------|-------------|
| `4ce0976` | Fase 1 `ensure_certificate_assets` anti-huérfanos |
| `f3534c0` | Unificación sync/UI, listado EVENTO, PDF regenerate resiliente, tests |
| `1696aba` | Docs contexto EN1 certificados de eventos |
| `1d878d4` | Editor único Formato/Plantilla, `?return=` navegación evento, API org evento |

---

## 9. Pendiente / fuera de alcance cerrado

| Item | Estado |
|------|--------|
| Cron `repair_certificates_job` en `/etc/cron.d/` | Pendiente |
| Fase 2: auto-emitir PDF al check-in | No acordado |
| Quitar ojo duplicado en filas EVENTO de certificate-events | Opcional UX |
| Despliegue relatic `1d878d4` | Hecho (pull `develop` + restart `easynodeone-relatic`, jun 2026) |
| Commit `docs/MANUAL_USUARIO_RELATIC_GUIA_PANTALLA.md` | Pendiente (archivo local sin commit) |

### Refactor certificados (plan jun 2026)

| Fase | Estado | Notas |
|------|--------|-------|
| **0 Quick wins** | Hecho | `institutional_template_id` muerto; `event_certificates.html` eliminado; `analytics.py` y `create_certificate_tables.py` → `backend/scripts/archive/`; `nodeone/modules/certificates/manifest.py` |
| **1 Tests** | Hecho | `tests/events/test_event_certificates.py`, `tests/test_certificate_verify.py` |
| **2 Motor render + helpers** | Hecho | `certificate_render.py`, `certificate_http.py`, `admin_api.admin_required_json` |
| **3 Mover blueprints** | Hecho | `nodeone/modules/certificates/` + shims en `backend/` |
| **4 Consolidar services** | Hecho | `certificate_visual_templates` + `certificate_org`; form helpers en `certificate_assets`; shim legacy |
| **5 certificates_builder** | Hecho | Editor canónico: `/admin/certificate-templates/editor`; builder redirige; upload en `/api/templates/upload-image` |
| **6 app.py** | Epic aparte | — |

### Deploy — limpieza post-pull

Scripts: `scripts/post_deploy_cleanup.sh`, `deploy_cleanup_manifest.txt`, `deploy_with_cleanup.sh`.  
Contexto operativo e IA: [`docs/EN1_DEPLOY_LIMPIEZA_CONTEXTO.md`](EN1_DEPLOY_LIMPIEZA_CONTEXTO.md).

---

## 10. Documentos relacionados

| Documento | Audiencia |
|-----------|-----------|
| `backend/docs/MANUAL_ADMIN_CERTIFICADOS_EN1.md` | Admin usuario final |
| `backend/docs/MANUAL_USUARIO_CERTIFICADOS_EN1.md` | Participante |
| `docs/MANUAL_OPERATIVO_RELATIC_CERTIFICADOS_EVENTOS.md` | Operación Relatic |
| `docs/PLAN_EVENTOS_EN1_SEGUIMIENTO.md` | Checklist módulo eventos |
| `AGENTS.md` | Protocolo IA / entornos |

---

## 11. Checklist rápido para IA (nueva tarea certificados evento)

1. ¿Solo Dev EN1? → sí salvo GO explícito otro silo.
2. ¿Formato o PDF? → formato = `certificate_events`; PDF = `event_certificate`.
3. ¿Tocar plantilla existente? → **no** sobrescribir `json_layout` con contenido.
4. ¿Cambio en `routes.py`? → preferir extender `certificate_assets.py`.
5. ¿Probar en servidor? → restart `easynodeone-dev` tras cambios Python.
6. ¿Sync/rsync uploads? → permisos `nodeone:nodeone` en `static/uploads/certificates/`.
7. ¿UI Formato desde evento? → **no** duplicar modal; enlace `?edit=` + `?return=` a `/admin/events/<id>/certificates`.
8. ¿Cambiar navegación certificados? → `admin_certificate_pages/routes.py`, `certificate_events.html`, `certificates.html`.
9. ¿Tests emisión/verify? → `tests/events/test_event_certificates.py`, `tests/test_certificate_verify.py` antes de mover PDF o `/verify`.
