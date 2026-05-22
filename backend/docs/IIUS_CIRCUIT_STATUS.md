# IIUS — Estado del circuito (referencia rápida)

**Última actualización:** 2026-05-22  
**Leer primero en la próxima sesión.** Detalle operativo: `IIUS_GO_CHECKLIST.md`, `ETAPA2_IIUS_RUNBOOK.md`, `IIUS_PAYPAL_LIVE.md`.

---

## Referencias Git (alineadas)

| Ref | Commit | Notas |
|-----|--------|--------|
| `origin/develop` | `9330cfc` | Merge `release/iius-go-20260522` |
| Tag `iius-go-20260522` | `9330cfc` | Mismo commit que `develop` |
| Release branch | `6b0da66` + handoff `8240166` | Ya fusionado en `develop` |
| Rollback IIUS (código) | `iius-pre-etapa2-20260522` | Pre-Etapa 2 en silo IIUS |
| Baseline histórico | `b605a78` | Solo referencia |

**Hosts**

| Silo | Ruta app | Servicio | Dominio |
|------|----------|----------|---------|
| DEV | `/opt/easynodeone/dev/app` | `easynodeone-dev` | `appdev.easynodeone.com` |
| IIUS prod | `/opt/easynodeone/app` | `nodeone.service` | `apps.internationalinstitute.us` |

---

## Circuito — estado real

| Bloque | Estado |
|--------|--------|
| **Git ↔ DEV ↔ IIUS prod (código)** | **Cerrado** — `9330cfc` en los tres |
| **DEV técnico** | **Cerrado** — merge, tag push, servicio active, `run_etapa1_dev_validation` 22 OK, `verify_payments` OK |
| **IIUS prod deploy** | **Hecho** (2026-05-22) — checkout tag, restart, `go_iius_validate_all.sh` OK (gate, 5 landings, `org_id=1`) |
| **BD IIUS** | **Hecho** — `subdomain=iius`, `academic_closed`, 5 programas, migraciones idempotentes |
| **Tarball / scp** | **No obligatorio** — release por Git (`release/iius-go-20260522`); tar opcional en `/opt/easynodeone/backups/` en IIUS |
| **DEV `test_academic_gate_iius`** | 2 FAIL esperados (BD multi-tenant); no desalinea prod |
| **PayPal live** | **Pendiente** — `mode=live`, `client_id` MISSING → demo |
| **QA navegador IIUS** | **Pendiente** — inscripción + pago real + campus |
| **Yappy** | **N/A** IIUS |

**Progreso circuito completo:** ~90 % — falta negocio (PayPal live + prueba manual).

---

## Qué está cerrado vs qué falta

### Cerrado (técnico / servidores)

- Merge IIUS → `develop` sin tarball (`9330cfc`).
- Tag `iius-go-20260522` en remoto (force desde `63203e6` si aplicaba).
- IIUS prod en tag, no en `63203e6` suelto.
- Etapa 1 pagos multi-tenant en DEV validada automáticamente.
- Inscripción académica, campus gate, landings — scripts OK en IIUS.

### Pendiente (negocio — no bloquea Git)

1. **PayPal live** — Admin → Pagos (org 1): Client ID + Secret. Ver `IIUS_PAYPAL_LIVE.md`.  
   Verificar: `python3 scripts/check_paypal_readiness_iius.py` → exit 0.
2. **Prueba manual** en `https://apps.internationalinstitute.us` — p. ej. `neuro-liderazgo-intercultural` → login → checkout → campus con matrícula `confirmed`.

### Opcional

- Cerrar PR `release/iius-go-20260522` en GitHub si quedó abierto.
- Commitear notas locales en IIUS si hay `.md` solo en servidor.
- Autorizar scp IIUS→DEV solo si quieren copia manual del tar.

---

## Comandos — próxima conexión

### DEV (verificar que sigue alineado)

```bash
cd /opt/easynodeone/dev/app
git fetch origin && git rev-parse develop origin/develop iius-go-20260522^{commit}
# Los tres deben mostrar 9330cfc (o el commit vigente documentado arriba)

cd backend
set -a && source /opt/easynodeone/dev/.env && set +a
export NODEONE_BRAND_PRESET=iius
python3 run_etapa1_dev_validation.py
python3 verify_payments_tenant_setup.py
# go_iius_validate_all.sh: gate puede FAIL en DEV; OK en IIUS
```

### IIUS prod (revalidar tras cambios)

```bash
cd /opt/easynodeone/app
git fetch origin && git rev-parse HEAD iius-go-20260522^{commit}
sudo systemctl restart nodeone.service
cd backend && set -a && source ../.env && set +a
export NODEONE_BRAND_PRESET=iius
bash scripts/go_iius_validate_all.sh
```

---

## Índice de documentación

| Archivo | Uso |
|---------|-----|
| **Este archivo** | Estado global y próximo paso |
| `IIUS_GO_CHECKLIST.md` | Checklist servidor IIUS |
| `IIUS_DEV_HANDOFF.md` | Historial merge Git vs tar |
| `IIUS_TRANSFER_TO_DEV.md` | Procedimiento tar (histórico) |
| `IIUS_PAYPAL_LIVE.md` | PayPal live |
| `ETAPA2_IIUS_RUNBOOK.md` | Deploy, migraciones, rollback |
| `ETAPA1_DEV_CHECKLIST.md` | Etapa 1 DEV (multi-tenant) |

---

## Historial (contacto)

| Fecha | Evento |
|-------|--------|
| 2026-05-22 | Etapa 2 IIUS en prod: GO técnico, backup, tag rollback `iius-pre-etapa2-20260522` |
| 2026-05-22 | Release Git: `release/iius-go-20260522` → merge DEV → tag `iius-go-20260522` @ `9330cfc` |
| 2026-05-22 | IIUS prod desplegado y validado; PayPal live y QA navegador pendientes |
