# IIUS → DEV: transferir parches para commit en `develop`

El silo IIUS (`/opt/easynodeone/app`) tiene cambios locales **no commiteados**. La política del proyecto exige commit solo desde **`/opt/easynodeone/dev/app`**.

## Opción A — Tarball (recomendado)

**En IIUS:**

```bash
cd /opt/easynodeone/app/backend
bash scripts/package_iius_release_tar.sh
# Salida: /opt/easynodeone/backups/iius-release-to-dev_YYYYMMDD_HHMM.tar.gz
```

**Copiar al host DEV** (`194.60.201.29`):

```bash
# En silo IIUS (vmi3215083):
scp /opt/easynodeone/backups/iius-release-to-dev_20260522_2249.tar.gz dev@194.60.201.29:/tmp/
```

Primera vez: aceptar host key (`ssh-keyscan -H 194.60.201.29 >> ~/.ssh/known_hosts`).

**SSH:** el usuario `dev@194.60.201.29` exige clave pública autorizada en DEV o copia manual (USB/SFTP). Desde IIUS sin clave: `Permission denied (publickey)` — alguien con acceso debe ejecutar el `scp` o añadir la pubkey de IIUS a `~dev/.ssh/authorized_keys`.

**En DEV** (cuando el tar esté en `/tmp`):

```bash
bash /opt/easynodeone/dev/app/backend/scripts/dev_apply_iius_tarball.sh /tmp/iius-release-to-dev_20260522_2249.tar.gz
git push origin develop
git push origin iius-go-20260522
```

O manualmente: extraer tar → `git add` rutas de `IIUS_COMMIT_PATHS.txt` (sin `.env`) → `git commit -F backend/docs/IIUS_COMMIT_MESSAGE.txt` → tag `iius-go-20260522`.

**Validación en DEV (Postgres):** el `.env` del silo DEV está en **`/opt/easynodeone/dev/.env`** (no `app/.env`):

```bash
cd /opt/easynodeone/dev/app/backend
set -a && source /opt/easynodeone/dev/.env && set +a
# alternativa: source ../../.env
export NODEONE_BRAND_PRESET=iius
python3 verify_payments_tenant_setup.py
python3 run_etapa1_dev_validation.py
bash scripts/go_iius_validate_all.sh   # tras aplicar el tar
```

`run_etapa1` fallaba si el proceso usaba SQLite readonly sin este `.env`.

## Opción B — rsync directo

```bash
rsync -avz --files-from=/opt/easynodeone/app/backend/docs/IIUS_COMMIT_PATHS.txt \
  --exclude='.env' \
  /opt/easynodeone/app/ USUARIO@HOST_DEV:/opt/easynodeone/dev/app/
```

Luego commit en DEV como arriba.

## Después del push — IIUS prod (`/opt/easynodeone/app`)

Solo `git pull` / checkout del tag + reinicio (**sin** editar archivos a mano en prod):

```bash
cd /opt/easynodeone/app
git fetch origin
git checkout iius-go-20260522
sudo systemctl restart nodeone.service
cd backend && source ../.venv/bin/activate
export NODEONE_BRAND_PRESET=iius
bash scripts/go_iius_validate_all.sh
```

Migraciones y semilla (SQLite IIUS): `docs/ETAPA2_IIUS_RUNBOOK.md` §§2–4 si aplica tras el tag.

PayPal live: `docs/IIUS_PAYPAL_LIVE.md` (independiente del deploy).

## PayPal live

Ver `IIUS_PAYPAL_LIVE.md` (independiente del commit).
