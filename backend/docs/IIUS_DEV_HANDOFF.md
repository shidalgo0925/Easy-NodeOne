# Handoff IIUS → DEV (estado 2026-05-22)

## Módulos SaaS (Ventas / Contabilidad)

Corrección de menú vs flags en Módulos: ver **`backend/docs/MODULOS_SAAS_VENTAS_Y_CONTABILIDAD.md`** (incluye bootstrap `ensure_saas_catalog_full` y archivos a mergear en `develop`).

## Bloqueo scp (alternativa Git — preferida si el tar no llega)

Rama publicada desde IIUS: **`release/iius-go-20260522`** (commit `6b0da66`).

**En DEV:**

```bash
cd /opt/easynodeone/dev/app
git fetch origin
git checkout develop && git pull origin develop
git merge origin/release/iius-go-20260522 -m "Merge IIUS release mayo 2026"
git tag -a iius-go-20260522 -m "Release IIUS operativo mayo 2026"
git push origin develop
git push origin iius-go-20260522
```

No hace falta el tarball si el merge anterior es limpio.

## Bloqueo scp (tar manual)

El tarball puede **no estar** en DEV (`/tmp/iius-release-to-dev_*.tar.gz`).

Desde IIUS (`vmi3215083`) el `scp` a `dev@194.60.201.29` falla con **`Permission denied (publickey)`** — copiar por SFTP o autorizar clave SSH.

## Archivo en IIUS

```
/opt/easynodeone/backups/iius-release-to-dev_20260522_2249.tar.gz
```

Regenerar: `bash backend/scripts/package_iius_release_tar.sh`

## Ya hecho en DEV (sin tar)

| Paso | Estado |
|------|--------|
| `dev_apply_iius_tarball.sh` | En repo `develop` (commit `72b4c21`) |
| `verify_payments_tenant_setup.py` | OK |
| `run_etapa1_dev_validation.py` | 22 OK con `source /opt/easynodeone/dev/.env` |
| Tag `iius-go-20260522` | Pendiente hasta aplicar tar + commit |

## Cuando el tar esté en DEV `/tmp`

```bash
ls -la /tmp/iius-release-to-dev_20260522_2249.tar.gz
bash /opt/easynodeone/dev/app/backend/scripts/dev_apply_iius_tarball.sh /tmp/iius-release-to-dev_20260522_2249.tar.gz
git push origin develop
git push origin iius-go-20260522
```

Si el tag existía en remoto apuntando a `63203e6`: acordar `git push --force origin iius-go-20260522` solo si el equipo lo aprueba.

Post-tar en DEV:

```bash
cd /opt/easynodeone/dev/app/backend
set -a && source /opt/easynodeone/dev/.env && set +a
export NODEONE_BRAND_PRESET=iius
bash scripts/go_iius_validate_all.sh
```

## Después del push — IIUS prod

En host IIUS (`/opt/easynodeone/app`), no en DEV:

```bash
git fetch && git checkout iius-go-20260522
sudo systemctl restart nodeone.service
bash backend/scripts/go_iius_validate_all.sh
# ETAPA2_IIUS_RUNBOOK.md §§2–4 + IIUS_PAYPAL_LIVE.md
```

## Desbloquear scp (opciones)

1. En DEV: añadir pubkey de IIUS a `~dev/.ssh/authorized_keys` (pedir a quien administre IIUS la salida de `cat ~/.ssh/id_ed25519_github.pub` en IIUS).
2. Copiar el `.tar.gz` por panel/SFTP a `/tmp/` en DEV.
3. Ejecutar `scp` desde una máquina que ya tenga acceso a ambos hosts.
