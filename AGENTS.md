# AGENTS.md — leer primero (IA y programadores)

**Único punto de entrada** para reglas de Easy NodeOne. Antes de editar código, migrar BD o desplegar: leé este archivo completo.

Detalle operativo humano: [`REGLAS-DE-TRABAJO.md`](REGLAS-DE-TRABAJO.md). Despliegue a clientes: [`docs/CHECKLIST_ACTUALIZACION_Y_CLIENTES.md`](docs/CHECKLIST_ACTUALIZACION_Y_CLIENTES.md).

---

## 1. Protocolo con el usuario (obligatorio para IA)

| Señal | Acción |
|-------|--------|
| Sin **GO** / sin pedido explícito | Solo leer, explicar o proponer. **No** editar archivos ni ejecutar comandos destructivos. |
| **??** | Analizar opciones. **No** ejecutar nada. |
| **GO** (o «implementa X») | Ejecutar **solo** lo pedido en ese mensaje. Nada extra (ni docs, ni refactors, ni «mejoras»). |
| Commit / push / PR | **Solo** si el usuario lo pide explícitamente. |

**Prohibido para la IA:** asumir alcance, tocar staging/prod/relatic, crear `.md` no pedidos, commitear por iniciativa propia.

### Ciclo por chat (1 chat = 1 tarea)

Cada conversación cubre **una sola tarea** de punta a punta:

```text
Plan → Cambios → Review → Commit → Push → Cerrar chat → Chat nuevo
```

| Fase | IA | Usuario |
|------|-----|---------|
| **Plan** | Alcance, archivos, riesgos, criterio de hecho. **Sin editar.** | Describe la tarea (o `??` solo opciones) |
| **Cambios** | Implementa **solo** lo acordado en el plan | **GO** / «implementa X» |
| **Review** | Resume diff, riesgos, qué probar | Feedback o OK |
| **Commit** | `git add` + commit con mensaje claro | «commit» explícito |
| **Push** | `git push origin develop` | «push» explícito |
| **Cerrar** | Confirma que la tarea quedó cerrada | Abre **chat nuevo** para la siguiente tarea |

**Reglas del ciclo:** no mezclar tareas en un mismo chat; no pasar a **Cambios** sin plan acordado; al cerrar, working tree limpio o cambios ya commiteados y pusheados.

---

## 2. Entornos y Git

| Regla | Valor |
|-------|--------|
| **Única ruta de edición manual** | `/opt/easynodeone/dev/app` |
| Rama en dev | `develop` |
| Staging / prod / relatic | Solo `git pull` + deps + migraciones + reinicio. **Prohibido** editar o copiar código ahí. |
| Ramas en silos | staging, prod, relatic → `main` (relatic: `relatic` solo si está acordado) |
| Flujo | dev → commit → push → pull staging → validar → pull prod / relatic |

| Silo | Ruta | Puerto |
|------|------|--------|
| dev | `/opt/easynodeone/dev/app` | 9101 |
| staging | `/opt/easynodeone/staging/app` | 9104 |
| prod | `/opt/easynodeone/prod/app` | 9102 |
| relatic | `/opt/easynodeone/relatic/app` | 9103 |

Cada silo: su `.env`, `venv/`, PostgreSQL y unit systemd. **No** sincronizar carpetas entre silos; todos tiran del **mismo remoto Git**.

Despliegue fuera de dev: **tag o commit explícito** acordado — nunca «lo último de develop» a ciegas.

### Modo estricto — solo Dev EN1 (obligatorio para IA)

**Dev EN1** es el único entorno de trabajo. Todo lo demás queda fuera de alcance salvo que el usuario lo pida **explícitamente** en ese chat.

