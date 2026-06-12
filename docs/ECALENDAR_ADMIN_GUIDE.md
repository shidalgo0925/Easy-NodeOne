# ECalendar — Guía de administración EN1

Guía técnica y operativa del módulo **ECalendar V1** (agenda pública EasyTech → Google Calendar).

**Audiencia:** administradores EN1, DevOps, programadores.  
**Relacionado:** `INSTRUCCION_ECALENDAR_EN1_APPDEV.md` (implementación inicial), `ECALENDAR_QA_CHECKLIST.md` (pruebas).

---

## 1. Arquitectura

### 1.1 Contexto

| Componente | Rol |
|------------|-----|
| **Site_2026** (sitio estático EasyTech) | Formulario `/agenda`; consume API JSON; **sin** OAuth en HTML |
| **EN1** (`appdev` / `appprd`) | API `/api/ecalendar/*`, OAuth servidor, creación de eventos en Google Calendar |
| **Google Calendar** | Calendario único V1 (ej. `primary` o «EasyTech Citas») |

### 1.2 Diagrama de flujo

```text
Site_2026 (agenda.html)
        │  GET products / availability
        │  POST bookings
        ▼
EN1  /api/ecalendar/*
        │  OAuth refresh token (servidor)
        ▼
Google Calendar API v3
```

### 1.3 Estructura de código (EN1)

```text
backend/
  models/ecalendar.py                    # Tabla ecalendar_settings
  migrate_ecalendar_settings.py          # Crear tabla (PostgreSQL APPDEV)
  nodeone/modules/ecalendar/
    routes.py                            # API pública
    admin_routes.py                      # Pantalla + API admin
    products.py                          # 11 productos por defecto
    services/
      config.py                          # DTO ECalendarConfig
      settings_store.py                  # Carga desde BD
      google_calendar.py                 # OAuth + Calendar API
      availability.py                    # Slots Lun–Vie
      bookings.py                        # Reservas + 409
  nodeone/core/features.py               # register_ecalendar_blueprint
templates/admin/ecalendar_settings.html  # UI configuración
```

### 1.4 Registro del módulo

- Blueprint público: `register_ecalendar_blueprint(app)` → prefijo `/api/ecalendar`
- Rutas admin: `register_ecalendar_admin_routes(app)` → `/admin/ecalendar`, `/api/admin/ecalendar/*`
- Desactivar módulo: `NODEONE_SKIP_ECALENDAR_BLUEPRINT=1`

### 1.5 Persistencia

Toda la configuración vive en **`ecalendar_settings`** (una fila por `organization_id`).  
**No** usar variables de entorno para credenciales Google ni horarios en V1.

---

## 2. Flujo OAuth

### 2.1 Modelo V1

- **Tipo:** OAuth 2.0 servidor con **refresh token** de larga duración.
- **Scope:** `https://www.googleapis.com/auth/calendar`
- **Intercambio:** `POST https://oauth2.googleapis.com/token` con `grant_type=refresh_token`
- **Uso:** cada llamada a Calendar API obtiene `access_token` fresco vía refresh.

### 2.2 Obtener refresh token (una vez por entorno)

1. En **Google Cloud Console** → cliente OAuth Web:
   - Redirect URI: `http://localhost:8765/oauth2callback`
   - Habilitar **Google Calendar API**
   - Usuario de prueba: cuenta del calendario (ej. `easytechservices25@gmail.com`) si la app está en modo Testing
2. Abrir URL de autorización (Client ID del tenant):

```text
https://accounts.google.com/o/oauth2/v2/auth
  ?client_id=<CLIENT_ID>
  &redirect_uri=http%3A%2F%2Flocalhost%3A8765%2Foauth2callback
  &response_type=code
  &scope=https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fcalendar
  &access_type=offline
  &prompt=consent
```

3. Tras aceptar permisos, copiar `code` de la URL de redirect.
4. Intercambiar `code` → `refresh_token` (script o pantalla admin).
5. Guardar refresh token en BD (`ecalendar_settings.google_refresh_token`).

### 2.3 Prueba OAuth desde EN1

- **UI:** `/admin/ecalendar` → botón **Probar OAuth**
- **API:** `POST /api/admin/ecalendar/test` (sesión admin)
- **Éxito:** `{ "success": true, "message": "Conexión OAuth OK." }`

### 2.4 Separación del login social

`GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` en `.env` del silo son para **login web** (`/auth/google`).  
ECalendar usa credenciales **propias** guardadas en `ecalendar_settings` (cliente OAuth dedicado a Calendar).

---

## 3. Configuración Google Calendar

### 3.1 Pantalla admin

**URL:** `https://<host>/admin/ecalendar`  
**Menú:** Configuración → Agenda ECalendar

