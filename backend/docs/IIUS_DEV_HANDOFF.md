# Handoff IIUS → DEV

**Estado:** cerrado por Git (2026-05-22). **Estado global:** `IIUS_CIRCUIT_STATUS.md`.

---

## Hecho en DEV

| Paso | Estado |
|------|--------|
| Merge `origin/release/iius-go-20260522` → `develop` | OK — commit **`9330cfc`** |
| Tag `iius-go-20260522` en remoto | OK — apunta a **`9330cfc`** |
| `dev_apply_iius_tarball.sh` | En repo (alternativa si llega tar a `/tmp`) |
| `verify_payments_tenant_setup.py` | OK |
| `run_etapa1_dev_validation.py` | 22 OK — `source /opt/easynodeone/dev/.env` |
| `easynodeone-dev` | active |

---

## Hecho en IIUS prod (`vmi3215083`)

| Paso | Estado |
|------|--------|
| `git checkout iius-go-20260522` | OK |
| `systemctl restart nodeone.service` | OK |
| `go_iius_validate_all.sh` | OK |
| Migraciones + semillas §§2–4 runbook | OK (deploy 2026-05-22) |

---

## Release Git (ruta usada — sin tarball)

Rama: **`release/iius-go-20260522`** (`6b0da66` release + `8240166` handoff).

```bash
# Ya ejecutado en DEV; referencia histórica:
cd /opt/easynodeone/dev/app
git fetch origin
git checkout develop && git pull origin develop
git merge origin/release/iius-go-20260522 -m "Merge IIUS release mayo 2026"
git tag -f -a iius-go-20260522 -m "Release IIUS operativo mayo 2026"
git push origin develop
git push --force origin iius-go-20260522   # si el tag remoto apuntaba a commit anterior
```

---

## Tarball / scp (opcional, no bloqueante)

- Tar en IIUS: `/opt/easynodeone/backups/iius-release-to-dev_20260522_2249.tar.gz`
- `scp` IIUS → DEV falló por **publickey**; el merge por Git reemplazó este paso.
- Si en el futuro hace falta el tar: `bash backend/scripts/dev_apply_iius_tarball.sh /tmp/iius-release-to-dev_*.tar.gz`
- Regenerar en IIUS: `bash backend/scripts/package_iius_release_tar.sh`

---

## Validación DEV

```bash
cd /opt/easynodeone/dev/app/backend
set -a && source /opt/easynodeone/dev/.env && set +a
export NODEONE_BRAND_PRESET=iius
bash scripts/go_iius_validate_all.sh
```

En DEV, `test_academic_gate_iius.py` puede mostrar 2 FAIL (usuarios org 1 sin matrícula en BD multi-tenant). En IIUS prod debe pasar.

---

## Pendiente (negocio)

Ver `IIUS_CIRCUIT_STATUS.md` — PayPal live + QA navegador en `apps.internationalinstitute.us`.
