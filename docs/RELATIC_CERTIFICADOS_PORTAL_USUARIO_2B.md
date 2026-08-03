# Relatic — Nivel 2B: Portal «Mis Certificados»

Pantalla unificada donde cada usuario autenticado ve y descarga sus certificados emitidos.

## Acceso (UI)

| Entrada | Ruta |
|---------|------|
| **Principal** | **Documentos → Certificados** → `/certificates` |
| Perfil (dropdown) | Mis Certificados → `/certificates` |
| Mi Perfil | botón «Mis Certificados» → `/certificates` |
| Alias legado | `/my/certificates` → redirige a `/certificates` |

## Rutas HTTP

| Acción | Ruta | Notas |
|--------|------|-------|
| Lista unificada | `GET /certificates` | Eventos (arriba) + membresía (abajo, si el módulo está activo) |
| Descarga evento | `GET /my/certificates/<certificate_id>/download` | Solo certificados de evento propios |
| Descarga membresía | `GET /api/certificates/<certificate_code>/download` | PDF ya emitido (módulo Canva / REG·MEM) |
| Solicitar membresía | `POST /api/request-certificate/<certificate_event_id>` | Genera PDF si cumple requisitos |
| Listado API membresía | `GET /api/my-certificates` | Usado por la sección inferior de la plantilla |
| Verificación pública | `GET /certificates/verify/<certificate_number>` | Sin login; sin cambios respecto al flujo admin |

## Contenido de la pantalla `/certificates`

1. **Certificados de eventos** (módulo `events` activo en el tenant)  
   Tabla con evento, fecha, código, emisión, estado, **Descargar PDF** y **Verificar**.

2. **Certificados de membresía** (módulo `certificates` activo)  
   Tarjetas con tipos REG/MEM: solicitar, descargar o ver requisitos pendientes.

Si el usuario no tiene certificados de evento, la primera sección muestra un mensaje informativo (no error).

## Asociación usuario ↔ certificado de evento

Al entrar en `/certificates`, si el módulo de eventos está activo:

1. Se intenta vincular participantes huérfanos: `event_participant.user_id` se rellena cuando el email coincide con el del usuario.
2. Se listan certificados donde el participante cumple **una** de:
   - `event_participant.user_id = current_user.id` (prioridad)
   - `event_participant.email` (normalizado, case-insensitive) = email del usuario

Solo certificados con `status != 'revoked'` e `is_active = true`.

La descarga comprueba de nuevo que el certificado pertenece al usuario; si no, **HTTP 403**.

## Diferencia con admin

| Ámbito | Ruta típica |
|--------|-------------|
| Usuario | `/certificates`, `/my/certificates/.../download` |
| Admin eventos | `/admin/events/<id>/certificates`, descarga desde panel admin |
| Admin plantillas membresía | `/admin/certificate-events`, `/admin/certificate-templates` |

Los certificados PDF institucionales de eventos (Nivel 2A) se **emiten** en admin; el usuario solo **descarga** los ya generados (2B).

Manual operativo admin (emisión, import participantes, QR): `docs/MANUAL_OPERATIVO_RELATIC_CERTIFICADOS_EVENTOS.md`.

## Pruebas (Relatic Panamá DEV — `:9105`)

| # | Caso | Resultado esperado |
|---|------|-------------------|
| 1 | Usuario con email del participante y cert generado | Ve fila en «Certificados de eventos» + Descargar + Verificar |
| 2 | Usuario sin certificados de evento | Mensaje en sección eventos; membresía según módulo |
| 3 | Descarga de `certificate_id` ajeno | HTTP 403 |
| 4 | Certificado revocado | No aparece en lista |
| 5 | PDF ausente en disco | Flash «Certificado no disponible, contacte al administrador» |
| 6 | Admin descarga desde `/admin/events/...` | Sin cambios |
| 7 | `/certificates/verify/EN1-2026-736191` | Sigue respondiendo |
| 8 | `/my/certificates` | Redirige 302 a `/certificates` |

### Datos de prueba (clon `relatic_panama_dev`)

- Evento: **Certificados para revisores** (id 3)
- Certificado: `EN1-2026-736191`
- Participante: Smoke Test Participante A — `smoke-cert-a@relatic.test`

Usuario de prueba: cuenta con ese email (o vincular `event_participant.user_id`).

### Validación ejecutada (2026-06-08, `:9105`)

| # | Caso | Resultado |
|---|------|-----------|
| 1 | `smoke-cert-a@relatic.test` ve `EN1-2026-736191` | OK — `/certificates` 200, PDF 200 |
| 2 | Usuario sin certs (`shidalgo@relatic.org`) | OK — 0 filas en query eventos |
| 3 | Descarga `certificate_id` ajeno | OK — HTTP 403 |
| 4 | Revocados | OK — excluidos por query (`status != revoked`, `is_active`) |
| 5 | PDF en disco | OK — archivo presente (~15 KB) |
| 6 | Admin `/admin/events/.../download` | Sin cambios en código |
| 7 | `/certificates/verify/EN1-2026-736191` | OK — HTTP 200 |
| 8 | Alias `/my/certificates` | OK — redirige a pantalla unificada |

Usuario de prueba creado en clon: `smoke-cert-a@relatic.test` (participante A, evento 3).

### Comandos smoke (servidor)

```bash
# Sincronizar código dev → silo panama-dev y reiniciar
rsync -a --exclude '.git' --exclude 'venv' /opt/easynodeone/dev/app/ /opt/easynodeone/relatic-panama-dev/app/
sudo systemctl restart easynodeone-relatic-panama-dev.service

# Login → http://127.0.0.1:9105/certificates
# (o http://127.0.0.1:9105/my/certificates — mismo destino)
```

## Archivos

| Archivo | Rol |
|---------|-----|
| `backend/certificate_routes.py` | `GET /certificates` — pantalla unificada |
| `templates/certificates.html` | UI: eventos + membresía |
| `backend/nodeone/modules/events/services/user_certificates.py` | Query, vínculo por email, resolución PDF |
| `backend/nodeone/modules/events/user_certificates_routes.py` | Alias `/my/certificates`, descarga evento |
| `templates/my/event_certificates.html` | Plantilla legacy eliminada; lista unificada en `templates/certificates.html` |
| `backend/nodeone/core/features.py` | Registro blueprints |
| `templates/base.html`, `templates/profile.html` | Enlaces de menú |
