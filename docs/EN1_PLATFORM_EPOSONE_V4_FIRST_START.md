# EPosOne V4 — Primer inicio (Sprint 4)

| Campo | Valor |
|-------|--------|
| Sprint | **4 — Primer inicio** |
| Estado | **Histórico / supersedido para onboarding de producto** · ver **[ADR-027](ADR-027-EPOSONE-ONBOARDING-UNIFICADO-V1.md)** + [`eposone-onboarding/`](eposone-onboarding/README.md) (6 ago 2026) · UI “Crear negocio sin EN1” **no oficial** |
| Roadmap | [`EN1_PLATFORM_EPOSONE_V4_ROADMAP.md`](EN1_PLATFORM_EPOSONE_V4_ROADMAP.md) |
| Etapa 2 Android | [`EN1_PLATFORM_EPOSONE_V4_ANDROID_ETAPA2.md`](EN1_PLATFORM_EPOSONE_V4_ANDROID_ETAPA2.md) |
| ADR | [ADR-003](ADR-003-EPOSONE-SYNC.md) |
| Providers | [`EN1_PLATFORM_EPOSONE_V4_PROVIDERS.md`](EN1_PLATFORM_EPOSONE_V4_PROVIDERS.md) |
| Código dominio | `backend/nodeone/core/eposone_domain/first_start.py` |
| Código APK | Proyecto local `…\EPosOne\eposone` (no en este repo servidor) |

---

## 1. Objetivo

Congelar el **wizard de primer arranque** con dos caminos (una sola APK / un solo producto):

```text
Primer inicio
  ├─ Crear un nuevo negocio     → Modo Local
  └─ Conectar con EasyNodeOne   → Modo Plataforma
```

**No** es el asistente «Vincular con EasyNodeOne» (Local → Plataforma): eso es Sprint 5 / ADR-004.

---

## 2. Copy (congelado)

| Path | Label UI | Resultado |
|------|----------|-----------|
| `create_business` | Crear un nuevo negocio | `operating_mode=local` |
| `connect_en1` | Conectar con EasyNodeOne | `operating_mode=platform` |

Prohibido en UI: «migración», «migrar», «standalone» (docs técnicos sí pueden).

---

## 3. Flujos

### Crear negocio (Local)

1. Nombre negocio + moneda (ISO 4217)  
2. Sucursal principal + caja  
3. Admin local (manager/cashier, PIN opcional)  
4. Persistencia vía `ConfigRepository` + `EmployeeRepository`  
5. Estado bootstrap `completed=true`

### Conectar EN1 (Plataforma)

1. Login EN1 ocurre **fuera** de este módulo (cliente entrega `access_granted`)  
2. `organization_id` + selección sucursal/caja (ids o nombres)  
3. Bootstrap de `BusinessConfig` / branch / register  
4. `operating_mode=platform`, `has_en1_credentials=true`  
5. Sync offline (§ 6.9) se cablea en Sprint 7 — aquí solo modo + config

---

## 4. API Python

```python
from nodeone.core.eposone_domain.first_start import (
    CreateBusinessInput,
    ConnectEn1Input,
    wizard_from_memory_bundle,
    wizard_from_sqlite_bundle,
)
from nodeone.core.eposone_domain.memory import MemoryProviderBundle

wiz = wizard_from_memory_bundle(MemoryProviderBundle())
assert wiz.needs_first_start()
wiz.choices()  # dos opciones
result = wiz.create_local_business(CreateBusinessInput(business_name='Mi Café'))
# result.state.operating_mode == 'local'
```

SQLite: `wizard_from_sqlite_bundle` guarda estado en tabla `app_bootstrap`.

---

## 5. Criterio de hecho

- [x] Dos caminos + labels ADR-003  
- [x] Crear negocio → Local (empresa, sucursal, caja, admin)  
- [x] Conectar EN1 → Plataforma (sin OAuth embebido; flag `access_granted`)  
- [x] Estado bootstrap persistible (Memory / SQLite)  
- [x] Tests unitarios  
- [x] Sin APK, sin cambios a `core/sync/` (Vincular = Sprint 5)

---

## 6. Fuera de alcance

- UI Android / Compose screens  
- OAuth / tokens EN1  
- Asistente Vincular — [`EN1_PLATFORM_EPOSONE_V4_LINK_EN1.md`](EN1_PLATFORM_EPOSONE_V4_LINK_EN1.md) (Sprint 5)  
- Dispositivos POS (Sprint 6)  
- Cablear sync (Sprint 7)
