# EPosOne ↔ EN1 — Dónde quedamos (handoff)

| Campo | Valor |
|-------|--------|
| Fecha | **14 jul 2026** |
| Rama | `develop` · Hito 2 API **`b254735`** · Hito 1 tag **`eposone-provisioning-v1.0`** |
| Silo | Solo **Dev EN1** — `https://appdev.easynodeone.com` |
| Modo | **Estricto Dev** — sin staging/prod/relatic |
| **ADR-006** | [`ADR-006-EPOSONE-OPERATION-VS-ADMIN.md`](ADR-006-EPOSONE-OPERATION-VS-ADMIN.md) — Op vs Admin **aprobado** |
| **Hito 3 spec** | [`EN1_EPOSONE_HITO3_SPEC_FUNCIONAL_V1.md`](EN1_EPOSONE_HITO3_SPEC_FUNCIONAL_V1.md) — **En diseño** · desarrollo **congelado** |
| **Hito 3 brief** | [`EN1_EPOSONE_HITO3_ORDER_LIFECYCLE.md`](EN1_EPOSONE_HITO3_ORDER_LIFECYCLE.md) |
| **Hito 1** | **CERRADO / CONGELADO** |
| **Hito 2** | EN1 API ✅ · E2E APK 🟡 (`/api/v1/devices/bootstrap`) |
| **Siguiente código** | P2 puede cerrar Bootstrap E2E · Hito 3 **no** hasta sesión §13 + spec congelada + GO |

---

## Una frase

**Hito 1/2 (EN1):** provisionar + bootstrap API listos.  
**Arquitectura:** EPosOne opera; EN1 administra (ADR-006).  
**Hito 3:** Spec funcional V1.0 **en diseño** — desarrollo congelado; falta sesión de preguntas A–E.

---

## Diagnóstico Hito 2 (14 jul) — para P2

| Hallazgo | Detalle |
|----------|---------|
| Device Token | Autoriza `/api/v1/devices/config` y **`/api/v1/devices/bootstrap`** |
| `GET /api/eposone/products` | Solo sesión usuario BO (`@login_required`) → **401** con Bearer dispositivo |
| Mensaje APK “Reprovisiona…” | Genérico ante 401; **no** implica token inválido para Hito 2 |
| Fix | APK debe llamar **bootstrap**, no products BO |

No cambiar contrato Hito 2. No abrir device auth en API BO sin GO.

---

## Hito 1 — cierre

| Chequeo | Estado |
|---------|--------|
| URL `https://appdev.easynodeone.com` | ✅ |
| Código Caja Itsmo (`caja-01`) | ✅ |
| `POST /api/v1/devices/register` | ✅ |
| Token Bearer | ✅ |

Contrato: [`EPOSONE_EN1_HITO1_PROVISIONING_CONTRACT.md`](EPOSONE_EN1_HITO1_PROVISIONING_CONTRACT.md)

---

## Hito 2 — Bootstrap

| Pieza | Estado |
|-------|--------|
| Contrato | ✅ [`EN1_EPOSONE_HITO2_DEVICE_BOOTSTRAP_SYNC_DOWN.md`](EN1_EPOSONE_HITO2_DEVICE_BOOTSTRAP_SYNC_DOWN.md) |
| EN1 `GET /api/v1/devices/bootstrap` | ✅ `b254735` |
| APK E2E | 🟡 corregir endpoint + revalidar |

---

## Arquitectura aprobada (resumen)

| | EPosOne | EN1 |
|--|---------|-----|
| Rol | Operación | Administración (fuente oficial) |
| Inventario | Consulta + eventos | Kardex / stock / auditoría |
| Micro negocio | Admin **básica** en tablet | Sigue siendo truth al sync |
| Corporativo | Solo vender | Todo el admin |

Tres modos org: **Solo POS** · **POS + BackOffice** · **Corporativo**.  
Una APK; capacidades por modo + nivel usuario — detalle en ADR-006.

---

## Roadmap

```text
Provisioning ✅
    ↓
Bootstrap 🟡 (E2E APK)
    ↓
Hito 3 — Operación del Pedido ⏸ (contrato + GO)
    ↓
Inventario por eventos / caja / FE ⏸
```

---

## Instrucciones cortas P1 / P2

Ver documento completo: [`EN1_EPOSONE_HITO3_ORDER_LIFECYCLE.md`](EN1_EPOSONE_HITO3_ORDER_LIFECYCLE.md)

| Quién | Ahora | No hacer |
|-------|--------|----------|
| **P1 EN1** | Leer ADR-006; diseñar mentalmente Order\* — **sin código** Hito 3 | Inventario operativo, FE, reabrir H1/H2 |
| **P2 EPosOne** | Cerrar Hito 2 con `bootstrap`; luego Pedido offline-first (tras GO) | `/api/eposone/products` para sync; ventas→stock prematuro |

---

## Fuera de alcance (hasta GO)

- Implementación Hito 3  
- Inventario operativo / transferencias / compras  
- FE / CRM / IA  
- Despliegue fuera de Dev  

---

## Repos

| Pieza | Dónde |
|-------|--------|
| EN1 | `/opt/easynodeone/dev/app` · `develop` |
| APK | PC equipo (Flutter) |

---

## Chat nuevo

1. P2 — fix Bootstrap E2E  
2. Ambos — contrato Hito 3  
3. GO implementación Hito 3 (chats separados EN1 / APK)
