# EN1 — Contexto: limpieza post-deploy

**Para:** IA, operación y programadores al desplegar en silos EN1 e IIUS.  
**Última actualización:** 2026-06-24  
**Rama:** `develop`

> Complementa [`CHECKLIST_ACTUALIZACION_Y_CLIENTES.md`](CHECKLIST_ACTUALIZACION_Y_CLIENTES.md) y [`REGLAS-DE-TRABAJO.md`](../REGLAS-DE-TRABAJO.md). No sustituye la norma de **tag/commit explícito** antes de pull en staging/prod/relatic.

---

## 1. Qué problema resuelve

`git pull` **sí** elimina archivos que Git dejó de versionar, pero **no**:

- borra **cachés** Python (`__pycache__`, `.pytest_cache`, `*.pyc`);
- quita **copias manuales** o restos de parches en rutas ya eliminadas del repo;
- hace limpieza de **untracked** fuera de Git (opcional, con cuidado).

Este flujo estandariza una **limpieza segura** tras cada deploy en **dev, staging, prod, relatic** e **IIUS**.

---

## 2. Scripts (versionados en el repo)

| Archivo | Rol |
|---------|-----|
| [`scripts/post_deploy_cleanup.sh`](../scripts/post_deploy_cleanup.sh) | Limpieza por silo |
| [`scripts/deploy_cleanup_manifest.txt`](../scripts/deploy_cleanup_manifest.txt) | Rutas legacy a borrar si existen |
| [`scripts/deploy_with_cleanup.sh`](../scripts/deploy_with_cleanup.sh) | Pull + pip + restart (servidor) + limpieza |

Tras el primer `git pull` que incluya estos archivos, viven en cada silo como  
`/opt/easynodeone/<silo>/app/scripts/...`.

---

## 3. Silos y rutas

| Instancia | Argumento | Árbol `app/` | Servicio systemd (típico) |
|-----------|-----------|--------------|---------------------------|
| Dev EN1 | `dev` | `/opt/easynodeone/dev/app` | `easynodeone-dev` |
| Staging | `staging` | `/opt/easynodeone/staging/app` | `easynodeone-staging` |
| Producción | `prod` | `/opt/easynodeone/prod/app` | `easynodeone-prod` |
| Relatic | `relatic` | `/opt/easynodeone/relatic/app` | `easynodeone-relatic` |
| IIUS | `iius` | `/opt/easynodeone/app` (host dedicado) | `nodeone.service` |

**IIUS** comparte el mismo repositorio Easy-NodeOne; el preset de marca es operativo (`NODEONE_BRAND_PRESET=iius`), no un silo más en el host EN1. Ver también [`backend/docs/IIUS_RELEASE_MANIFEST.md`](../backend/docs/IIUS_RELEASE_MANIFEST.md).

---

## 4. Orden recomendado en cada deploy

```text
git fetch / checkout (tag o commit acordado)
    → git pull
    → pip install (si cambió requirements.txt)
    → post_deploy_cleanup.sh <silo>
    → migrate-easynodeone-instance.sh (si hubo DDL)
    → systemctl restart
    → verificación mínima (login + pantalla del release)
```

Atajo en servidor (si existe `/opt/easynodeone/scripts/deploy-easynodeone-instance.sh`):

```bash
sudo bash /opt/easynodeone/dev/app/scripts/deploy_with_cleanup.sh staging
```

O integrar **después del pull** en `deploy-easynodeone-instance.sh`:

```bash
bash "${APP}/scripts/post_deploy_cleanup.sh" "${INST}"
```

---

## 5. Uso del script de limpieza

### Modo seguro (por defecto)

```bash
bash scripts/post_deploy_cleanup.sh staging
```

1. Borra rutas del **manifiesto** si aún existen.
2. Elimina **cachés Python** en `backend/`, `templates/`, `scripts/`, `docs/`, `static/` (excepto `static/uploads/`).

### Simulación

```bash
bash scripts/post_deploy_cleanup.sh staging --dry-run
```

### Todos los silos del host EN1

```bash
bash scripts/post_deploy_cleanup.sh all
```

Incluye dev, staging y relatic. **Prod** solo si:

```bash
export EASYNODEONE_DEPLOY_PROD_CONFIRM=YES
bash scripts/post_deploy_cleanup.sh all
```

