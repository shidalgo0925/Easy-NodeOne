# Plan operativo — Release 3.0.1 (Git como única fuente de verdad)

**Promoción obligatoria:** DEV → STAGING → PROD → RELATIC → SPAGETTI

**Contexto:** El entorno DEV es el referente funcional correcto. Este plan convierte ese estado en una **release formal 3.0.1** y despliega **exactamente esa versión** en todos los entornos, **sin divergencias**.

---

## Objetivo

Convertir el estado actual de DEV en una release formal **3.0.1** y desplegar **exactamente esa versión** en todos los entornos, sin divergencias.

---

## Reglas (no negociables)

1. **No desplegar “lo último de dev”.** Solo se despliega una release identificada: **3.0.1** (referencia Git: **v3.0.1**).
2. **Una sola fuente de verdad: Git.** Nada de parches manuales en servidores que no estén en el repo.
3. **Mismo código, distinta configuración:** `.env`, dominios, claves y DB son **por entorno**.
4. **Orden de promoción obligatorio:** **DEV → STAGING → PROD → RELATIC → SPAGETTI**.
5. **Rollback posible:** Cada despliegue debe permitir volver a la versión anterior.

---

## Fase 1 — Validar que DEV es la verdad

En **DEV**:

- Confirmar que todo lo que “funciona” está **commiteado**.
- Verificar:
  - `git status` → limpio o cambios **conocidos y explícitos** (no sorpresas).
  - No depender de archivos **fuera del repo** (plantillas, fixes manuales, etc.).
- Confirmar versión actual: archivo **`VERSION`** (hoy **3.0**).

**Resultado esperado:** El estado funcional de DEV está **completamente en Git**.

---

## Fase 2 — Crear release 3.0.1

En el **repo**:

- Actualizar **`VERSION`** → **`3.0.1`**.
- **Commit** de release, mensaje tipo: `release: 3.0.1`.
- Crear **tag:** **`v3.0.1`** apuntando a ese commit.
- **Subir a GitHub:** commit + tag (`git push origin <rama>` y `git push origin v3.0.1`).

**Resultado esperado:** Una referencia única y clara: **`v3.0.1` = este commit exacto**.

---

## Fase 3 — Matriz de entornos

Para **cada** entorno definir:

| Tipo | Dónde vive |
|------|------------|
| **Variables por entorno (no en Git)** | `.env`, DB (nombre/credenciales), dominios, claves API, correo, rutas de media/uploads |
| **Código (sí en Git)** | `backend/`, módulos, `templates`, assets, migraciones, `VERSION` |

---

## Fase 4 — Despliegue a STAGING

**Objetivo:** Probar la release **3.0.1** antes de tocar productivo.

**Qué hacer:**

- Traer **exactamente** **`v3.0.1`** (no `develop`, no “lo último” sin tag).
- Mantener **su `.env` propio**.

**Validaciones mínimas:** login, sesión/organización, dashboard, módulos críticos, creación/edición, carga de assets, permisos, errores en logs.

**Si falla → no pasa a PROD.**

---

## Fase 5 — Despliegue a PROD

Solo si **STAGING** está OK.

- Desplegar la **misma** versión **`v3.0.1`**.
- No recompilar/desplegar cosas distintas al tag.
- No modificar código manualmente en el servidor.

**Validar:** versión visible **3.0.1**, servicio arranca, sin errores críticos.

---

## Fase 6 — Despliegue a RELATIC

RELATIC = entorno **controlado** (puede tener branding/config distinta, módulos distintos, lógica específica).

**Regla:** mismo **core `v3.0.1`**, **config propia** (`.env`).

**Validar:** flujos propios de RELATIC, permisos, UI/branding.

---

## Fase 7 — Despliegue a SPAGETTI (aislado)

SPAGETTI = instalación **independiente**.

Debe tener: repo propio (o clon), DB propia, `.env` propio, servicio (systemd) propio, dominio/subdominio propio.

**Regla:** no depender de PROD ni RELATIC.

**Resultado esperado:** SPAGETTI corre **3.0.1** de forma **autónoma**.

---

## Fase 8 — Control post-despliegue

En **todos** los entornos: confirmar versión **3.0.1**, revisar logs, validar funcionalidad crítica, assets y rutas, permisos.

---

## Fase 9 — Preparar siguiente ciclo

Tras liberar **3.0.1**:

- DEV vuelve a abrirse para cambios nuevos.
- Siguiente versión: **3.0.2** (fixes) o **3.1.0** (mejoras), según alcance.

---

## Riesgos a controlar

- Cambios no commiteados en DEV.
- Archivos fuera de Git (media, plantillas tocadas a mano).
- Diferencias de `.env` entre entornos.
- Migraciones de base de datos.
- Servicios apuntando a carpetas incorrectas.
- Caché (Cloudflare / navegador).
- Builds o assets no regenerados.
- Logs con errores ocultos.

---

## Definición clave

A partir de ahora:

- **No** se despliega “lo último de dev”.
- Se despliega **la versión `v3.0.1`** (commit etiquetado en Git).

---

## Resumen ejecutivo para el programador

1. DEV es correcto → convertirlo en release **3.0.1**.
2. Versionar en Git (**commit + tag `v3.0.1`**).
3. Desplegar primero a **STAGING**, validar.
4. Promover la **misma** versión a **PROD**.
5. Replicar a **RELATIC** y **SPAGETTI** con su **config propia**.
6. Nunca modificar código directamente en servidores.
7. Mantener **Git** como única fuente de verdad.

---

## Próximos pasos inmediatos (orden sugerido)

1. **Fase 1 en máquina/repo de trabajo:** `git status`, revisar diff, commitear o descartar todo lo necesario hasta que “lo que debe ir a release” esté en Git.
2. **Fase 2:** editar `VERSION` a `3.0.1`, commit `release: 3.0.1`, `git tag -a v3.0.1 -m "release 3.0.1"`, push de rama + `git push origin v3.0.1`.
3. **Fase 4 (STAGING):** checkout del tag `v3.0.1` (o merge explícito de ese commit), **sin** tocar `.env` con secretos del repo; reiniciar servicio; ejecutar checklist de validación.
4. Si STAGING OK → **Fase 5 (PROD)** con el mismo commit/tag; anotar hash previo para rollback.
5. En paralelo o después: **RELATIC** y **SPAGETTI** con misma etiqueta y configs aislados.
6. **Fase 8:** verificación cruzada de versión en UI/logs y monitoreo breve.
