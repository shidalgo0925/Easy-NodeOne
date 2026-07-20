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
| Limpieza post-deploy (silos + IIUS) | [`docs/EN1_DEPLOY_LIMPIEZA_CONTEXTO.md`](docs/EN1_DEPLOY_LIMPIEZA_CONTEXTO.md) |
| Roles RBAC | [`docs/RBAC_Y_ROLES.md`](docs/RBAC_Y_ROLES.md) |
| Eventos EN1 (módulo) | [`.cursor/rules/easynodeone-events-en1-plan.mdc`](.cursor/rules/easynodeone-events-en1-plan.mdc) |
| **Plataforma EN1 (Master Plan)** | [`docs/EN1_PLATFORM_MASTER_PLAN.md`](docs/EN1_PLATFORM_MASTER_PLAN.md) · carriles: [`docs/EN1_PLATFORM_CARRILES_Y_SOPORTE.md`](docs/EN1_PLATFORM_CARRILES_Y_SOPORTE.md) · Etapa 1: [`docs/EN1_PLATFORM_ETAPA1_CORE_APPS.md`](docs/EN1_PLATFORM_ETAPA1_CORE_APPS.md) · Sprint UX transición apps: [`docs/EN1_PLATFORM_SPRINT_UX_TRANSICION_APPS.md`](docs/EN1_PLATFORM_SPRINT_UX_TRANSICION_APPS.md) · **EPosOne V4:** [`docs/EN1_PLATFORM_EPOSONE_V4_ROADMAP.md`](docs/EN1_PLATFORM_EPOSONE_V4_ROADMAP.md) · [POS + licenciamiento](docs/EN1_PLATFORM_EPOSONE_V4_POS_LICENSING_ROADMAP.md) · [**Etapa 2 Android**](docs/EN1_PLATFORM_EPOSONE_V4_ANDROID_ETAPA2.md) · [**Hito EN1-01**](docs/EPOSONE_EN1_HITO1_PROVISIONING_CONTRACT.md) · [**Hito 2.5 Cajero**](docs/EPOSONE_EN1_HITO2_5_CASHIER_CONTRACT.md) · [**Handoff / dónde quedamos**](docs/EN1_EPOSONE_HANDOFF_STATUS.md) · [**ADR-006 Op/Admin**](docs/ADR-006-EPOSONE-OPERATION-VS-ADMIN.md) · [**Hito 3 Pedido**](docs/EN1_EPOSONE_HITO3_ORDER_LIFECYCLE.md) · [**Hito 3 Spec V1**](docs/EN1_EPOSONE_HITO3_SPEC_FUNCIONAL_V1.md) · [**V5 Roadmap**](docs/EN1_PLATFORM_EPOSONE_V5_ROADMAP.md) · [**EN1-POS V7 (producto)**](docs/EN1_POS_V7_ROADMAP.md) · [**Constitución**](docs/EN1_POS_CONSTITUCION_V1.md) · [**Domain Model**](docs/EN1_POS_DOMAIN_MODEL_V1.md) · [**DoD**](docs/EN1_POS_DEFINITION_OF_DONE_V1.md) · [**Gap capacidades**](docs/EN1_POS_CAPABILITY_GAP_V7.md) · [**Backlog V7**](docs/EN1_POS_BACKLOG_V7.md) · [**V6 contratos comerciales**](docs/EN1_PLATFORM_EPOSONE_V6_ROADMAP.md) · [**Modelo Comercial V1**](docs/EN1_EPOSONE_MODELO_COMERCIAL_V1.md) · [**Contrato Fiscal V1**](docs/EN1_EPOSONE_CONTRATO_FISCAL_V1.md) · [**Contrato Propinas V1**](docs/EN1_EPOSONE_CONTRATO_PROPINAS_V1.md) · [**Contrato Pagos V1**](docs/EN1_EPOSONE_CONTRATO_PAGOS_V1.md) · [**Contrato Recibo V1**](docs/EN1_EPOSONE_CONTRATO_RECIBO_V1.md) · [**Motor Comercial V1**](docs/EN1_EPOSONE_MOTOR_COMERCIAL_V1.md) · [**Motor Totales V1**](docs/EN1_EPOSONE_MOTOR_TOTALES_V1.md) · [**Infra Policy Engine**](docs/EN1_EPOSONE_COMMERCIAL_POLICY_ENGINE_INFRA_V1.md) · [**ADR-008**](docs/ADR-008-EPOSONE-COMMERCIAL-ENGINE.md) (Fase 5) · [**Order Domain Spec**](docs/EN1_EPOSONE_ORDER_DOMAIN_SPEC_V1.md) · [**Hito 3 HTTP Contract**](docs/EN1_EPOSONE_HITO3_ORDER_HTTP_CONTRACT.md) · ADR-001…005 ([licenciamiento POS](docs/ADR-005-EPOSONE-LICENSING-POS.md)) · sync: [`docs/EN1_PLATFORM_EPOSONE_V4_SYNC.md`](docs/EN1_PLATFORM_EPOSONE_V4_SYNC.md) · código: `backend/nodeone/core/eposone_domain/` · license: `backend/nodeone/core/license/` · Core Etapa 2: `backend/nodeone/core/platform/` |
| Protocolo legado (`??` / `go`) | [`md/.ai-protocol.md`](md/.ai-protocol.md) → sustituido por §1 de este archivo |

---

*Si hay conflicto entre docs, prevalece este `AGENTS.md` para la IA; para operación humana y legal del equipo, prevalece `REGLAS-DE-TRABAJO.md`.*