| Campo | Descripción |
|-------|-------------|
| Activar ECalendar | Si OFF → API pública responde `503 ecalendar_disabled` |
| Usar para agenda pública | Tenant que alimenta Site_2026 (solo uno con flag ON) |
| Cuenta Google (referencia) | Email documental; no valida OAuth |
| Client ID / secret / refresh token | Credenciales servidor |
| ID calendario | `primary` o ID del calendario «EasyTech Citas» |
| Zona / horario / lead / horizonte | Reglas de slots |
| Prefijo título | Ej. `[TEST]` en appdev |
| Orígenes CORS | URLs del sitio estático (una por línea) |
| Productos JSON | Opcional; si vacío → 11 productos por defecto |

### 3.2 API admin

| Método | Ruta | Auth |
|--------|------|------|
| GET | `/api/admin/ecalendar/config` | Admin |
| POST/PUT | `/api/admin/ecalendar/config` | Admin |
| POST | `/api/admin/ecalendar/test` | Admin |

Al guardar con `use_for_public_agenda=true`, se apaga ese flag en **otros** tenants.

### 3.3 Migración de tabla

En APPDEV (PostgreSQL del silo):

```bash
sudo -u nodeone bash -lc 'set -a && source /opt/easynodeone/dev/.env && set +a && \
  cd /opt/easynodeone/dev/app/backend && \
  /opt/easynodeone/dev/venv/bin/python3 migrate_ecalendar_settings.py'
```

El script valida que no apunte a SQLite y confirma existencia de tabla.

---

## 4. Configuración por tenant

### 4.1 Resolución de tenant

| Contexto | Org usada |
|----------|-----------|
| API pública `/api/ecalendar/*` | `ECalendarSettings.get_public_settings()` |
| Admin `/admin/ecalendar` | `get_admin_effective_organization_id()` (org efectiva del admin) |

**Prioridad agenda pública:** primer registro con `enabled=true`, `use_for_public_agenda=true`, `is_active=true`; si ninguno, primer `enabled=true`.

### 4.2 APPDEV (jun 2026)

| Org ID | Nombre | Rol ECalendar |
|--------|--------|---------------|
| 1 | Easy NodeOne - Dev | Tenant admin por defecto; fila `ecalendar_settings` |

### 4.3 Reglas de negocio V1

| Regla | Valor default |
|-------|---------------|
| Duración slot | 30 min |
| Lead mínimo | 4 h |
| Horizonte | 30 días |
| Días laborables | Lun–Vie |
| Horario | 09:00–17:00 |
| Zona | `America/Panama` |
| Slot ocupado | HTTP 409 `slot_unavailable` |
| Título evento | `[Producto] Demo con Nombre` (+ prefijo opcional) |

---

## 5. Health checks

### 5.1 Endpoint

```bash
curl -s https://appdev.easynodeone.com/api/ecalendar/health
```

### 5.2 Campos

| Campo | Significado |
|-------|-------------|
| `ok` | Módulo cargado |
| `enabled` | Flag `enabled` del tenant público |
| `google_connected` | Client ID + secret + refresh + calendar_id presentes |
| `oauth_valid` | Refresh token produce access token válido |
| `calendar_id` | ID calendario configurado |
| `products` | Cantidad de productos (default 11) |

### 5.3 Estados esperados

| Fase | `enabled` | `google_connected` | `oauth_valid` |
|------|-----------|-------------------|---------------|
| Código desplegado, sin config | `false` | `false` | `false` |
| Credenciales en BD, sin refresh | `false`* | `false` | `false` |
| Operativo | `true` | `true` | `true` |

\*Recomendado mantener `enabled=false` hasta OAuth válido.

### 5.4 Servicio EN1

```bash
sudo systemctl status easynodeone-dev.service --no-pager
curl -s -o /dev/null -w "%{http_code}\n" https://appdev.easynodeone.com/api/ecalendar/health
```

---

## 6. Endpoints disponibles

### 6.1 API pública (`/api/ecalendar`)

| Método | Ruta | Auth | Descripción |
|--------|------|------|-------------|
| GET | `/health` | No | Estado módulo |
| GET | `/products` | No | Catálogo productos (requiere `enabled`) |
| GET | `/availability?date=YYYY-MM-DD` | No | Slots libres (requiere Google) |
| POST | `/bookings` | No | Crear cita en GCal |
| OPTIONS | `/*` | No | CORS preflight |

### 6.2 Códigos de error frecuentes (pública)

| HTTP | `error` | Causa |
|------|---------|-------|
| 503 | `ecalendar_disabled` | `enabled=false` |
| 503 | `google_not_configured` | Falta refresh u otro campo OAuth |
| 502 | `google_api_error` | Fallo Calendar API |
| 400 | `invalid_date`, `past_date`, `date_out_of_range` | Parámetro `date` |
| 409 | `slot_unavailable` | Slot ya ocupado |
| 400 | `invalid_product`, `invalid_email`, … | Payload booking |

