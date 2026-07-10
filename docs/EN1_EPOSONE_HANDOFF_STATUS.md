# EPosOne ↔ EN1 — Dónde quedamos (handoff)

| Campo | Valor |
|-------|--------|
| Fecha | **10 jul 2026** |
| Rama | `develop` (EN1-02 en working tree / próximo commit) |
| Silo | Solo **Dev EN1** (`appdev.easynodeone.com`) |

---

## Estado en una frase

**Contrato oficial = EN1-02:** el código de provisioning identifica **Caja (destino)** → EN1 resuelve Empresa/Sucursal/POS/Caja.  
Wizard tablet: solo **URL + código**.

EN1-01 queda como **legacy** (refs en body + código por org).

---

## Hecho en EN1

| Entrega | Commit / estado |
|---------|-----------------|
| POS + LicensePolicy | `18f6593` |
| EN1-01 APIs (legacy) | `847a09f` |
| **EN1-02 código = destino** | Implementado (tabla `eposone_provisioning_code`, register sin refs) |

### APIs

| Método | Path | Contrato oficial |
|--------|------|------------------|
| `POST` | `/api/v1/devices/register` | Header código + `device_uuid` (+ metadatos). **Sin** org/branch/pos/register en body |
| `GET` | `/api/v1/devices/config` | `Authorization: Bearer` |

Contrato: [`EPOSONE_EN1_HITO1_PROVISIONING_CONTRACT.md`](EPOSONE_EN1_HITO1_PROVISIONING_CONTRACT.md) (documento actualizado a EN1-02).

Admin: EPosOne → Dispositivos → **Generar** código por Caja.

---

## Siguiente

| Quién | Qué |
|-------|-----|
| **EPosOne** | Wizard: URL + código → register EN1-02 → token → config → PIN |
| **E2E** | Tablet contra appdev |
| **No ahora** | Sync catálogo/ventas |

---

## Repos

| Pieza | Ubicación |
|-------|-----------|
| EN1 | `/opt/easynodeone/dev/app` · `develop` |
| APK | PC local `…\EPosOne\eposone` |