| Concepto | Dev EN1 (único permitido) |
|----------|---------------------------|
| Silo | `dev` |
| Código | `/opt/easynodeone/dev/app` |
| Rama Git | `develop` |
| `.env` / `DATABASE_URL` | `/opt/easynodeone/dev/.env` → `easynodeone_dev` @ `127.0.0.1:5432` |
| Servicio systemd | `easynodeone-dev` |
| URL | `https://appdev.easynodeone.com` |
| Puerto | `9101` |

**Permitido:** editar código, migrar/bootstrap, reiniciar servicio, probar y commitear **solo** en Dev EN1.

**Prohibido sin GO explícito del usuario:**

- Editar, copiar o ejecutar en `/opt/easynodeone/staging`, `prod` o `relatic`.
- `git pull`, despliegue, migraciones o `systemctl` en silos que no sean `dev`.
- DDL o consultas contra BD distinta de `easynodeone_dev`.
- Asumir despliegue a appprd, staging o relatic al cerrar una tarea.

Si la tarea requiere otro silo, el usuario debe decirlo en el **Plan** de ese chat; si no, la IA se limita a Dev EN1.

---

## 3. Base de datos — PostgreSQL (no SQLite)

| Entorno | `DATABASE_URL` |
|---------|----------------|
| dev | `/opt/easynodeone/dev/.env` → `easynodeone_dev` @ `127.0.0.1:5432` |
| otros silos | `/opt/easynodeone/<silo>/.env` |

- **Runtime (Gunicorn):** systemd carga el `.env` del **silo**, no `dev/app/.env`.
- **Bootstrap y migraciones:** deben cargar el mismo `.env` del silo (`bootstrap_nodeone.py`, `wsgi.py` ya lo hacen). Si no, DDL cae en SQLite y PG queda desalineado.
- SQLite (`instance/NodeOne.db`) = solo desarrollo local **sin** `DATABASE_URL`. **No** usar en servidores.
- DDL nuevo: aplicar en **PostgreSQL** del silo. Si el rol de app no es owner de la tabla → `psql` como superusuario.

---

## 4. Checklist antes de actuar (IA)

1. ¿El usuario dio **GO** o pidió explícitamente el cambio?
2. ¿Modo estricto? → ¿Todo es **solo Dev EN1** (§2)? Si no, parar y pedir aclaración.
3. ¿La edición es solo bajo `/opt/easynodeone/dev/app`?
4. ¿Migración o bootstrap? → Confirmar `DATABASE_URL` apunta a **`easynodeone_dev`** (`/opt/easynodeone/dev/.env`).
5. ¿Alcance mínimo? → Un mensaje = un cambio acotado; **1 chat = 1 tarea** (ver §1).
6. ¿Commit/push? → Solo si lo pidió.
7. ¿Es otra tarea distinta? → Cerrar chat y abrir uno nuevo; no acumular en la misma conversación.

---

## 5. Git — qué no commitear

No subir: `.env`, secretos, `venv/`, `logs/`, `uploads/`, dumps. Respetar `.gitignore`.

---

## 6. Documentos de detalle (no duplicar aquí)

| Tema | Archivo |
|------|---------|
| Reglas completas equipo | [`REGLAS-DE-TRABAJO.md`](REGLAS-DE-TRABAJO.md) |
| Despliegue y clientes | [`docs/CHECKLIST_ACTUALIZACION_Y_CLIENTES.md`](docs/CHECKLIST_ACTUALIZACION_Y_CLIENTES.md) |
| Roles RBAC | [`docs/RBAC_Y_ROLES.md`](docs/RBAC_Y_ROLES.md) |
| Eventos EN1 (módulo) | [`.cursor/rules/easynodeone-events-en1-plan.mdc`](.cursor/rules/easynodeone-events-en1-plan.mdc) |
| Protocolo legado (`??` / `go`) | [`md/.ai-protocol.md`](md/.ai-protocol.md) → sustituido por §1 de este archivo |

---

*Si hay conflicto entre docs, prevalece este `AGENTS.md` para la IA; para operación humana y legal del equipo, prevalece `REGLAS-DE-TRABAJO.md`.*
