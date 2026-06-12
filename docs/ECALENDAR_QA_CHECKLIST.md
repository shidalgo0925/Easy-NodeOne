# ECalendar V1 — QA Checklist

Lista de validación antes de declarar **GO** operativo (appdev) y antes de promover a **appprd**.

**Entorno referencia appdev:** `https://appdev.easynodeone.com`  
**Tenant referencia:** `organization_id=1` (Easy NodeOne - Dev)

Marcar cada ítem: ☐ pendiente · ☑ OK · ✗ falla

---

## 0. Pre-requisitos

| # | Verificación | Comando / acción | Esperado |
|---|--------------|------------------|----------|
| 0.1 | Código en remoto | `git log origin/develop -1` | Commits `70bc61e` + `e347d9c` (o posteriores) |
| 0.2 | Servicio activo | `systemctl is-active easynodeone-dev.service` | `active` |
| 0.3 | Tabla BD | `SELECT COUNT(*) FROM ecalendar_settings` | ≥ 1 fila para org admin |
| 0.4 | Google Calendar API | Google Cloud Console | API habilitada |
| 0.5 | OAuth client | Redirect `http://localhost:8765/oauth2callback` | Registrado |
| 0.6 | Refresh token | BD / admin | `has_google_refresh_token=true` |

---

## 1. Health

| # | Prueba | Comando | Esperado |
|---|--------|---------|----------|
| 1.1 | Health básico | `curl -s .../api/ecalendar/health` | HTTP 200, `ok:true` |
| 1.2 | Módulo habilitado | mismo JSON | `enabled:true` |
| 1.3 | Credenciales completas | mismo JSON | `google_connected:true` |
| 1.4 | OAuth válido | mismo JSON | `oauth_valid:true` |
| 1.5 | Calendario | mismo JSON | `calendar_id` = valor configurado |
| 1.6 | Productos cargados | mismo JSON | `products: 11` (o cantidad custom) |

**Ejemplo operativo:**

```json
{
  "ok": true,
  "enabled": true,
  "google_connected": true,
  "oauth_valid": true,
  "calendar_id": "primary",
  "products": 11
}
```

---

## 2. OAuth (admin)

| # | Prueba | Acción | Esperado |
|---|--------|--------|----------|
| 2.1 | Pantalla carga | GET `/admin/ecalendar` (sesión admin) | HTTP 200, formulario visible |
| 2.2 | GET config | `GET /api/admin/ecalendar/config` | `success:true`, `configured:true` |
| 2.3 | Secretos no expuestos | Revisar JSON config | Solo flags `has_google_*`, no secret en claro |
| 2.4 | Test OAuth UI | Botón **Probar OAuth** | Mensaje éxito |
| 2.5 | Test OAuth API | `POST /api/admin/ecalendar/test` | `{ "success": true }` |
| 2.6 | Sin credenciales | Borrar refresh (solo QA) → test | Error claro, no 500 |

---

## 3. Products

| # | Prueba | Comando | Esperado |
|---|--------|---------|----------|
| 3.1 | Lista productos | `curl -s .../api/ecalendar/products` | HTTP 200 |
| 3.2 | Estructura | JSON | `ok:true`, array `products` |
| 3.3 | Campos | cada item | `id` + `name` string no vacíos |
| 3.4 | Catálogo default | sin `products_json` custom | 11 productos (Easy Odoo, EN1, etc.) |
| 3.5 | Módulo deshabilitado | `enabled=false` → products | HTTP 503 `ecalendar_disabled` |

---

## 4. Availability

| # | Prueba | Comando | Esperado |
|---|--------|---------|----------|
| 4.1 | Día laborable futuro | `GET .../availability?date=YYYY-MM-DD` (Lun–Vie, +5 días) | HTTP 200, `slots` array |
| 4.2 | Formato slot | cada slot | `start` / `end` ISO 8601 con offset |
| 4.3 | Zona horaria | JSON | `timezone: America/Panama` |
| 4.4 | Sábado | fecha sábado | `slots: []` |
| 4.5 | Fecha pasada | ayer | HTTP 400 `past_date` |
| 4.6 | Fecha inválida | `date=foo` | HTTP 400 `invalid_date` |
| 4.7 | Fuera de horizonte | > 30 días | HTTP 400 `date_out_of_range` |
| 4.8 | Google real | comparar con GCal UI | Slots libres coherentes con eventos existentes |
| 4.9 | Lead 4 h | slot dentro de 4 h | No debe aparecer en slots |

