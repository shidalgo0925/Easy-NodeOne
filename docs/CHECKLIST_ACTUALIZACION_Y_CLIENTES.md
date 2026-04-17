# Checklist: despliegue y comunicación a clientes

Documento para **consultar en cada actualización** que llegue a clientes (o a sus entornos).  
Complementa la política técnica de [`REGLAS-DE-TRABAJO.md`](../REGLAS-DE-TRABAJO.md) (solo desarrollo en dev, Git como fuente, pull por silo).

---

## Antes de tocar código

**Antes de tocar código**, leé [`REGLAS-DE-TRABAJO.md`](../REGLAS-DE-TRABAJO.md) en la raíz del repo (`/opt/easynodeone/dev/app`): único punto de edición manual, ramas (`develop` / `main`), prohibiciones en staging/prod/relatic y flujo Git.

---

## Norma: desplegar solo versión acordada (tag o commit)

Esta norma aplica a **staging**, **prod** y **relatic** (cualquier silo que no sea `dev/app`).

1. **No** actualizar contra “lo último de `develop`” ni hacer `git pull` a ciegas sin saber **qué revisión** queda en el servidor.
2. Cada despliegue va contra un **tag** (p. ej. `v3.0.2`) o **commit** explícito que te indiquen. Si no te pasan referencia, **parar** y pedirla antes de tocar el silo.
3. Flujo típico: `git fetch origin --tags` y luego dejar el checkout en el **tag** o **commit** acordado (p. ej. `git checkout vX.Y.Z`, o avanzar `main` con merge/`--ff-only` hasta ese commit, según procedimiento del equipo).
4. **No** machacar `.env` ni secretos con el repo: solo código desde Git; configuración **por entorno** local al silo.

**Frase para el equipo:** *Solo se despliega el tag o el commit que te den; nunca “el último de develop” sin etiqueta.*

Detalle de release (ejemplo operativo): [`PLAN_RELEASE_3.0.1_OPERACION.md`](PLAN_RELEASE_3.0.1_OPERACION.md).

---

## Antes de tocar producción

1. **Código** mergeado y pusheado según el flujo acordado (p. ej. `develop` → `main`) y **referencia de despliegue** acordada (tag o commit).
2. **Staging** actualizado en `staging/app` **al commit/tag acordado** (`git fetch`, luego checkout/merge según procedimiento), dependencias y **migraciones** aplicadas si corresponde, **servicio reiniciado**.
3. **Validación en staging** hecha (flujos críticos que usan los clientes afectados).
4. Anotar **commit o tag** que vas a llevar a prod (para rastreo y rollback mental).

## Al actualizar prod (y relatic si aplica)

1. Ventana acordada (si los clientes son sensibles al downtime).
2. En `prod/app` (y `relatic/app` si toca): `git pull` al commit/tag acordado.
3. **Migraciones** si hubo cambios de esquema.
4. **Reinicio** del servicio systemd correspondiente.
5. **Verificación mínima** (login, pantalla clave, API crítica).
6. Registrar en tu bitácora interna: **fecha**, **entorno**, **commit**, **quién**.

## Antes de avisar a clientes

- Confirmar que **prod** (y otros entornos que usen) está estable tras el reinicio.
- Tener claro **qué cambió en lenguaje de negocio** (no hace falta tecnicismos).
- Definir **si hay acción requerida** por parte del cliente (cambiar contraseña, nueva URL, etc.).

## Plantilla breve para el mensaje al cliente

Puedes copiar y completar:

```text
Asunto: Actualización del sistema [nombre producto / Easy NodeOne] – [fecha]

Hemos publicado una actualización con las siguientes mejoras o correcciones:
- [punto 1, beneficio claro]
- [punto 2]

[Si aplica] Deben [acción concreta].
[Si no aplica] No necesitan hacer nada especial.

Si notan algún inconveniente, [canal de soporte acordado].
```

## Dónde guardar el texto “para clientes”

- Para **comunicados largos o histórico**: podés usar `docs/root/` con nombre fechado, p. ej. `ANUNCIO_ACTUALIZACION_YYYY-MM-DD.md`, o el proceso que ya usen para anuncios.
- Este archivo (**`docs/CHECKLIST_ACTUALIZACION_Y_CLIENTES.md`**) es la **checklist fija**; los anuncios concretos pueden ser archivos aparte por release.

## Resumen en una frase

**No avisar a clientes hasta** que staging esté validado, prod actualizado y verificado; **dejar escrito** qué versión salió y qué les comunicaste.

---

## Lecciones (para que no vuelva a pasar)

### 1. “En dev se ve distinto que en staging/prod”

- **Causa:** cambios **solo en el disco de `dev/app`**, sin **commit + push** a Git (y merge a `main` si el silo consume `main`).
- **Regla:** lo que no está en el remoto **no existe** para staging/prod. Reiniciar servicios **no** copia trabajo local.
- **Check:** antes de desplegar, `git status` limpio en dev y el commit deseado en `origin/main`.

### 2. “`git pull` + reinicio y el servicio no arranca” (`UndefinedColumn`, etc.)

- **Causa:** el **código (modelos SQLAlchemy)** ya espera columnas/tablas nuevas, pero **PostgreSQL del silo** aún no las tiene. El unit suele ejecutar `bootstrap_nodeone.py` en `ExecStartPre`; si falla ahí, Gunicorn no levanta.
- **Qué hacer:**
  - Ver log: `journalctl -u easynodeone-<silo>.service -n 80 --no-pager`.
  - Si aparece **`column ... does not exist`**: aplicar el **DDL / bootstrap** que corresponda al cambio (en el repo suele haber funciones idempotentes llamadas desde `bootstrap_nodeone_schema` en `app.py`), o ejecutar el script/migración documentado para ese release.
  - Volver a **reiniciar** el servicio y confirmar `active (running)`.
- **Prevención:** en releases con **cambios de modelo**, asumir siempre **paso explícito de esquema** además del pull (aunque muchas veces lo cubra el bootstrap; hay que **verificar el primer arranque** tras el deploy).

### 3. Orden del bootstrap

- Hubo un caso donde se consultaba `saas_organization` **antes** de crear columnas fiscales en BD, y el arranque fallaba. En código quedó corregido el **orden** del DDL en `bootstrap_nodeone_schema` (fiscal / facturas / CRM **antes** de lógica que carga orgs).
- **Regla general:** al añadir columnas a tablas que el **bootstrap o el arranque** lean enseguida, el **DDL idempotente** debe ejecutarse **antes** de esa lectura.

### 4. Checklist mínima tras cada deploy en un silo

1. `git pull` al commit acordado.  
2. `pip install` solo si cambió `requirements.txt` / lock.  
3. **Reinicio** del servicio.  
4. **`systemctl status`** + **últimas líneas de `journalctl`** (confirmar `ExecStartPre` OK).  
5. Prueba rápida en UI (login + una pantalla tocada por el release).
