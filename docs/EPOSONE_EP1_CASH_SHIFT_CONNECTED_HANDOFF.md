# Handoff EP1 — Turnos/cierres → EN1 (solo Connected)

| Campo | Valor |
|-------|--------|
| Audiencia | Prog2 / Local (APK EPosOne) |
| Modalidad | **Connected únicamente** |
| Standalone | **N/A** — cierres solo locales; no pushear turnos a EN1 |
| Contrato | [`EN1_EPOSONE_CASH_SHIFT_HTTP_CONTRACT.md`](EN1_EPOSONE_CASH_SHIFT_HTTP_CONTRACT.md) v1.0 |
| Spec | [`EN1_EPOSONE_CASH_SHIFT_SPEC_V1.md`](EN1_EPOSONE_CASH_SHIFT_SPEC_V1.md) §0 |
| Prioridad | P2 |

---

## Mensaje operativo

En instalaciones **Connected** (POS enlazado a EN1), la APK debe **enviar** apertura y cierre de caja a EN1, para que Turnos / OCC tengan los **mismos cierres** que el POS.

1. **Abrir** → `POST /api/v1/cash/shifts` (Device Bearer, `client_shift_id`, `cashier_contact_id`)
2. **Cerrar** → `POST /api/v1/cash/shifts/{shift_id}/close` (`counted_amount`, `cashier_contact_id`)
3. **Sin red** → encolar y pushear al recuperar (idempotente; no duplicar turno)

El cierre en BO EN1 es **solo emergencia**. El cierre que cuenta es el del **cajero en EP1**, y ese debe llegar a EN1.

**Standalone:** no aplica este handoff. No llamar `/api/v1/cash/shifts*`.

---

## Por qué

Hoy el cajero cierra en la tablet y EN1 no se entera → turnos abiertos/mezclados y reportes que no cuadran. EN1 ya tiene el HTTP congelado; falta el **cableado APK en Connected**.

---

## Criterio de hecho (Connected)

- [ ] Abrir en EP1 → turno `open` en EN1
- [ ] Cerrar en EP1 → turno `closed` en EN1 (cajero + contado)
- [ ] Visible en OCC → Cierres / Turnos
- [ ] Offline: un solo cierre al sync (`client_shift_id`)

---

## Fuera de alcance

- Historial `GET` de cierres para el POS (fase aparte)
- Sync legado `open_cash_shift` / `close_cash_shift` como camino de desbloqueo
- Paridad de cierres Standalone ↔ EN1
