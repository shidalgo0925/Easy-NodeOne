# EPosOne ↔ EN1 — Dónde quedamos (handoff)

| Campo | Valor |
|-------|--------|
| Fecha | **13 jul 2026** |
| Rama | `develop` · código EN1-02: **`82c68f7`** · tag: **`eposone-provisioning-v1.0`** |
| Silo | Solo **Dev EN1** — `https://appdev.easynodeone.com` · `easynodeone-dev` |
| Modo | **Estricto Dev** — sin staging/prod/relatic |
| **Hito 1 Provisioning EN1-02** | **CERRADO / CONGELADO** |
| **Siguiente** | **Hito 2 Bootstrap** — API Dev lista · E2E APK (bajar catálogo/imágenes) |
| Contrato Hito 2 | [`EN1_EPOSONE_HITO2_DEVICE_BOOTSTRAP_SYNC_DOWN.md`](EN1_EPOSONE_HITO2_DEVICE_BOOTSTRAP_SYNC_DOWN.md) · `GET /api/v1/devices/bootstrap` |
| Productos / inventario BO | [`EN1_EPOSONE_HANDOFF_PRODUCTOS_INVENTARIO.md`](EN1_EPOSONE_HANDOFF_PRODUCTOS_INVENTARIO.md) |

---

## Una frase

**Hito 1 cerrado:** la tablet se provisiona solo con URL + código de Caja; EN1 no reabre provisioning sin GO.  
**Hito 2:** bajar catálogo/imágenes/precios/UOM/stock/config desde EN1 — **contrato listo, sin sync implementado**.

---

## Hito 1 — cierre formal (13 jul 2026)

| Chequeo E2E | Estado |
|-------------|--------|
| URL `https://appdev.easynodeone.com` | ✅ |
| Código de Caja (Itsmo org 5 · `caja-01`) | ✅ |
| `POST /api/v1/devices/register` → 201 | ✅ (verificado EN1 + tablet) |
| Token Bearer | ✅ |
| Empresa → Sucursal → POS → Caja | ✅ |
| UUID dispositivo | ✅ |
| Config post-registro | ✅ |
| Reinicio sin Wizard → PIN | ✅ / bitácora APK (si falta un renglón, no reabre el hito) |
| Reprovision mismo UUID | **Opcional** — no bloquea cierre |

### Congelado (no reabrir sin GO)

| Entrega | Commit / nota |
|---------|----------------|
| Dominio POS + LicensePolicy stub | `18f6593` |
| EN1-01 APIs (legacy) | `847a09f` |
| **EN1-02 código = destino** | **`82c68f7`** |
| Docs “listo E2E” | `9014e21` |
| **Cierre Hito 1 + contrato Hito 2** | tag **`eposone-provisioning-v1.0`** |

### Contrato oficial Hito 1

[`EPOSONE_EN1_HITO1_PROVISIONING_CONTRACT.md`](EPOSONE_EN1_HITO1_PROVISIONING_CONTRACT.md)

| API | Auth | Body mínimo |
|-----|------|-------------|
| `POST /api/v1/devices/register` | `X-EN1-Provisioning-Code` | `device_uuid` + metadatos |
| `GET /api/v1/devices/config` | `Authorization: Bearer <token>` | — |

**No** en el Wizard: `organization_id`, `branch_ref`, `pos_ref`, `register_ref`.

---

## Hito 2 — Device Bootstrap (EN1 Dev)

| Pieza | Estado |
|-------|--------|
| Contrato | ✅ |
| `GET /api/v1/devices/bootstrap` | ✅ Dev / appdev (smoke Itsmo 8 productos + stock) |
| Consumo APK + E2E tablet | ⏳ equipo EPosOne |

Auth: Bearer del register. Query `include=config,products,stock` opcional.

---

## Fuera de alcance (hasta GO explícito)

- Implementación Sync Down / bootstrap  
- Sync ventas → stock  
- Licencias / FE / CRM / IA  
- Despliegue fuera de Dev  

---

## Repos

| Pieza | Dónde |
|-------|--------|
| EN1 | `/opt/easynodeone/dev/app` · `develop` · tag `eposone-provisioning-v1.0` |
| APK EPosOne | PC equipo (Flutter local) |

---

## Chat nuevo

- **Cierre Hito 1:** este handoff + tag. No mezclar sync.  
- **Hito 2:** chat + **GO** solo para implementar Device Bootstrap tras aprobar contrato.  
- Bugs de register/config: solo si la APK reporta desalineación del Hito 1.
