# IIUS — Coaching V1 + ECalendar (handoff)

**Fecha:** 2026-07-08  
**Rama:** `feature/iius-coaching-v1`  
**Tag despliegue:** `iius-coaching-v1-20260708`  
**Prod:** `apps.internationalinstitute.us` (org 1, PostgreSQL `iius_nodeone`)

## Alcance

| Pieza | Detalle |
|-------|---------|
| Catálogo | `/coaching` — 7 programas `program_type=coaching`, USD 99 |
| Agenda post-pago | Solo `coaching-individual` y `coaching-ejecutivo` (`requires_agenda=true`) |
| Ruta agenda | `GET/POST /inscripcion/agendar/<enrollment_id>` |
| ECalendar | OAuth Google Calendar, slots 60 min, admin `/admin/ecalendar` |
| Landing WP | `[iius_coaching_en1_vitrina]` en `/coaching/` — vitrina EN1 |
| UX inscripción | Bloque «¿Cómo funciona?» (3 o 4 pasos según agenda) |

**Flujo:** Landing → Inscribirme (EN1) → Pagar → (si agenda) Agendar → Google Calendar.

## Migraciones

```bash
cd backend && source ../.venv/bin/activate
python migrate_ecalendar_settings.py
python migrate_academic_program_agenda_v1.py   # o SQL equivalente en prod
```

En prod IIUS (2026-07-08) la migración agenda se aplicó vía `psql` por lock del script Python.

## Semilla coaching

```bash
python scripts/seed_iius_coaching_programs.py 1
```

## WordPress (landing)

Mu-plugins en `deploy/wordpress/`:

- `iius-coaching-en1-vitrina.php` — shortcodes vitrina + sync
- `patch_iius_coaching_landing.php` — parche página 208 (ejecutar una vez)
- `iius-coaching-booking.php` — **legacy**, no flujo principal

## Validación mínima

1. `/coaching` lista 7 programas; `/programas` no incluye coaching.
2. Inscripción `coaching-de-vida` → pago → gracias (sin agenda).
3. Inscripción `coaching-individual` → pago → pantalla agenda → evento GCal.
4. Dashboard «Mi coaching» con enrollment pendiente/programado.
5. `/api/ecalendar/health` → `oauth_valid: true`.

## Integración monorepo

Este host **no tiene** `/opt/easynodeone/dev/app`. Tras merge a `develop`:

1. Cherry-pick o PR desde `feature/iius-coaching-v1`.
2. Staging al tag/commit acordado.
3. Prod IIUS: `git fetch && git checkout iius-coaching-v1-20260708` (o merge a `iius-product` según acuerdo).

Contexto operativo ampliado: `Easy-Wiki/05_Proyectos/iius/estado_actual_iius.md`.