### Limpieza Git adicional (opcional)

```bash
bash scripts/post_deploy_cleanup.sh staging --git-clean
```

Ejecuta `git clean -fd` con exclusiones: `static/uploads/`, `.env`, `instance/`, `venv/`, `backups/`, logs.

Activar en deploy completo:

```bash
EASYNODEONE_CLEANUP_GIT=YES sudo bash scripts/deploy_with_cleanup.sh staging
```

### IIUS (host dedicado)

```bash
cd /opt/easynodeone/app
git pull   # commit/tag acordado
bash scripts/post_deploy_cleanup.sh iius
sudo systemctl restart nodeone.service
```

---

## 6. Qué NO toca (protegido)

| Recurso | Motivo |
|---------|--------|
| `static/uploads/` | PDFs, logos, certificados emitidos |
| `/opt/easynodeone/<silo>/.env` | Fuera del árbol `app/`; secrets del silo |
| `instance/` (Flask) | Datos locales gitignored |
| `venv/` / `.venv/` | Entorno Python del silo |
| PostgreSQL | La limpieza es solo **filesystem** |
| Código versionado vigente | Solo elimina paths del manifiesto o cachés |

---

## 7. Manifiesto de rutas obsoletas

Archivo: [`scripts/deploy_cleanup_manifest.txt`](../scripts/deploy_cleanup_manifest.txt)

**Regla para IA y devs:** cuando un commit **elimine o mueva** archivos que pudieron quedar en silos por copia manual, añadir la ruta relativa a `app/` en ese manifiesto.

### Entradas actuales (ejemplo certificados, jun 2026)

| Ruta | Motivo |
|------|--------|
| `templates/my/event_certificates.html` | UI legacy unificada en `templates/certificates.html` |
| `backend/analytics.py` | Movido a `backend/scripts/archive/analytics_legacy.py` |
| `backend/create_certificate_tables.py` | Movido a `backend/scripts/archive/create_certificate_tables_legacy.py` |

Líneas con `#` son comentarios. Se admiten globs simples (ej. `*.pyc.bak`).

---

## 8. Relación con código muerto en el repo

| Situación | ¿Lo quita el deploy? |
|-----------|----------------------|
| Archivo borrado en Git y commiteado | **Sí** — con `git pull` desaparece del disco |
| Código muerto **dentro** de un `.py` que sigue en Git | **No** — requiere refactor y commit |
| Shim/legacy **intencional** (ej. `certificate_routes.py`) | **No** — sigue versionado |
| Resto manual en ruta del manifiesto | **Sí** — si se ejecuta `post_deploy_cleanup.sh` |

Ver refactor certificados: [`EN1_CERTIFICADOS_EVENTOS_CONTEXTO.md`](EN1_CERTIFICADOS_EVENTOS_CONTEXTO.md).

---

## 9. Checklist rápida (operador)

- [ ] Commit/tag acordado identificado
- [ ] `git pull` en el silo correcto
- [ ] `post_deploy_cleanup.sh <silo>` (o `deploy_with_cleanup.sh`)
- [ ] Migración/bootstrap si el release tocó modelos
- [ ] `systemctl restart` + `journalctl` sin errores
- [ ] Smoke test en URL del silo
- [ ] Si se eliminaron archivos en el release: ¿actualizado `deploy_cleanup_manifest.txt`?

---

## 10. Documentos relacionados

| Documento | Tema |
|-----------|------|
| [`CHECKLIST_ACTUALIZACION_Y_CLIENTES.md`](CHECKLIST_ACTUALIZACION_Y_CLIENTES.md) | Deploy y comunicación a clientes |
| [`REGLAS-DE-TRABAJO.md`](../REGLAS-DE-TRABAJO.md) | Solo dev manual; silos solo pull |
| [`EN1_CERTIFICADOS_EVENTOS_CONTEXTO.md`](EN1_CERTIFICADOS_EVENTOS_CONTEXTO.md) | Certificados evento (manifiesto parcial) |
| [`backend/docs/IIUS_RELEASE_MANIFEST.md`](../backend/docs/IIUS_RELEASE_MANIFEST.md) | Release IIUS |
| `/opt/easynodeone/scripts/deploy-easynodeone-instance.sh` | Deploy servidor (sin limpieza hasta integrar) |
