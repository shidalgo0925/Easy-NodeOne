# EPosOne ↔ EN1 — Dónde quedamos (handoff)

| Campo | Valor |
|-------|--------|
| Fecha | **10 jul 2026** |
| Rama | `develop` @ **`9014e21`** (código EN1-02: `82c68f7`) |
| Silo | Solo **Dev EN1** — `https://appdev.easynodeone.com` · servicio `easynodeone-dev` |
| Modo | **Estricto Dev** — sin staging/prod/relatic |
| Estado | **EN1-02 congelado** · appdev **listo para E2E** · turno **EPosOne (APK)** |

---

## Una frase

EN1 ya no debe desarrollar provisioning: el contrato oficial es **código = destino (Caja)**.  
La tablet solo envía **URL + código**. Siguiente trabajo = pruebas E2E en la APK contra appdev.

---

## Congelado en EN1 (no reabrir sin GO)

| Entrega | Commit |
|---------|--------|
| Dominio POS + LicensePolicy stub | `18f6593` |
| EN1-01 APIs (legacy: refs en body) | `847a09f` |
| **EN1-02 código = destino** | **`82c68f7`** |
| Docs handoff “listo E2E” | **`9014e21`** |

### Contrato oficial

[`EPOSONE_EN1_HITO1_PROVISIONING_CONTRACT.md`](EPOSONE_EN1_HITO1_PROVISIONING_CONTRACT.md) — contenido **EN1-02**.

| API | Auth | Body mínimo |
|-----|------|-------------|
| `POST /api/v1/devices/register` | `X-EN1-Provisioning-Code` | `device_uuid` + metadatos dispositivo |
| `GET /api/v1/devices/config` | `Authorization: Bearer <token>` | — |

**No** pedir en el Wizard: `organization_id`, `branch_ref`, `pos_ref`, `register_ref`.

Admin: EPosOne → **Dispositivos** → Generar/Rotar código **por Caja**.

---

## Cómo probar E2E (checklist)

1. appdev: Sucursal → POS → Caja (register con parent = POS).  
2. Dispositivos → **Generar** código para esa caja.  
3. APK: URL `https://appdev.easynodeone.com` + código.  
4. Esperado: register `201` → guardar token → config → pantalla PIN.  
5. Reprovision (mismo UUID): `201`, token nuevo, `config_version`++.

---

## Fuera de alcance (hasta nuevo GO)

- Sync catálogo / ventas / inventario  
- Licencias / planes  
- FE, CRM, IA, KDS nuevo  
- Despliegue fuera de Dev  

---

## Repos

| Pieza | Dónde |
|-------|--------|
| EN1 | `/opt/easynodeone/dev/app` · GitHub Easy-NodeOne · `develop` |
| APK EPosOne | PC: `C:\Users\shidalgo\Documents\0. Tecnologia\EPosOne\eposone` |

---

## Chat nuevo

- **EPosOne:** integración Wizard + E2E tablet.  
- **EN1:** solo bugs de API / contrato si la APK reporta desalineación.
