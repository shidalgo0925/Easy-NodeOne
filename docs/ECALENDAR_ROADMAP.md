# ECalendar — Roadmap EN1

**Última actualización:** julio 2026  
**Módulo:** `nodeone/modules/ecalendar/` · consumidores: `easytech.services/agenda.html` · **IIUS** (planificado, ver §IIUS)

---

## Versión actual: **V1** (en curso — cerrar GO dev/prod)

**Comportamiento:** `POST /bookings` valida slot (freebusy) y **crea evento en Google Calendar de inmediato**.

| Hito | Estado |
|------|--------|
| API `/api/ecalendar/*` (health, products, availability, bookings) | Implementado |
| OAuth servidor + `ecalendar_settings` (BD) | Implementado |
| Admin `/admin/ecalendar` | Implementado |
| CORS `easytech.services` | Configurar por tenant |
| Landing `agenda.html` → API EN1 | Web EasyTech |
| QA V1 (`docs/ECALENDAR_QA_CHECKLIST.md`) | Cerrar en appdev → appprd |
| Sustituir Calendly en producción | Tras GO prod |

**Documentación V1:** `INSTRUCCION_ECALENDAR_EN1_APPDEV.md` · `ECALENDAR_ADMIN_GUIDE.md` · `ECALENDAR_QA_CHECKLIST.md`

**No mezclar con:** appointments internos, CRM calendar, dashboard miembro, eventos académicos.

---

## Versión planificada: **V2** — **POSPUESTA** (nueva versión posterior)

**Decisión (jun 2026):** V2 **no** se implementa en el cierre de V1. Se aborda en una **versión dedicada** cuando V1 esté operativo en prod y el negocio dé GO explícito.

### Objetivo V2 (resumen)

Flujo en dos pasos respecto a V1:

1. `POST /bookings` → lead CRM + booking `pending_email` + **email** con enlace (sin evento GCal definitivo).
2. `GET /bookings/confirm?token=...` → confirmación → **entonces** `events.insert` en Google Calendar.

### Alcance V2 (backlog)

| Bloque | Prioridad sugerida |
|--------|-------------------|
| Tabla `ecalendar_bookings` + estados (`pending_email`, `confirmed`, `expired`, …) | V2.0a |
| Cambiar `POST /bookings` (respuesta `pending_confirmation`) | V2.0a |
| Hold de slots en `GET /availability` (bookings pendientes no expirados) | V2.0a |
| Email transaccional «Confirmá tu cita» (SMTP tenant EasyTech) | V2.0b |
| `GET /bookings/confirm` + redirect a `agenda.html?confirmed=1` | V2.0b |
| Integración CRM (`crm_create_lead_from_booking`, etapas pipeline) | V2.0c |
| Job expiración TTL (`ECALENDAR_CONFIRM_TTL_HOURS`, default 24 h) | V2.0c |
| Rate limit, validación Turnstile, `resend-confirmation` | V2.1 |

### Cambios landing (tras V2 EN1)

- Post-submit: «Revisá tu correo» (no «cita confirmada»).
- Pantalla éxito con `?confirmed=1` tras clic en email.
- Sin OAuth ni secretos en el HTML.

### Prerrequisitos antes de GO V2

- V1 en prod con QA cerrado.
- SMTP operativo para tenant comercial EasyTech.
- Etapas CRM definidas para leads desde agenda (`source: easytech.services/agenda`).
- Especificación V2 acordada (confirmación email + CRM lead) — revisar notas técnicas EN1 (servicio CRM interno, no API pública; credenciales OAuth en BD, no `.env`).

### Fuera de alcance V2

- Múltiples calendarios por producto.
- Pipeline CRM completo (cotización, factura).
- WhatsApp / Easy Converso automático.
- Admin UI nueva de citas (usar CRM + GCal).

---

## IIUS — Agenda coaching (backlog **IIUS-ECAL-01**)

