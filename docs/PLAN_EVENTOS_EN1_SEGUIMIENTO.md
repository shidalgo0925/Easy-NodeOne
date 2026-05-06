# Plan módulo Eventos + Participantes + Asistencia + Certificados (EN1)

**Silos:** principalmente `dev` (`/opt/easynodeone/dev/app`). Replicar a relatic/prod según despliegue.  
**Documento de control:** al cerrar un punto, actualizar la columna **Estado** y la fecha en **Notas**.

**Leyenda:** `HECHO` | `PARCIAL` | `PEND` | `N/A`

---

## A. Visión, datos y Excel

| # | Entrega | Estado | Notas |
|---|---------|--------|-------|
| A.1 | Objetivo de negocio (eventos, participantes, import, asistencia, certificados QR, verificación, revocación, export, UI) | HECHO | Flujo admin: eventos, participantes, import A–J, asistencia, PDF/QR, verify público, revocación, exports XLSX, UI |
| A.2 | Reglas de conceptos: Event / EventRegistration / EventParticipant / EventCertificate / User no mezclados | HECHO | Inscripción (`EventRegistration`) ≠ persona en evento (`EventParticipant`). Certificados (`EventCertificate`) sobre `EventParticipant`. `User` opcional en participante; no se auto-asigna en alta manual/import |
| A.3 | Excel «LISTA PARA CERTIFICADOS PARA REVISORES»: Hoja1, 7 col A–G | HECHO | Import + preview |
| A.4 | Formato extendido (cols H–J: tipo, pago, notas) | HECHO | Import + preview + confirm; sin H: casilla «lista revisores» → reviewer, si no → external (§29 / §4); pago por defecto not_required |
| A.5 | Modelo EventParticipant | HECHO | ORM + CRUD admin + import; asistencia y certificado en modelo |
| A.6 | `full_name` normalizado | HECHO | |
| A.7 | Validaciones import | HECHO | |

---

## B. Duplicados e import UI

| # | Entrega | Estado | Notas |
|---|---------|--------|-------|
| B.1 | Duplicados por evento | HECHO | |
| B.2 | Pantalla import + confirmación | HECHO | |

---

## C. Participantes admin y asistencia

| # | Entrega | Estado | Notas |
|---|---------|--------|-------|
| C.1 | Listado + acciones | HECHO | Incl. vista `/participants/<id>/certificate` + enlace «Certs.» |
| C.2 | CRUD manual new/edit/delete | HECHO | `/participants/new`, `/participants/<id>/edit`, POST delete |
| C.3 | Check-in `checked_in_at` / `checked_in_by` | HECHO | |
| C.4 | Ausente / pendiente | HECHO | |
| C.5 | Filtros asistencia | HECHO | Query `attendance=` |

---

## D. Certificados (modelo, código, archivos)

| # | Entrega | Estado | Notas |
|---|---------|--------|-------|
| D.1 | Modelo EventCertificate + esquema | HECHO | ORM + migración PG `backend/nodeone/services/migrations/002_event_participant_certificate_en1_pg.sql`; revocación y verify |
| D.2 | Código `REV-YYYY-XXXXXX` / `EN1-YYYY-XXXXXX` | HECHO | `services/certificates.py` |
| D.3 | QR + PDF en `static/uploads/certificates/<org>/<event>/` | HECHO | ReportLab + PNG QR |
| D.4 | Servicio `services/certificates.py` | HECHO | crear, revocar, bulk |
| D.5 | Deps qrcode / reportlab | HECHO | Ya en `requirements.txt` |

---

## E. Rutas y verificación

| # | Entrega | Estado | Notas |
|---|---------|--------|-------|
| E.1 | Rutas admin generate, download, revoke, export | HECHO | Motivo revocación opcional en UI |
| E.2 | Verificación pública sin PII completo | HECHO | Doc enmascarado; fechas evento, org emisora, título, vencimiento/expirado; 404 si código inexistente |
| E.3 | Elegibilidad: checked_in o reviewer | HECHO | `participant_eligible_for_certificate` |

---

## F. Exportaciones, multi-tenant, UI, calidad

| # | Entrega | Estado | Notas |
|---|---------|--------|-------|
| F.1 | Export participantes | HECHO | XLSX: identidad, tipo/categoría, fuente, pago, asistencia, check-in y quién registró, certificado, notas, ids |
| F.2 | Export certificados XLSX | HECHO | `/certificates/export.xlsx` |
| F.3 | Multi-tenant org en rutas admin | HECHO | Eventos admin vía `_scoped_events_query` (join creador + `user_in_org_clause` y org de sesión) |
| F.4 | Seguridad (no auto-usuario, únicos, revocación) | HECHO | Alta manual/import: `user_id=None`; número cert único; rutas `_scoped_*`; verify sin email/tel completos |
| F.5 | Mejoras visuales cards + tabs detalle evento | HECHO | Subnav con `?tab=` + estado activo; anchors |
| F.6 | Pruebas documentadas | HECHO | Checklist manual § abajo + `pytest backend/tests/events/test_participants_import.py` (`pytest` en `requirements.txt`) |

---

## Orden de trabajo recomendado (no saltar sin motivo)

1. ~~**C.3–C.4** — Asistencia.~~ ✓  
2. ~~**D.2–D.4 + E.1** — Certificado mínimo + rutas.~~ ✓  
3. ~~**E.2** — Verificación pública evento/membresía.~~ ✓  
4. ~~**C.1–C.2** — CRUD + acciones fila.~~ ✓  
5. ~~**E.3, F.2** — Elegibilidad + export cert.~~ ✓  
6. ~~**F.5–F.6** — Tabs/subnav, export participantes completo, tests.~~ ✓  

**Cierre v1 plan:** mantener solo smoke manual antes de subir a otro entorno y aplicar migración PG en cada BD nueva.

---

## Casos de prueba manual (F.6, smoke EN1 dev)

1. Lista admin eventos: vista tarjetas y tabla; portada placeholder vs imagen; badge estado legible.  
2. Editar evento: subnav con `?tab=` y anclas; enlaces a Inscripciones / Participantes / Import / Certificados / Catálogo descuentos.  
3. Import Excel: A–G y filas con H–J; preview (columnas tipo/pago/notas) → confirm → listado correcto.  
4. Check-in / ausente / pendiente conservan filtro `attendance=`.  
5. Crear participante manual y editar.  
6. Generar certificado (revisor o con check-in); PDF; verificación pública válida / revocado / código inexistente (404); vista «Certs.» por participante.  
7. Export participantes y export certificados `.xlsx` (columnas esperadas).

**Última revisión del checklist:** 2026-05-05 — plan tabla cerrado v1; smoke manual recomendado pre-deploy.
