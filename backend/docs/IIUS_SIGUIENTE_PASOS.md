# IIUS — qué falta y cómo retomar

**Host:** `vmi3215083`  
**Última actualización:** 2026-05-27  
**Rama viva:** `iius-product` en `/opt/easynodeone/app`  
**Runtime prod:** `/opt/easynodeone/app` (no `/var/www/nodeone`, no editar staging/prod/relatic fuera de Git)

Documento de handoff para continuar en otra sesión. Detalle técnico de infra: [`IIUS_INFRA_READINESS.md`](IIUS_INFRA_READINESS.md). Freeze funcional: [`IIUS_FREEZE.md`](IIUS_FREEZE.md).

---

## Hecho (no repetir salvo incidente)

| Área | Estado |
|------|--------|
| **PostgreSQL 16** | BD `iius_nodeone`, rol `iius_nodeone_app`, migración pgloader desde SQLite OK |
| **`.env`** | `DATABASE_URL` + `SQLALCHEMY_DATABASE_URI` → Postgres |
| **Servicio** | `nodeone.service` activo tras reinicio |
| **Backup SQLite** | `/opt/easynodeone/backups/NodeOne_pre_postgres_*.db` |
| **Password PG** | `/opt/easynodeone/app/instance/.pg_password` (chmod 600, **no commitear**) |
| **Esqueleto `/opt/iius`** | `dev`, `staging`, `prod` con `{app,backups,logs}` + `.env.example` |
| **Smokes post-Postgres** | catálogo 12/12, pagos 6/6, gate OK |
| **Pagos test** | Yappy manual #9 → `cancelled`; checkout IIUS = PayPal + wire |

**HEAD remoto conocido:** `d06b76d` (`test(iius): smoke pagos tolera cola Yappy vacía tras limpieza`).

---

## Pendiente (orden sugerido)

### 1. Cerrar hito en Git (prioritario)

Working tree **sucio** — sin push de la migración/infra:

- `backend/scripts/migrate_iius_sqlite_to_postgresql.sh` (nuevo)
- `backend/scripts/provision_iius_opt_layout.sh` (nuevo)
- `backend/scripts/audit_iius_infra_readiness.py` (detecta `/opt/iius/*/app`)
- `backend/docs/IIUS_INFRA_READINESS.md` (Postgres + `/opt/iius`)

**No incluir en commit:** `.env`, `instance/.pg_password`, `*.db`, uploads, venv.

```bash
cd /opt/easynodeone/app
git add backend/scripts/migrate_iius_sqlite_to_postgresql.sh \
        backend/scripts/provision_iius_opt_layout.sh \
        backend/scripts/audit_iius_infra_readiness.py \
        backend/docs/IIUS_INFRA_READINESS.md \
        backend/docs/IIUS_SIGUIENTE_PASOS.md
git commit -m "$(cat <<'EOF'
infra(iius): Postgres migración, /opt/iius esqueleto y docs handoff

EOF
)"
git push origin iius-product
# Opcional:
# git tag -a iius-postgres-v1 -m "Prod IIUS en PostgreSQL 16"
# git push origin iius-postgres-v1
```

### 2. Validación periódica (tras cada deploy)

```bash
cd /opt/easynodeone/app/backend
source ../.venv/bin/activate
python scripts/audit_iius_infra_readiness.py   # engine → …/iius_nodeone
python scripts/smoke_iius_catalog_events.py
python scripts/smoke_iius_payments_ops.py
python scripts/test_academic_gate_iius.py
# Opcional recursos/leads:
# python scripts/smoke_program_resources_iius.py
```

### 3. Operación / runbook interno

- [ ] Anotar en gestor de secretos (fuera del repo) usuario/contraseña de `iius_nodeone_app`.
- [ ] Política de backups Postgres (`pg_dump` cron → `/opt/easynodeone/backups/` o `/opt/iius/prod/backups/`).
- [ ] Decidir si se **archiva** `instance/NodeOne.db` (solo lectura) o se mantiene como fallback temporal.
- [ ] Revisar warning no bloqueante: `No module named 'license_validator'`.

### 4. Silos `/opt/iius` (futuro, no urgente)

El esqueleto existe; **prod real sigue en** `/opt/easynodeone/app`. Para separar entornos hace falta:

- [ ] Clonar repo en cada `/opt/iius/{dev,staging,prod}/app`
- [ ] `.env` propio, venv, unit systemd y dominio por silo
- [ ] Probar migración Postgres en **staging** antes de cualquier otro corte
- [ ] Checklist en `IIUS_INFRA_READINESS.md` § “antes de separar entornos”

### 5. Producto / línea `iius-product` (si sigue el roadmap)

Revisar [`IIUS_FREEZE.md`](IIUS_FREEZE.md) y tags existentes:

`iius-freeze-20260527`, `iius-resources-v1`, `iius-lead-capture-v1`, …

Posibles siguientes bloques (según acuerdo de producto, no infra):

- Matriz acceso 10 casos automatizada en script dedicado (hoy documentada en ops/chat).
- Lead capture / recursos: smoke `smoke_program_resources_iius.py` en CI o cron.
- Merge `iius-product` ↔ `develop`/`main`: **solo con acuerdo explícito**.

---

## Comandos rápidos de diagnóstico

```bash
systemctl status nodeone.service --no-pager
sudo -u postgres psql -d iius_nodeone -c "SELECT count(*) FROM users;"
grep -E '^DATABASE_URL=' /opt/easynodeone/app/.env | sed 's/:[^:@]*@/:***@/'
ls -la /opt/iius/
```

Restaurar solo si hay incidente grave (ventana de mantenimiento):

1. Parar `nodeone.service`
2. Restaurar `.env` a SQLite **o** restore `pg_dump`
3. `systemctl start nodeone.service` + smokes

Script referencia migración: `backend/scripts/migrate_iius_sqlite_to_postgresql.sh`.

---

## Reglas que no olvidar

1. Commits y push desde `/opt/easynodeone/app`, rama `iius-product`.
2. Deploy prod: `git pull origin iius-product` + deps + `bootstrap`/schema si aplica + `systemctl restart nodeone.service`.
3. Org 1: `academic_closed`, `REQUIRE_PAID_ACCESS=true` — no relajar gate sin decisión de negocio.
4. En este servidor **no** existe `/opt/easynodeone/dev/app`; la política global del monorepo aplica donde exista `dev/app`.

---

## Contacto con sesión anterior

Transcript Cursor (si hace falta contexto): buscar en el proyecto por `iius-product`, `postgres`, `provision_iius_opt_layout`.
