# ECalendar V1 — Entrega ejecutiva

**Proyecto:** Agenda pública EasyTech (reemplazo Calendly)  
**Plataforma:** Easy NodeOne (EN1)  
**Fecha:** junio 2026  
**Entornos:** appdev (activo) · appprd (pendiente)

---

## 1. Qué se hizo

### Desarrollo (100 %)

| Entregable | Estado |
|------------|--------|
| Módulo `nodeone/modules/ecalendar/` | ✓ Implementado |
| API pública `/api/ecalendar/*` | ✓ health, products, availability, bookings |
| API admin `/api/admin/ecalendar/*` | ✓ config + test OAuth |
| Pantalla `/admin/ecalendar` | ✓ UI configuración por tenant |
| Modelo `ecalendar_settings` | ✓ PostgreSQL |
| Migración `migrate_ecalendar_settings.py` | ✓ Con guard PostgreSQL |
| 11 productos EasyTech | ✓ Catálogo default |
| CORS para Site_2026 | ✓ Orígenes configurables |
| Tests unitarios availability | ✓ `tests/ecalendar/` |
| Documentación programador | ✓ `INSTRUCCION_ECALENDAR_EN1_APPDEV.md` |
| Guía admin + QA | ✓ `ECALENDAR_ADMIN_GUIDE.md`, `ECALENDAR_QA_CHECKLIST.md` |

### Git y despliegue appdev

| Hito | Detalle |
|------|---------|
| Commit V1 | `70bc61e` — Add ECalendar V1 Google Calendar integration |
| Commit migración | `e347d9c` — fix(ecalendar): use service env and prevent sqlite migration issues |
| Rama | `develop` publicada en `origin/develop` |
| Servicio | `easynodeone-dev.service` activo, puerto 9101 |
| Health módulo | HTTP 200 — módulo cargado |

### Configuración parcial (appdev)

| Ítem | Estado |
|------|--------|
| Fila `ecalendar_settings` org 1 | ✓ Existe |
| Google Client ID (cliente Calendar dedicado) | ✓ En BD |
| Google Client Secret | ✓ En BD |
| Cuenta referencia | `easytechservices25@gmail.com` |
| Google Refresh Token | ✗ **Pendiente** |
| ECalendar activado (`enabled`) | ✗ OFF hasta OAuth |

---

## 2. Qué falta

| # | Tarea | Responsable | Bloquea |
|---|-------|-------------|---------|
| 1 | Obtener **refresh token** OAuth (scope Calendar) | Ops / admin Google | Todo lo operativo |
| 2 | Activar ECalendar en `/admin/ecalendar` | Admin EN1 | API pública 503 |
| 3 | Probar OAuth (botón admin) | Admin EN1 | `oauth_valid` |
| 4 | Cerrar **QA checklist** appdev | QA | GO appdev |
| 5 | Integrar `agenda.html` Site_2026 → appdev | Web EasyTech | Prueba end-to-end |
| 6 | Promover a **appprd** (git pull + config prod) | DevOps | Producción |
| 7 | Apagar Calendly | Negocio | Cierre migración |

### Seed automático (mejora propuesta, no implementada)

Evitar estado «tabla sin filas» tras migración en silos nuevos. Propuesta técnica en `ECALENDAR_ADMIN_GUIDE.md` §8.

---

## 3. Riesgos

| Riesgo | Impacto | Mitigación |
|--------|---------|------------|
| Refresh token no obtenido | Módulo inoperativo | Seguir guía OAuth §2; usuario de prueba en consent screen |
| Secret OAuth expuesto en chat | Compromiso credenciales | Rotar client secret en Google Cloud; actualizar BD |
| Confundir OAuth login vs Calendar | Tokens incorrectos | Cliente OAuth **dedicado** ECalendar; credenciales solo en BD |
| `enabled=true` sin OAuth válido | 502/503 en availability | Activar solo tras test OAuth OK |
| CORS mal configurado | Site_2026 no puede llamar API | Listar dominios prod en `allowed_origins` antes de go-live |
| Deploy prod sin migración | Tabla inexistente | Ejecutar `migrate_ecalendar_settings.py` en silo prod |
| Parches manuales en prod/relatic | Violación política Git | Solo `git pull` desde remoto |

---

## 4. Criterio GO

### GO appdev (operativo)

Todos deben cumplirse:

| Criterio | Estado actual |
|----------|---------------|
| Código en `origin/develop` | ✓ |
| Servicio appdev activo | ✓ |
| `health`: `enabled`, `google_connected`, `oauth_valid` = true | ✗ |
| `products` HTTP 200 | ✗ (503 — disabled) |
| `availability` con slots reales | ✗ |
| `bookings` crea evento en Google Calendar | ✗ |
| QA checklist §9 cerrado | ✗ |

**Veredicto appdev:** **NO GO** — bloqueado por refresh token OAuth.

### GO producción

Adicionalmente:

- Checklist repetido en appprd
- Site_2026 apuntando a `appprd.easynodeone.com/api/ecalendar`
- Calendly desactivado

**Veredicto prod:** **Pendiente**

---

## 5. Próximo paso único

1. Completar OAuth refresh token (ver `ECALENDAR_ADMIN_GUIDE.md` §2).
2. Ejecutar `ECALENDAR_QA_CHECKLIST.md`.
3. Declarar GO appdev.
4. Planificar ventana appprd.

---

## 6. Roadmap — V2 pospuesta

**ECalendar V2** (confirmación por email + lead CRM + evento GCal solo al confirmar) queda **fuera del alcance del cierre V1**.

Planificación y fases: **`docs/ECALENDAR_ROADMAP.md`**

Implementar V2 solo tras **GO explícito** y con V1 operativo en producción.

---

## 7. Referencias rápidas

| Recurso | Ruta |
|---------|------|
| **Roadmap V1 / V2** | `docs/ECALENDAR_ROADMAP.md` |
| Guía admin | `docs/ECALENDAR_ADMIN_GUIDE.md` |
| QA | `docs/ECALENDAR_QA_CHECKLIST.md` |
| Instrucción implementación | `docs/INSTRUCCION_ECALENDAR_EN1_APPDEV.md` |
| Admin UI | `https://appdev.easynodeone.com/admin/ecalendar` |
| Health | `https://appdev.easynodeone.com/api/ecalendar/health` |
| EasyWiki producto | `EasyWiki/03_Productos/ecalendar.md` |
