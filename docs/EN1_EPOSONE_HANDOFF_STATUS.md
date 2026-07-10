# EPosOne ↔ EN1 — Dónde quedamos (handoff)

| Campo | Valor |
|-------|--------|
| Fecha | **10 jul 2026** |
| Rama | `develop` @ `847a09f` |
| Silo | Solo **Dev EN1** (`appdev.easynodeone.com`) |

---

## Estado en una frase

**EN1 ya entregó el servidor de provisioning (Hito EN1-01).**  
La pelota está en **EPosOne (APK Flutter)**: cablear el wizard «Conectar EN1» a esas APIs y probar E2E con tablet.

---

## Hecho en EN1 (no reabrir sin GO)

| Entrega | Commit | Notas |
|---------|--------|-------|
| Dominio V4 + POS + LicensePolicy stub | `18f6593` | Cupos apagados |
| Docs Etapa 2 Android | `92562a0` | APK en PC local, no en este servidor |
| **Hito EN1-01** APIs provisioning | **`847a09f`** | Contrato + register/config + token + admin |

### APIs listas (appdev)

| Método | Path | Auth |
|--------|------|------|
| `POST` | `/api/v1/devices/register` | Header `X-EN1-Provisioning-Code` |
| `GET` | `/api/v1/devices/config` | `Authorization: Bearer <token>` |

Contrato: [`EPOSONE_EN1_HITO1_PROVISIONING_CONTRACT.md`](EPOSONE_EN1_HITO1_PROVISIONING_CONTRACT.md)

Código: `backend/nodeone/modules/eposone/device_provisioning.py`, `devices_v1_routes.py`

Admin: EPosOne → **Dispositivos** (código de provisioning + listado).

Smoke EN1: unit tests + register/config/reprovision en BD Dev — OK.  
**E2E tablet:** pendiente (criterio de cierre del hito con APK).

---

## No hecho (siguiente trabajo)

| Quién | Qué |
|-------|-----|
| **EPosOne / Flutter** | Quitar stub «Conectar EN1»; llamar register + config; guardar token; ir a PIN |
| **EPosOne** | Prueba con tablet de demo contra appdev |
| **Ambos** | Si el contrato Flutter difiere de EN1 → proponer ajuste **antes** de cambiar paths |
| **Después** | Sync inteligente (productos/ventas) — **no** ahora |
| **Nunca en este hito** | Licencias, FE, CRM, IA, KDS nuevo, etc. |

---

## Foco actual del proyecto

```text
EN1  ████████████░░░░  provisioning APIs ✅  (esperando E2E)
APK  ████░░░░░░░░░░░░  Core ✅ · wizard EN1 stub → integrar EN1-01
Sync █░░░░░░░░░░░░░░░  después del E2E provisioning
```

**No** desarrollar sync de catálogo ni features TPV nuevas hasta cerrar:

Instalar APK → Wizard → Conectar EN1 → Register → Token → Config → PIN.

---

## Dónde está cada repo

| Pieza | Ubicación |
|-------|-----------|
| EN1 | `/opt/easynodeone/dev/app` · GitHub Easy-NodeOne · `develop` |
| APK EPosOne | PC: `C:\Users\shidalgo\Documents\0. Tecnologia\EPosOne\eposone` (no en este servidor) |

---

## Chat nuevo

Para el prog EN1: solo soporte de contrato / bugs de API si Flutter reporta.  
Para el prog EPosOne: integración contra `847a09f` + contrato EN1-01.
