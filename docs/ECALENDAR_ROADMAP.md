# ECalendar — Roadmap EN1

**Última actualización:** junio 2026  
**Módulo:** `nodeone/modules/ecalendar/` · agenda pública `easytech.services/agenda.html`

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

## Línea de tiempo sugerida

```text
Ahora        → Cerrar V1 (agenda.html E2E, appprd, apagar Calendly)
Siguiente    → V2.0a–b (email + confirmación + GCal diferido)
Después      → V2.0c (CRM + expiración) + V2.1 (abuso / Turnstile)
```

---

## Referencias

| Documento | Uso |
|-----------|-----|
| `ECALENDAR_ROADMAP.md` | Este archivo |
| `ECALENDAR_ENTREGA_EJECUTIVA.md` | Estado ejecutivo V1 |
| Especificación V2 (jun 2026) | Ticket / wiki producto (CRM + confirmación email) |
