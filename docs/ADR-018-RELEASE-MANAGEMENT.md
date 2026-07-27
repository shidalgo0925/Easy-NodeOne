# ADR-018 — Release Management EN1 (DEV → STAGING → PROD)

| Campo | Valor |
|-------|-------|
| ID | ADR-018 |
| Título | Release Management — pipeline oficial EN1 |
| Estado | **Aprobado (proceso)** — 27 jul 2026 |
| Ámbito | Todos los productos EN1 / ETS (EPosOne, EPayRoll, Portal, futuros) |
| Relacionados | [`CHECKLIST_ACTUALIZACION_Y_CLIENTES.md`](CHECKLIST_ACTUALIZACION_Y_CLIENTES.md) · [`REGLAS-DE-TRABAJO.md`](../REGLAS-DE-TRABAJO.md) · [`AGENTS.md`](../AGENTS.md) · [ADR-017](ADR-017-CUSTOMER-ENTRY-POINT-PRODUCT-PORTAL.md) · [`EN1_DEPLOY_LIMPIEZA_CONTEXTO.md`](EN1_DEPLOY_LIMPIEZA_CONTEXTO.md) |
| Precedencia | **Proceso obligatorio** para releases a clientes. Complementa (no reemplaza) el checklist de comunicación a clientes. |

---

## Pregunta rectora

> **¿Cómo publicamos un producto EN1 a producción de forma repetible, con QA, backup y rollback &lt; 15 min — sin `git pull` a ciegas en prod?**

---

## Decisión

**Pipeline oficial (todos los productos):**

```text
DEV (develop) → Feature Freeze → Tag RC → STAGING (= mismo commit/tag)
       → QA + Performance → Backup PROD → GO LIVE
       → PROD (= mismo tag) → Smoke → Publicación comercial
```

| Regla | Valor |
|-------|--------|
| Edición de código | Solo `/opt/easynodeone/dev/app` · rama `develop` |
| Release Candidate | Tag anotado (`vX.Y.Z-rcN` o `vX.Y.Z`) en commit de `main` / merge acordado |
| Staging | Checkout **exacto** al mismo commit/tag del RC — cero drift |
| Producción | Solo el tag/commit **aprobado con GO LIVE** — nunca “lo último de develop” |
| Rollback | Procedimiento documentado por release; objetivo &lt; 15 minutos |

**Prohibido en staging/prod/relatic:** editar código a mano, copiar carpetas entre silos, `git pull` sin referencia explícita.

---

## Fases del Release (checklist)

### Fase 1 — Congelamiento (Feature Freeze)

- [ ] DEV contiene solo funcionalidades **aprobadas**
- [ ] No nuevas features hasta cerrar el release (solo fixes críticos)
- [ ] Generar versión: tag + commit + fecha + changelog
- [ ] Entregar paquete de release en `docs/releases/`

### Fase 2 — Preparación STAGING

- [ ] `git fetch origin --tags`
- [ ] Checkout del **mismo** tag/commit del RC en `/opt/easynodeone/staging/app`
- [ ] Deps (`pip`/venv del silo) si el release lo requiere
- [ ] Migraciones / bootstrap contra BD **staging** (`.env` del silo)
- [ ] Assets estáticos OK
- [ ] Reinicio `easynodeone-staging`
- [ ] Verificar: sin diff de código vs RC (`git rev-parse HEAD` = tag)

### Fase 3 — QA funcional (staging)

Portal, auth, org, licenciamiento, provisioning, producto, sync, seguridad — ver plantilla en el paquete del release (`docs/releases/…`).

### Fase 4 — Performance / salud

- [ ] Logs sin errores críticos nuevos
- [ ] Memoria / CPU / workers / colas aceptables
- [ ] Sin consultas obviamente rotas en el smoke

### Fase 5 — Backup producción (antes de tocar prod)