**Contexto (jul 2026):** El sitio marketing [internationalinstitute.us](https://internationalinstitute.us/) tiene menú **Calendario** y segmento **Coaching** (Personal / Ejecutivo). La plataforma académica vive en `apps.internationalinstitute.us` (tenant IIUS, org 1). **No** documentado ni implementado para IIUS; solo existe el patrón EasyTech (§V1).

### Qué **no** es

| Pieza | Rol | ¿Usar para calendario coaching? |
|-------|-----|----------------------------------|
| `/inscripcion/<slug>` | Matrícula + pago diplomados/cursos | **No** — funnel distinto (PayPal, `AcademicProgramEnrollment`) |
| WordPress `internationalinstitute.us` | Marketing | **No** lógica OAuth/API — solo **enlace** al landing EN1 |
| `appointments` / citas internas EN1 | Servicios + asesores tenant | **No** — otro módulo |
| Eventos académicos / campus | Seminarios, check-in | **No** |

### Arquitectura acordada (borrador)

```text
internationalinstitute.us  →  menú «Calendario» / «Coaching»
         │  (solo URL manual, como /inscripcion/*)
         ▼
apps.internationalinstitute.us/agenda   ← landing público EN1 (nuevo)
         │
         ▼
/api/ecalendar/*   tenant IIUS (ecalendar_settings org 1)
         │
         ▼
Google Calendar (cuenta/calendario IIUS, productos: Coaching Personal, Coaching Ejecutivo, …)
```

**Ventaja:** misma API que EasyTech; landing en EN1 evita CORS cross-domain si la página vive en `apps.*` (o CORS `https://internationalinstitute.us` si se prefiere embed mínimo en WP).

### Alcance propuesto (tras GO)

| # | Tarea | Notas |
|---|--------|-------|
| 1 | Ruta pública EN1 `/agenda` (o `/coaching/cita`) | Template IIUS (`iius-enrollment-landings.css` o variante); JS consume `/api/ecalendar/*` |
| 2 | Config admin `/admin/ecalendar` tenant IIUS | OAuth Google, horarios, calendario propio; `use_for_public_agenda` según política multi-tenant |
| 3 | `products_json` IIUS | Ej. `coaching_personal`, `coaching_ejecutivo` — **no** reutilizar catálogo 11 productos EasyTech |
| 4 | WordPress | Actualizar menú **Calendario** → URL absoluta al landing EN1 |
| 5 | QA | Smoke en `apps.internationalinstitute.us`; checklist derivado de `ECALENDAR_QA_CHECKLIST.md` |
| 6 | Deploy IIUS prod | `git pull` + restart `nodeone.service` (sin editar silo a mano) |

### Prerrequisitos

- V1 ECalendar estable (API + admin) — ver §V1.
- Cuenta Google Calendar operativa para IIUS (OAuth refresh token en BD).
- Decisión negocio: productos coaching, horario, lead time, quién atiende las citas.

### Fuera de alcance (IIUS-ECAL-01)

- Mezclar agenda con `/inscripcion/*`.
- Sync automático WordPress ↔ EN1.
- V2 confirmación por email (hasta GO V2 global).

### Referencia cruzada IIUS

| Documento | Uso |
|-----------|-----|
| `backend/docs/IIUS_CIRCUIT_STATUS.md` | Backlog **IIUS-ECAL-01** en tabla roadmap |
| `docs/INSTRUCCION_ECALENDAR_EN1_APPDEV.md` | API y admin (mismo motor) |
| `docs/MANUAL_OPERATIVO_RELATIC_CERTIFICADOS_EVENTOS.md` | No aplica — solo certificados eventos |

---

## Línea de tiempo sugerida

```text
Ahora        → Cerrar V1 EasyTech (agenda.html E2E, appprd, apagar Calendly)
Paralelo     → IIUS-ECAL-01 (landing /agenda en apps.*) tras GO explícito IIUS
Siguiente    → V2.0a–b (email + confirmación + GCal diferido)
Después      → V2.0c (CRM + expiración) + V2.1 (abuso / Turnstile)
```

---

## Referencias

| Documento | Uso |
|-----------|-----|
| `ECALENDAR_ROADMAP.md` | Este archivo (incl. §IIUS **IIUS-ECAL-01**) |
| `ECALENDAR_ENTREGA_EJECUTIVA.md` | Estado ejecutivo V1 |
| Especificación V2 (jun 2026) | Ticket / wiki producto (CRM + confirmación email) |
