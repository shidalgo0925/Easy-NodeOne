# Roadmap — EPosOne V4 (Arquitectura definitiva)

| Campo | Valor |
|-------|--------|
| Estado | **Aprobado** — 9 jul 2026 |
| Fase actual | **Hito EN1-01 ✅** (`847a09f`) · **siguiente: E2E APK ↔ provisioning** · sync fino después |
| Handoff | [`EN1_EPOSONE_HANDOFF_STATUS.md`](EN1_EPOSONE_HANDOFF_STATUS.md) |
| Master Plan | [`EN1_PLATFORM_MASTER_PLAN.md`](EN1_PLATFORM_MASTER_PLAN.md) |
| Dominio comercial | [`EN1_PLATFORM_ETAPA6_DOMINIO_COMERCIAL.md`](EN1_PLATFORM_ETAPA6_DOMINIO_COMERCIAL.md) |
| Contratos portables | [`EN1_PLATFORM_EPOSONE_V4_DOMAIN_CONTRACTS.md`](EN1_PLATFORM_EPOSONE_V4_DOMAIN_CONTRACTS.md) |
| Data providers | [`EN1_PLATFORM_EPOSONE_V4_PROVIDERS.md`](EN1_PLATFORM_EPOSONE_V4_PROVIDERS.md) · código `backend/nodeone/core/eposone_domain/` |
| Primer inicio | [`EN1_PLATFORM_EPOSONE_V4_FIRST_START.md`](EN1_PLATFORM_EPOSONE_V4_FIRST_START.md) |
| Vincular EN1 | [`EN1_PLATFORM_EPOSONE_V4_LINK_EN1.md`](EN1_PLATFORM_EPOSONE_V4_LINK_EN1.md) |
| Dispositivos POS | [`EN1_PLATFORM_EPOSONE_V4_DEVICES.md`](EN1_PLATFORM_EPOSONE_V4_DEVICES.md) |
| Sync Plataforma | [`EN1_PLATFORM_EPOSONE_V4_SYNC.md`](EN1_PLATFORM_EPOSONE_V4_SYNC.md) |
| POS + licenciamiento | [`EN1_PLATFORM_EPOSONE_V4_POS_LICENSING_ROADMAP.md`](EN1_PLATFORM_EPOSONE_V4_POS_LICENSING_ROADMAP.md) |
| Licenciamiento | [`ADR-005-EPOSONE-LICENSING-POS.md`](ADR-005-EPOSONE-LICENSING-POS.md) |
| **Etapa 2 Android** | [`EN1_PLATFORM_EPOSONE_V4_ANDROID_ETAPA2.md`](EN1_PLATFORM_EPOSONE_V4_ANDROID_ETAPA2.md) |
| **Hito EN1-01** | [`EPOSONE_EN1_HITO1_PROVISIONING_CONTRACT.md`](EPOSONE_EN1_HITO1_PROVISIONING_CONTRACT.md) |

---

## Objetivo

Convertir EPosOne en un **producto independiente** que opere:

1. de forma **autónoma** (Modo Local), y  
2. **integrado** con EasyNodeOne Platform (Modo Plataforma),

con **un único modelo de dominio** y **una sola aplicación Android**.

---

## ADRs (Sprint 1 — entregables)

| ADR | Archivo | Tema |
|-----|---------|------|
| ADR-001 | [`ADR-001-EPOSONE-STANDALONE.md`](ADR-001-EPOSONE-STANDALONE.md) | EPosOne como producto; una APK; EN1 no obligatorio |
| ADR-002 | [`ADR-002-EPOSONE-DOMAIN.md`](ADR-002-EPOSONE-DOMAIN.md) | Dominio único; SQLite/EN1 = proveedores |
| ADR-003 | [`ADR-003-EPOSONE-SYNC.md`](ADR-003-EPOSONE-SYNC.md) | Modo Local · Modo Plataforma · Vincular con EN1 |
| ADR-004 | [`ADR-004-EPOSONE-MIGRATION.md`](ADR-004-EPOSONE-MIGRATION.md) | Asistente Vincular con EasyNodeOne |
| ADR-005 | [`ADR-005-EPOSONE-LICENSING-POS.md`](ADR-005-EPOSONE-LICENSING-POS.md) | Licenciamiento por Punto de Venta; cupos en Core |

**Sprint 1:** ADRs + Master Plan / § 6.9. **Sin código.** ✅

**Sprint 2:** contratos portables — [`EN1_PLATFORM_EPOSONE_V4_DOMAIN_CONTRACTS.md`](EN1_PLATFORM_EPOSONE_V4_DOMAIN_CONTRACTS.md). **Sin providers / sin Android.** ✅ (doc; pendiente firma)

**Sprint 3:** providers — [`EN1_PLATFORM_EPOSONE_V4_PROVIDERS.md`](EN1_PLATFORM_EPOSONE_V4_PROVIDERS.md) · `eposone_domain/` (Memory / SQLite / API). **Sin sync rewrite / sin Android APK.** ✅

**Sprint 4:** primer inicio — [`EN1_PLATFORM_EPOSONE_V4_FIRST_START.md`](EN1_PLATFORM_EPOSONE_V4_FIRST_START.md) · `first_start.py`. **Sin APK / sin OAuth embebido / sin Vincular.** ✅

**Sprint 5:** vincular — [`EN1_PLATFORM_EPOSONE_V4_LINK_EN1.md`](EN1_PLATFORM_EPOSONE_V4_LINK_EN1.md) · `link_en1.py`. **Sin APK / sin sync rewrite.** ✅