---

## 5. Bookings

| # | Prueba | Acción | Esperado |
|---|--------|--------|----------|
| 5.1 | Crear reserva | `POST .../bookings` JSON válido | HTTP 201 |
| 5.2 | Respuesta | JSON | `ok:true`, `booking_id`, `title`, `slot_start`, `slot_end` |
| 5.3 | Título GCal | revisar Google Calendar | `[Producto] Demo con Nombre` (+ prefijo si aplica) |
| 5.4 | Duplicar slot | mismo `slot_start` otra vez | HTTP 409 `slot_unavailable` |
| 5.5 | Producto inválido | `product_id: invalid` | HTTP 400 `invalid_product` |
| 5.6 | Email inválido | email mal formado | HTTP 400 `invalid_email` |
| 5.7 | Sin enabled | `enabled=false` | HTTP 503 |

**Payload de prueba:**

```json
{
  "product_id": "easy_odoo",
  "slot_start": "2026-06-20T10:00:00-05:00",
  "name": "QA Test ECalendar",
  "email": "qa-test@easytech.local",
  "phone": "+50760000000",
  "company": "Easy Technology QA",
  "notes": "Reserva automática checklist"
}
```

*(Ajustar `slot_start` a un slot libre devuelto por availability.)*

---

## 6. Google Calendar (verificación manual)

| # | Verificación | Dónde | Esperado |
|---|--------------|-------|----------|
| 6.1 | Evento creado | Google Calendar cuenta configurada | Evento visible en fecha/hora correcta |
| 6.2 | Duración | Evento | 30 minutos |
| 6.3 | Descripción / invitado | Detalle evento | Email y notas del payload (si implementado en V1) |
| 6.4 | Calendario correcto | Selector GCal | Calendario ID configurado (`primary` u otro) |
| 6.5 | Borrado QA | Eliminar evento de prueba | Limpieza post-QA |

---

## 7. CORS (Site_2026)

| # | Prueba | Acción | Esperado |
|---|--------|--------|----------|
| 7.1 | Origen permitido | Request desde dominio en `allowed_origins` | Header `Access-Control-Allow-Origin` presente |
| 7.2 | Origen no listado | Request desde otro dominio | Sin header CORS permisivo |
| 7.3 | OPTIONS | Preflight `OPTIONS /api/ecalendar/products` | HTTP 204 |

---

## 8. Seguridad y operación

| # | Verificación | Esperado |
|---|--------------|----------|
| 8.1 | Secretos fuera de repo | No hay refresh/client secret en git |
| 8.2 | API admin protegida | Sin cookie → 401 |
| 8.3 | Rollback conocido | `NODEONE_SKIP_ECALENDAR_BLUEPRINT=1` documentado |
| 8.4 | Logs | Sin secretos en `journalctl` / app log |

---

## 9. Criterio GO (appdev)

**GO** solo si:

- [ ] 1.2 – 1.4 health OK
- [ ] 2.4 o 2.5 OAuth OK
- [ ] 3.1 products OK
- [ ] 4.1 availability con slots reales
- [ ] 5.1 booking crea evento en GCal
- [ ] 5.4 duplicado → 409

**Estado APPDEV (jun 2026):** desarrollo 100 % · OAuth refresh token **pendiente** · checklist **no cerrado**.

---

## 10. Pre-promoción appprd

| # | Tarea |
|---|-------|
| 10.1 | Merge `develop` → `main` según política EN1 |
| 10.2 | `git pull` en silo prod (sin parches manuales) |
| 10.3 | Migración `ecalendar_settings` en BD prod |
| 10.4 | Configurar tenant prod en `/admin/ecalendar` (credenciales prod) |
| 10.5 | CORS con dominio producción Site_2026 |
| 10.6 | Repetir checklist §1–6 en `appprd.easynodeone.com` |
| 10.7 | Apagar Calendly cuando Site apunte a EN1 |

---

## Evidencia a archivar

Guardar en ticket / wiki:

1. Salida `curl` health (JSON completo)
2. Salida `products` (extracto)
3. Salida `availability` para un día
4. Salida `bookings` 201 + captura GCal
5. Salida `bookings` 409 en reintento
6. Captura pantalla admin OAuth OK
