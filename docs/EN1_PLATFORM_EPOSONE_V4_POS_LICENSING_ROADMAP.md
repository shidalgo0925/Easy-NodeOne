# EPosOne V4 — Gestión de Puntos de Venta y Licenciamiento

| Campo | Valor |
|-------|--------|
| Estado | **Infraestructura lista** — 9 jul 2026 (Dev EN1); cupos comerciales **no** activos |
| ADR | [ADR-005](ADR-005-EPOSONE-LICENSING-POS.md) |
| Roadmap V4 | [`EN1_PLATFORM_EPOSONE_V4_ROADMAP.md`](EN1_PLATFORM_EPOSONE_V4_ROADMAP.md) |
| Objetivo | Separar **Dominio** · **Infraestructura** · **Licenciamiento**; cupos **ilimitados** ahora |

---

## Tres capas (no mezclar)

| Capa | Contenido |
|------|-----------|
| Dominio | Empresa → Sucursal → **POS** (`org_unit.type=pos`) → Caja (`register`) → Dispositivos (`core_pos_terminal.pos_ref`) |
| Infraestructura | Sync `client_id=pos:{unit_ref}` cuando hay POS; fallback device UUID |
| Licenciamiento | `nodeone.core.license` — `LicensePolicy` siempre permite |

---

## Fases

| Fase | Entregable | Estado |
|------|------------|--------|
| 1 | Modelo dominio POS / Caja / Dispositivo | ✅ |
| 2 | Provisionamiento EN1 (`/section/pos-points`) | ✅ |
| 3 | Registro dispositivo → POS + Caja (`pos_ref`) | ✅ |
| 4 | Sync Engine por POS (`client_id` / payload tag) | ✅ |
| 5 | Modelo `LicenseLimits` (NULL/-1 = ilimitado) | ✅ stub |
| 6 | Contrato `LicensePolicy` (siempre `true`) | ✅ |
| 7 | Integración EN1 real (denegar por plan) | ⏳ futuro |
| 8 | Planes comerciales | ⏳ solo doc |

---

## Jerarquía

```text
Tenant
  └── Empresa
        └── Sucursal (branch)
              └── Punto de Venta (pos)     ← unidad de licencia
                    └── Caja (register)
                          └── Dispositivos (N)  ← no consumen licencia
```

---

## Reglas congeladas (complemento ADR-005)

1. Un único dominio.  
2. Los planes nunca modifican el dominio.  
3. Restricciones solo en `LicensePolicy`.  
4. Dispositivos ≠ licencias; el **POS** es la unidad comercial.  
5. N dispositivos pueden trabajar sobre el mismo POS.  
6. Reemplazar un dispositivo no afecta la licencia.  
7. Cambiar de plan no exige reinstalar la app.

---

## Sprints de implementación

| Sprint | Entregable | Estado |
|--------|------------|--------|
| 1 | ADR-005 | ✅ |
| 2–4 | Entidades POS / Caja / Dispositivo (+ vínculo) | 🔧 este GO |
| 5 | Registro dispositivo (API + flujo) | 🔧 |
| 6 | Sync por POS | 🔧 |
| 7 | Módulo provisionamiento EN1 | 🔧 |
| 8 | `LicensePolicy` sin restricciones | 🔧 |
| 9 | Activar cupos por plan | ⏳ |

---

## Código

| Pieza | Ubicación |
|-------|-----------|
| Tipo `pos` | `ORG_UNIT_TYPE_POS` en `master/constants.py` |
| Política | `nodeone/core/license/policy.py` |
| Dispositivo → POS | `core_pos_terminal.pos_ref` |
| Admin | `/admin/eposone/section/pos-points` |
| Sync | `PlatformSyncBridge` + header `X-EPosOne-Pos-Id` |
