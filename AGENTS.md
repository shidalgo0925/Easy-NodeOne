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
2. ¿La edición es solo bajo `/opt/easynodeone/dev/app`?
3. ¿Migración o bootstrap? → Confirmar `DATABASE_URL` apunta a **PostgreSQL** del silo.
4. ¿Alcance mínimo? → Un mensaje = un cambio acotado.
5. ¿Commit/push? → Solo si lo pidió.

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
