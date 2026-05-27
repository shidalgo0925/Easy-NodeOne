# IIUS — congelamiento de producto (2026-05-27)

Documento de referencia del **freeze** operativo en el host IIUS. La línea viva de IIUS en Git es la rama **`iius-product`**, no `develop` ni `main`.

---

## Punto de congelamiento

| Campo | Valor |
|-------|--------|
| Host | `vmi3215083` |
| Dominio Apps | `https://apps.internationalinstitute.us` |
| Rama Git | **`iius-product`** |
| Commit freeze | **`5a230e2`** — `chore(iius): freeze current IIUS product state` |
| Tag de seguridad | **`iius-freeze-20260527`** |
| Base anterior | Tag **`iius-go-20260522`** → commit **`9330cfc`** |
| Remoto | `git@github.com:shidalgo0925/Easy-NodeOne.git` |

---

## Backup completo (fuera de Git)

**Directorio:** `/opt/easynodeone/backups/iius-freeze-20260527_025810`

| Archivo / carpeta | Contenido |
|-------------------|-----------|
| `app.env` | Copia de `/opt/easynodeone/app/.env` |
| `instance/` | SQLite (`NodeOne.db`, oauth, logs) |
| `static-uploads.tgz` | `static/uploads/` (~95 MB) |
| `app-git-tree.tgz` | Árbol `/opt/easynodeone/app` sin `.venv`, `instance/`, uploads |
| `wordpress.tgz` | `/var/www/wordpress` (~1.5 GB) |
| `moodle.tgz` | Intento Moodle (revisar permisos si está vacío) |

**No versionar en Git:** `.env`, `instance/*.db`, `static/uploads/`, `.venv/`.

---

## Runtime en el momento del freeze

| Área | Estado |
|------|--------|
| Servicio | `nodeone.service` → Gunicorn `127.0.0.1:8000` |
| WorkingDirectory | `/opt/easynodeone/app/backend` |
| EnvironmentFile | `/opt/easynodeone/app/.env` |
| BD | SQLite `/opt/easynodeone/app/instance/NodeOne.db` |
| Org tenant | `1` — International Institute US (`subdomain=iius`) |
| Política registro | `academic_closed` |
| Branding | `NODEONE_BRAND_PRESET=iius` |

---

## Qué incluye el commit freeze (`5a230e2`)

- WIP local sobre `9330cfc`: sync WP, catálogo `/programas`, landings `/inscripcion`, eventos, PDF leads, política de acceso, UI checkout/landings.
- **108 archivos** (+13 932 / −336 líneas).
- Scripts `*_iius_*`, módulos `wp_*_sync`, `catalog_public`, `inscripcion_bridge`, etc.

**Pendiente de implementar** (post-freeze, solo en `iius-product`): recursos descargables `AcademicProgramResource`, separación `/opt/iius/{dev,staging,prod}`.

---

## Política de ramas

| Línea | Rama | Regla |
|-------|------|--------|
| **IIUS** | `iius-product` | Todo desarrollo IIUS aquí |
| **EN1** | `develop` → `main` | Sin merge completo desde IIUS |
| Integración | Cherry-pick selectivo | Solo fixes acordados en ambas direcciones |

**Prohibido para IIUS:**

- Trabajar en detached HEAD sobre `iius-go-20260522` con cambios locales sin commit.
- `git pull` de `develop`/`main` sobre producción IIUS sin acuerdo.
- Editar `/var/www/nodeone` creyendo que es el runtime IIUS (Gunicorn usa `/opt/easynodeone/app`).

---

## Comandos de recuperación

Checkout del freeze en un clon limpio:

```bash
git fetch origin
git checkout iius-product
# o punto exacto:
git checkout iius-freeze-20260527
```

Restaurar datos operativos desde backup (ejemplo):

```bash
cp /opt/easynodeone/backups/iius-freeze-20260527_025810/app.env /opt/easynodeone/app/.env
cp -a /opt/easynodeone/backups/iius-freeze-20260527_025810/instance /opt/easynodeone/app/
tar -xzf /opt/easynodeone/backups/iius-freeze-20260527_025810/static-uploads.tgz -C /opt/easynodeone/app/static
sudo systemctl restart nodeone.service
```

---

## Documentos relacionados

- `IIUS_DEV_HANDOFF.md` — handoff release mayo 2026
- `IIUS_GO_CHECKLIST.md` — checklist operativo
- `IIUS_CATALOGO_SITIO_Y_SLUGS_ANALISTA.md` — catálogo y slugs
- `REGLAS-DE-TRABAJO.md` (raíz repo) — política EN1 multi-silo (IIUS usa `iius-product` como excepción acordada)

---

*Generado al cerrar el freeze 2026-05-27. Actualizar este archivo solo en commits explícitos de hitos IIUS.*