- [ ] Dump PostgreSQL prod
- [ ] Nota del commit/tag actual en prod
- [ ] Confirmar `.env`, nginx, units systemd, uploads (rutas)
- [ ] Guardar **punto de restauración** (path + fecha + hash)

### Fase 6 — Rollback documentado

Cada release debe incluir sección “Rollback &lt; 15 min” con:

1. Checkout del tag/commit **anterior** en `prod/app`
2. Restaurar BD **solo si** hubo migraciones incompatibles (dump Fase 5)
3. Deps / assets / reinicio servicio
4. Smoke mínimo

### Fase 7 — Release producción (solo con **GO LIVE**)

- [ ] Checkout del tag RC aprobado
- [ ] Deps si aplica
- [ ] Migraciones contra `easynodeone_prod` (owner correcto)
- [ ] `post_deploy_cleanup` si aplica
- [ ] Reinicio `easynodeone-prod`
- [ ] **No** ejecutar pasos no necesarios para ese release

### Fase 8 — Smoke test producción

Org de prueba: login, provisioning, flujo mínimo del producto, portal.

### Fase 9 — Publicación comercial

Landings / Portal / launcher según [ADR-017](ADR-017-CUSTOMER-ENTRY-POINT-PRODUCT-PORTAL.md). Hosts comerciales, no `appprd` en marketing.

### Fase 10 — Infraestructura

`appprd.easynodeone.com` = **técnico**. Cliente: hosts de producto + `app.easytech.services` cuando multiproducto.

### Fase 11 — Documentación

Actualizar ADRs / changelog / riesgos pendientes / checklist firmado.

---

## Comandos canónicos (silo ≠ dev)

```bash
# Referencia acordada (ejemplo)
TAG=v1.0.0-rc1   # o v1.0.0 tras GO LIVE
SILO=staging     # staging | prod

cd /opt/easynodeone/$SILO/app
git -c safe.directory=/opt/easynodeone/$SILO/app fetch origin --tags
git -c safe.directory=/opt/easynodeone/$SILO/app checkout "$TAG"

# Solo prod, y solo con GO LIVE explícito:
# export EASYNODEONE_DEPLOY_PROD_CONFIRM=YES

sudo systemctl restart easynodeone-$SILO
systemctl is-active easynodeone-$SILO
git -c safe.directory=/opt/easynodeone/$SILO/app rev-parse --short HEAD
```

Migraciones / bootstrap: cargar el `.env` del **silo** (`/opt/easynodeone/$SILO/.env`), nunca el de otro entorno.

---

## Versionado

| Tipo | Ejemplo | Uso |
|------|---------|-----|
| Release Candidate | `v1.0.0-rc1` | Freeze + staging + QA |
| Release | `v1.0.0` | Tras GO LIVE (puede ser el mismo commit que el RC si no hubo fixes) |
| Patch | `v1.0.1` | Fix crítico post-release |

Tags **anotados** en el remoto. El número de producto comercial (planes EPosOne) es independiente del semver de plataforma.

---

## Productos futuros

El mismo pipeline aplica a EPayRoll, EClassOne, etc.:

1. Freeze + tag en EN1
2. Staging = tag
3. QA del producto + portal/launcher
4. Backup + GO LIVE
5. Landing del producto (Host → ProductContext) si aplica

No se inventa un silo por producto: mismo proceso EN1, distinta superficie de host.

---

## Consecuencia para la IA (Codito)

1. Sin **GO** / sin pedido explícito → no editar, no desplegar.
2. Sin **GO LIVE** → no modificar producción.
3. Staging/prod: solo checkout de **tag o commit** acordado en el chat.
4. 1 chat = 1 tarea; release largo → paquete en `docs/releases/` + fases firmadas.

---

## Estado inicial (EPosOne — jul 2026)

Primer ejercicio formal del pipeline: ver [`docs/releases/EN1_RELEASE_v1.0.0.md`](releases/EN1_RELEASE_v1.0.0.md).
