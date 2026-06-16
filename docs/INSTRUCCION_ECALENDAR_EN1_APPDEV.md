# ECalendar V1 — Instrucción para programador EN1 (appdev → appprd)

Documento operativo para implementar la API de agenda EasyTech en **Easy NodeOne (EN1)**.  
El sitio estático **Site_2026** consume estos endpoints; **no** poner OAuth ni secretos en HTML.

---

## Contexto

| Tema | Detalle |
|------|---------|
| **Por qué ECalendar** | Calendly no permite etiquetar citas por producto del ecosistema EasyTech. |
| **EasyTech** | Sitio estático (Site_2026) + EN1 en prod (`appprd.easynodeone.com`). |
| **V1** | 1 Google Calendar + 1 URL `/agenda` + producto en formulario + título `[Producto] Demo con …`. |
| **OAuth Google** | Solo en servidor EN1 (`/api/ecalendar/*`), nunca en el HTML del sitio. |

---

## Flujo appdev → appprd

```text
Repo EN1 → implementar /api/ecalendar/*
         → deploy appdev
         → probar (curl + agenda.html apuntando a dev)
         → deploy appprd
         → sitio apunta a appprd
         → apagar Calendly
```

No hay que «levantar EN1» aparte: solo desplegar código nuevo en **appdev** y luego en **appprd**.

---

## Endpoints EN1 (V1)

| Método | Ruta | Función |
|--------|------|---------|
| GET | `/api/ecalendar/health` | Estado del módulo y credenciales Google |
| GET | `/api/ecalendar/products` | 11 productos para `<select>` |
| GET | `/api/ecalendar/availability?date=YYYY-MM-DD` | Slots libres (30 min, Lun–Vie 9–17, Panamá) |
| POST | `/api/ecalendar/bookings` | Crea evento en GCal; título `[Producto] Demo con Nombre` |

Prefijo blueprint: `url_prefix=/api/ecalendar`.

---

## Configuración en EN1 (pantalla admin)

**Ruta:** `/admin/ecalendar` (menú Configuración → Agenda ECalendar).

Todo se guarda en BD (`ecalendar_settings` por tenant). **No** usar variables de entorno para credenciales ni horarios.

| Campo en pantalla | Uso |
|-------------------|-----|
| Activar ECalendar | Si está apagado, la API pública responde 503 |
| Usar para agenda pública | Qué tenant alimenta Site_2026 (solo uno activo) |
| Cuenta Google (referencia) | `easytechservices25@gmail.com` — solo documentación |
| Client ID / secret / refresh token | OAuth servidor |
| ID calendario | `primary` o ID de «EasyTech Citas» |
| Horario, lead, CORS, productos JSON | Reglas V1 |

API admin: `GET/POST /api/admin/ecalendar/config`, `POST /api/admin/ecalendar/test` (prueba OAuth).

Opcional en servidor: `NODEONE_SKIP_ECALENDAR_BLUEPRINT=1` para desactivar el módulo.

Reglas de negocio:

- Slot **30 min**
- **Lead 4 h** (no reservar antes)
- Horizonte **30 días**
- **Lun–Vie 9:00–17:00** (`America/Panama`)
- Slot ocupado → **409 Conflict**
- CORS solo orígenes en `ECALENDAR_ALLOWED_ORIGINS`

---

## Cuenta y calendario Google

| Ítem | Valor |
|------|--------|
| Cuenta | `easytechservices25@gmail.com` |
| Calendario | Uno solo (ideal: «EasyTech Citas»; en dev puede ser de prueba con prefijo `[TEST]` en título) |

**Importante:** rotar `GOOGLE_CLIENT_SECRET` antes de appdev. No copiar secretos al repo ni a Site_2026.

---

## Payloads JSON

### GET `/api/ecalendar/products`

```json
{
  "ok": true,
  "products": [
    { "id": "easy_odoo", "name": "Easy Odoo" },
    { "id": "easy_nodeone", "name": "Easy NodeOne" }
  ]
}
```

### GET `/api/ecalendar/availability?date=2026-06-15`

```json
{
  "ok": true,
  "date": "2026-06-15",
  "timezone": "America/Panama",
  "slots": [
    { "start": "2026-06-15T09:00:00-05:00", "end": "2026-06-15T09:30:00-05:00" }
  ]
}
```

### POST `/api/ecalendar/bookings`

Request:

```json
{
  "product_id": "easy_odoo",
  "slot_start": "2026-06-15T10:00:00-05:00",
  "name": "Juan Pérez",
  "email": "juan@empresa.com",
  "phone": "+50760000000",
  "company": "ACME SA",
  "notes": "Interesado en inventario"
}
```

Response 201:

```json
{
  "ok": true,
  "booking_id": "abc123eventid",
  "title": "[Easy Odoo] Demo con Juan Pérez",
  "slot_start": "2026-06-15T10:00:00-05:00",
  "slot_end": "2026-06-15T10:30:00-05:00"
}
```

Response 409:

```json
{ "ok": false, "error": "slot_unavailable" }
```

---

## Estructura EN1 (implementado)

```text
backend/nodeone/modules/ecalendar/
  __init__.py
  routes.py
  products.py
  services/
    config.py
    availability.py
    google_calendar.py
    bookings.py
```

Registro: `nodeone.core.features.register_ecalendar_blueprint`.

---

## Trabajo paralelo Site_2026 (cuando appdev responda)

- `agenda.html` + `ecalendar.js` → formulario propio (sin Calendly)
- `portal-urls.js` → `ecalendarApiBase: https://appdev.easynodeone.com/api/ecalendar` (QA)
- Luego cambiar a `https://appprd.easynodeone.com/api/ecalendar`

---

## Checklist rápido appdev

- [ ] Rotar client secret Google (si se filtró)
- [ ] Módulo `ecalendar` en repo EN1 (`develop`)
- [ ] Deploy appdev
- [ ] Admin → **Agenda ECalendar**: credenciales, calendario, CORS, activar
- [ ] **Probar OAuth** desde la pantalla
- [ ] `GET /api/ecalendar/health` y `GET /api/ecalendar/products`
- [ ] `POST /api/ecalendar/bookings` de prueba → evento en Google Calendar
- [ ] Mismo slot otra vez → **409**
- [ ] Integrar `agenda.html` (Site_2026)
- [ ] Promover a appprd
- [ ] Sitio → appprd; apagar Calendly

---

## QA / rollback

| Prueba | Esperado |
|--------|----------|
| Fecha sábado | `slots: []` |
| Fecha pasada | 400 |
| Sin credenciales Google | health `configured: false`, bookings 503 |
| CORS origen no listado | sin header `Access-Control-Allow-Origin` |

Rollback: desregistrar blueprint (`NODEONE_SKIP_ECALENDAR_BLUEPRINT=1`) o revertir deploy.

**Roadmap V2 (pospuesto):** ver `docs/ECALENDAR_ROADMAP.md`.

---

## Fuera de V1

- Múltiples calendarios por producto
- Recordatorios email desde EN1
- Panel admin de citas en EN1
- Sincronización bidireccional Calendly
