# EPosOne ↔ EN1 — Dónde quedamos (handoff)

| Campo | Valor |
|-------|--------|
| Fecha | **10 jul 2026** |
| Rama | `develop` @ **`82c68f7`** |
| Silo | Solo **Dev EN1** (`https://appdev.easynodeone.com`) |
| Estado hito | **EN1-02 congelado** · appdev listo para pruebas E2E |

---

## Estado en una frase

**EN1-02 congelado y desplegado en appdev.**  
Contrato oficial: código = destino (Caja). Wizard: **URL + código**.  
Turno: equipo **EPosOne** — pruebas E2E contra Dev.

---

## Hecho en EN1 (congelado)

| Entrega | Commit |
|---------|--------|
| POS + LicensePolicy | `18f6593` |
| EN1-01 (legacy) | `847a09f` |
| **EN1-02 código = destino** | **`82c68f7`** ← actual |

### APIs en appdev

| Método | Path |
|--------|------|
| `POST` | `/api/v1/devices/register` |
| `GET` | `/api/v1/devices/config` |

Contrato: [`EPOSONE_EN1_HITO1_PROVISIONING_CONTRACT.md`](EPOSONE_EN1_HITO1_PROVISIONING_CONTRACT.md) (EN1-02).

Admin: EPosOne → **Dispositivos** → Generar código por Caja.

---

## Listo para pruebas

1. En appdev: crear/verificar Sucursal → POS → Caja.  
2. Generar código en Dispositivos.  
3. APK: URL `https://appdev.easynodeone.com` + código.  
4. Esperado: register → token → config → PIN.

---

## No tocar sin GO

Sync · catálogo · ventas · licencias · staging/prod/relatic.