**Sprint 6:** dispositivos — [`EN1_PLATFORM_EPOSONE_V4_DEVICES.md`](EN1_PLATFORM_EPOSONE_V4_DEVICES.md) · `devices.py` + `core_pos_terminal` V4. **Sin sync rewrite.** ✅

**Sprint 7:** sync Plataforma — [`EN1_PLATFORM_EPOSONE_V4_SYNC.md`](EN1_PLATFORM_EPOSONE_V4_SYNC.md) · `platform_sync.py` + rutas. **Motor intacto.** ✅

**ADR-005:** licenciamiento por POS — [`ADR-005-EPOSONE-LICENSING-POS.md`](ADR-005-EPOSONE-LICENSING-POS.md). **Solo doc; sin cupos activos.** ✅

---

## Sprints / entregables

| Sprint | Nombre | Estado | Resumen |
|--------|--------|--------|---------|
| **1** | ADR | ✅ | ADR-001…004 + modos en § 6.9 |
| **2** | Contrato de dominio | ✅ doc | Producto, Cliente, Pedido, Caja, Inventario, Empleado, Config — IDs opacos |
| **3** | Data providers | ✅ | `*Repository` + Memory / SQLite / API; dominio intacto |
| **4** | Primer inicio | ✅ | Wizard: Crear negocio \| Conectar EasyNodeOne (`first_start.py`) |
| **5** | Vincular con EN1 | ✅ | Asistente Local → Plataforma (`link_en1.py`) |
| **6** | Dispositivos POS | ✅ | UUID, perfil, app, empresa, sucursal, caja, flag sync |
| **7** | Sincronización | ✅ | Bridge política Plataforma sobre `core/sync/` |
| **—** | Licenciamiento POS | ✅ | ADR-005 + stub `LicensePolicy` (sin cupos) · commit `18f6593` |
| **EN1-01** | Provisioning APIs | ✅ código | `847a09f` — `/api/v1/devices/register` + `/config` · ⏳ E2E tablet |
| **Etapa 2** | Android (Producto) | 📋 | Sprints A–F — ver [`EN1_PLATFORM_EPOSONE_V4_ANDROID_ETAPA2.md`](EN1_PLATFORM_EPOSONE_V4_ANDROID_ETAPA2.md) · handoff [`EN1_EPOSONE_HANDOFF_STATUS.md`](EN1_EPOSONE_HANDOFF_STATUS.md) |

### Etapa 2 — Android (resumen)

Orden: **A** onboarding → **B** registro dispositivo → **C** config auto → **D** sync fino → **E** Este dispositivo → **F** Vincular EN1.  
Código APK: máquina local del equipo (no en `/opt/easynodeone/dev/app`). Sin planes/límites/FE/CRM/IA en esta etapa.

---

## Reglas congeladas

1. Existe **una sola APK**.
2. Existe **un solo modelo de dominio**.
3. El dominio **nunca** conoce SQLite ni EN1.
4. SQLite y EN1 son **únicamente proveedores de datos**.
5. EPosOne puede operar **completamente solo**.
6. EasyNodeOne **agrega capacidades**; nunca reemplaza EPosOne.
7. Vincular con EN1 **no cambia la aplicación**; solo el backend.
8. El usuario **nunca reinstala**, **nunca cambia de producto**, **nunca pierde información**.
9. El dominio **no** se limita por el plan comercial (ADR-005).
10. El **Punto de Venta** es la unidad de licenciamiento; los **dispositivos** no consumen licencia POS adicional.
11. EPosOne **no** contiene lógica de planes; los límites viven en **EN1 Core**.
12. Hoy los cupos están **ilimitados**; la arquitectura queda preparada vía hooks de política Core.
---

## Relación con trabajo Connected actual (appdev)

El shell UX, dashboard y analítica POS en EN1 web son trabajo de **Modo Plataforma**.  
No contradicen V4: Standalone/Local es otro modo de despliegue; al vincular, el cliente aterriza en el mismo producto.

El motor `nodeone/core/sync/` permanece; § 6.9 describe **Modo Plataforma**. Modo Local no usa ese motor hasta vincular.

---

## Protocolo

- **GO Sprint 1:** ADR — hecho.  
- **GO Sprint 2:** contratos portables — documento listo; **revisión humana** antes de Sprint 3.  
- **GO Sprint 3:** data providers — hecho en Dev (`eposone_domain/`).  
- **GO Sprint 4:** primer inicio — hecho (`first_start.py`; dominio; sin APK).  
- **GO Sprint 5:** vincular — hecho (`link_en1.py`; dominio; sin sync).  
- **GO Sprint 6:** dispositivos — hecho (`devices.py` + `core_pos_terminal` V4).  
- **GO Sprint 7:** sync — hecho (`platform_sync.py`; motor sin reescritura).  
- **GO ADR-005 + infra POS:** dominio POS/caja/dispositivo + `LicensePolicy` stub + admin provisionamiento — **cerrado** (`18f6593` en `develop`).  
- **GO EN1-01:** APIs provisioning dispositivos — **cerrado en código** (`847a09f`); E2E tablet = equipo EPosOne. Handoff: [`EN1_EPOSONE_HANDOFF_STATUS.md`](EN1_EPOSONE_HANDOFF_STATUS.md).  
- **Etapa 2 Android:** foco producto APK — [`EN1_PLATFORM_EPOSONE_V4_ANDROID_ETAPA2.md`](EN1_PLATFORM_EPOSONE_V4_ANDROID_ETAPA2.md).  
- Sin GO: no push a staging/prod, no sync forzado a flotas, no activar límites.