### 6.3 API admin

| Método | Ruta | HTTP sin sesión |
|--------|------|-----------------|
| GET/POST/PUT | `/api/admin/ecalendar/config` | 401 |
| POST | `/api/admin/ecalendar/test` | 401 |

---

## 7. Solución de problemas

| Síntoma | Causa probable | Acción |
|---------|------------------|--------|
| `enabled=false` en health | No activado en admin o sin refresh token | Completar OAuth; activar en `/admin/ecalendar` |
| `google_connected=false` | Falta client secret o refresh token | Guardar credenciales completas en BD |
| `oauth_valid=false` | Refresh inválido / scope / usuario no autorizado | Regenerar refresh; verificar scope Calendar |
| `503` en products | `enabled=false` | Activar ECalendar |
| `503 google_not_configured` en availability | OAuth incompleto | Completar Paso OAuth |
| `502 google_api_error` | API deshabilitada, cuota, calendario inexistente | Google Cloud Console; verificar `google_calendar_id` |
| `401` en admin API | Sin sesión admin | Login en EN1 |
| Tabla vacía tras migración | Solo se crea tabla, no filas | Ver **Propuesta seed** (§8); abrir `/admin/ecalendar` (hace `get_or_create`) |
| Migración apunta a SQLite | `.env` incorrecto al ejecutar script | Usar `sudo -u nodeone` + `/opt/easynodeone/dev/.env` |

### Rollback

- Variable: `NODEONE_SKIP_ECALENDAR_BLUEPRINT=1` + reinicio servicio
- O revertir deploy a commit anterior en el silo

---

## 8. Propuesta técnica: seed automático (no implementado)

### 8.1 Problema

Tras `migrate_ecalendar_settings.py` la tabla existe pero puede quedar con **0 filas**. La API pública usa `get_public_settings()` → `empty_config()` → comportamiento «desinstalado» aunque el código esté desplegado.

La pantalla admin ya llama `get_or_create_for_organization(admin_org_id)` al **primer acceso**, pero eso no garantiza fila para org 1 sin visitar admin.

### 8.2 Objetivo propuesto

Garantizar al menos **una fila base** para `organization_id=1` (APPDEV) con defaults seguros y `enabled=false` hasta OAuth completo.

### 8.3 Opciones evaluadas

| Opción | Dónde | Pros | Contras |
|--------|-------|------|---------|
| **A. Extender migración** | `migrate_ecalendar_settings.py` | Explícito en deploy | Acopla org 1; repetir lógica en cada silo |
| **B. Bootstrap al arranque** | `ensure_ecalendar_settings_table()` + seed | Siempre consistente | Arranque toca BD; definir qué org(s) |
| **C. Lazy en `load_ecalendar_config`** | `settings_store.py` | Sin migración extra | Side-effect en cada request si mal diseñado |
| **D. Señal por env** | `ECALENDAR_SEED_ORG_IDS=1` en silo | Flexible por entorno | Otra variable operativa |

### 8.4 Recomendación (para implementación futura)

**Opción B + D combinadas:**

1. En `settings_store.ensure_ecalendar_settings_table()` (ya invocado por admin y rutas):
   - Tras `CREATE TABLE`, leer `ECALENDAR_SEED_ORG_IDS` (default `1` solo en appdev; vacío en prod hasta acordar).
   - Para cada org ID: `get_or_create_for_organization(oid)` + `commit` si fila nueva.
2. Defaults de fila nueva:
   - `enabled=false`
   - `use_for_public_agenda=(oid==1)` solo en dev
   - `google_calendar_id='primary'`
   - `google_account_email=''` (rellenar en admin)
   - Sin copiar secretos desde `.env` automáticamente (evita mezclar login OAuth con Calendar).
3. Log una línea: `ecalendar_settings: seeded org 1 (enabled=false)`.

### 8.5 Criterios de aceptación (cuando se implemente)

- Tras deploy + migración, `SELECT COUNT(*) FROM ecalendar_settings WHERE organization_id=1` ≥ 1
- `health` sigue `enabled=false` hasta configuración manual
- No escribe secretos en repo ni en logs
- Idempotente (re-ejecutar no duplica: `organization_id` es UNIQUE)

### 8.6 Fuera de alcance V1

- Seed multi-tenant automático para todos los `saas_organization`
- Provisión automática de refresh token (siempre manual o script operativo one-shot)

---

## 9. Referencias

| Documento | Uso |
|-----------|-----|
| `INSTRUCCION_ECALENDAR_EN1_APPDEV.md` | Contrato API y payloads |
| `ECALENDAR_QA_CHECKLIST.md` | Pruebas antes de prod |
| `ECALENDAR_ENTREGA_EJECUTIVA.md` | Estado proyecto y GO |
| Commits | `70bc61e` (V1), `e347d9c` (migración PostgreSQL) |
