# Reglas de trabajo — Easy NodeOne (Git y entornos)

Documento fijo para programadores y operación. Política **obligatoria** salvo acuerdo explícito por escrito del responsable del proyecto.

---

## Regla oficial (absoluta)

**Único punto de actualización manual del código:** `/opt/easynodeone/dev/app`

| Concepto | Dónde |
|----------|--------|
| Desarrollo y edición manual | **Solo** `dev/app` |
| Historial y distribución del código | **Git** (remoto) |
| Staging, prod, relatic | **Solo** consumen con `git pull` + despliegue; **no** se desarrolla ahí |

**Frase exacta para el equipo:**

> El único punto autorizado para desarrollo y actualización manual del código es `/opt/easynodeone/dev/app`.  
> Las carpetas **staging**, **prod** y **relatic** no deben modificarse manualmente.  
> Esos entornos solo se actualizan mediante **`git pull`** desde el repositorio remoto, seguido de sus pasos de despliegue correspondientes (dependencias, migraciones, reinicio de servicio).

En una línea: **un solo punto manual (DEV), un solo distribuidor (GIT), el resto solo hace pull.**

---

## Qué implica “solo DEV”

En **`/opt/easynodeone/dev/app`** es el **único** entorno donde se puede:

- modificar código  
- crear o borrar archivos del proyecto  
- ajustar plantillas y estáticos versionados  
- cambiar lógica de negocio  
- probar el desarrollo (contra la BD y el servicio de **dev**)  
- crear **commits** y hacer **push** al remoto  

**Git no es “la carpeta dev”.** Git es el historial central. `dev/app` es donde nace el trabajo; el remoto es la fuente de verdad compartida.

---

## Staging, prod y relatic — sin desarrollo manual

No se programa ahí. Solo reciben el código ya versionado.

### Staging

```bash
cd /opt/easynodeone/staging/app
git pull origin main
```

Luego: instalar dependencias si aplica, migraciones / DDL si aplica, reiniciar servicio, validar.

**Importante:** si el servicio no arranca tras el pull, revisar `journalctl` del unit: a menudo es **esquema PostgreSQL desalineado** (columnas nuevas). Detalle y checklist en [`docs/CHECKLIST_ACTUALIZACION_Y_CLIENTES.md`](docs/CHECKLIST_ACTUALIZACION_Y_CLIENTES.md) → *Lecciones*.

### Prod

Solo después de aprobar staging:

```bash
cd /opt/easynodeone/prod/app
git pull origin main
```

Luego: migraciones / DDL si aplica, reinicio, verificación (y `journalctl` si el reinicio falla). Misma guía *Lecciones* en el checklist de despliegue.

### Relatic

Igual; sin tocar código a mano:

```bash
cd /opt/easynodeone/relatic/app
git pull origin main
# o, si existe política explícita: git pull origin relatic
```

---

## Prohibido en staging, prod y relatic

- Editar archivos del proyecto con editor (`nano`, `vim`, IDE apuntando a esas carpetas para **cambiar código**).  
- Copiar archivos desde `dev` (ni `scp`, ni pegar, ni rsync de código fuente).  
- Subir archivos manualmente para “parchar”.  
- Dejar cambios locales **no commiteados** como arreglo rápido.  
- Arreglar bugs o features **directo en producción** (u homólogo staging/relatic).  

Si algo urge: se reproduce en **dev**, se corrige, se commitea, se pasa por el flujo y recién entonces **pull** en el entorno correspondiente.

---

## Flujo correcto

```text
DEV → commit → push a Git → pull en STAGING → validar → pull en PROD
                                              └──→ pull en RELATIC cuando aplique
```

No hay sincronización **entre** carpetas: staging no “toma” de dev por copia; todos toman del **mismo remoto** con `git pull`.

---

## Política de ramas (obligatoria)

| Ubicación | Rama |
|-----------|--------|
| `dev/app` | **`develop`** |
| `staging/app` | **`main`** |
| `prod/app` | **`main`** |
| `relatic/app` | **`main`**, o **`relatic`** solo si hay diferencias reales y acordadas |

Así queda explícito: el trabajo nace en **dev** sobre **`develop`**, se integra a **`main`** cuando corresponda, y **staging/prod/relatic** consumen **`main`** (o la rama relatic acordada).

### En dev (commit y push)

```bash
cd /opt/easynodeone/dev/app
git add .
git commit -m "mensaje claro del cambio"
git push origin develop
# Merge a main cuando el equipo apruebe despliegue a staging/prod.
```

---

## Cuatro silos en el servidor (recordatorio)

No existen “cuatro carpetas en Git”. Hay **un repositorio remoto** y **cuatro checkouts**:

| Ruta | Rol | Puerto |
|------|-----|--------|
| `/opt/easynodeone/dev/app` | Desarrollo | 9101 |
| `/opt/easynodeone/staging/app` | Validación | 9104 |
| `/opt/easynodeone/prod/app` | Producción | 9102 |
| `/opt/easynodeone/relatic/app` | Relatic | 9103 |

Cada silo tiene su propio `.env`, `venv/`, base de datos y servicio systemd.

---

## Qué sí va a Git

Código Python, templates, estáticos del proyecto, migraciones, scripts del repo, documentación técnica del repositorio.

## Qué no debe ir a Git

`.env`, secretos, `venv/`, `logs/`, `uploads/`, dumps, temporales. Respetar `.gitignore`.

---

## Conclusión

- **Un solo punto manual:** `/opt/easynodeone/dev/app`.  
- **Un solo distribuidor del código versionado:** Git.  
- **Staging, prod y relatic:** solo `git pull` + pasos de despliegue; **ninguna** edición manual del árbol del proyecto.

---

## Documentos relacionados

- **Checklist al desplegar y al comunicar a clientes:** [`docs/CHECKLIST_ACTUALIZACION_Y_CLIENTES.md`](docs/CHECKLIST_ACTUALIZACION_Y_CLIENTES.md)
