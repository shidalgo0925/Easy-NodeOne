# EasyNodeOne Platform — Carriles y soporte operativo

Complemento operativo del [`EN1_PLATFORM_MASTER_PLAN.md`](EN1_PLATFORM_MASTER_PLAN.md).

Define **dónde se hace cada cambio** para no quedar parados ni romper IIUS/Relatic.

---

## Los tres carriles

```text
┌─────────────────────────────────────────────────────────────────┐
│ CARRIL 1 — Producción                                           │
│ Silos: prod (IIUS), relatic                                     │
│ Git: tag congelado + rama release/*-maint                       │
│ Entra: hotfixes críticos, soporte, incidencias                  │
│ No entra: refactor, features plataforma, develop                │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ CARRIL 2 — Plataforma                                           │
│ Silo: dev (appdev), staging plataforma cuando exista            │
│ Git: develop (futuro: platform/* si hace falta)                 │
│ Entra: Core, Registry, Launcher, Shell, EPosOne, apps nativas   │
│ No entra: deploy directo a IIUS/Relatic                         │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ CARRIL 3 — Integración                                          │
│ Silo: staging con perfil cliente (IIUS o Relatic)                │
│ Git: develop + flags app_runtime por org                        │
│ Entra: cutover de UNA app (EMembership, ECRM, …)                │
│ No entra: migración completa de cliente                         │
└─────────────────────────────────────────────────────────────────┘
```

---

## Etapa 0 — Congelación (acciones)

### IIUS

| Item | Valor |
|------|-------|
| Tag congelado | `iius-freeze-20260527` |
| Tag release previo | `iius-go-20260522` |
| Rama mantenimiento | `release/iius-maint` (desde tag congelado) |
| Smoke test | `cd backend && bash scripts/go_iius_validate_all.sh` |
| Manifiesto | `backend/docs/IIUS_RELEASE_MANIFEST.md` |

**Crear rama de mantenimiento (una vez):**

```bash
cd /opt/easynodeone/dev/app
git fetch origin --tags
git checkout -b release/iius-maint iius-freeze-20260527
# push solo cuando el equipo lo pida explícitamente
```

### Relatic

| Item | Valor |
|------|-------|
| Tag congelado | **Pendiente:** `relatic-freeze-YYYYMMDD` |
| Acción | En silo `relatic/app`: `git describe --tags` o `git rev-parse HEAD` → documentar commit → crear tag anotado en dev desde ese commit |
| Rama mantenimiento | `release/relatic-maint` (desde tag congelado) |
| Smoke test | Login, CRM, membresía, certificados evento, portal usuario (checklist Relatic) |

**No editar** `/opt/easynodeone/relatic/app` manualmente. El tag se crea en `dev/app` apuntando al commit que Relatic ejecuta hoy.

---

## Flujo hotfix (Carril 1)

```text
1. Ticket: app + cliente + severidad crítica
2. Confirmar tag en silo: git describe --tags
3. Rama desde tag: release/<cliente>-maint
4. Fix mínimo (sin refactor colindante)
5. Smoke test del cliente
6. Tag nuevo: <cliente>-hotfix-YYYYMMDD
7. Deploy solo ese silo (tag explícito)
8. Opcional: cherry-pick a develop si aplica a plataforma
```

**Prohibido en hotfix:** mezclar con trabajo de Launcher, Core o EPosOne en el mismo commit.

---

## Flujo plataforma (Carril 2)

```text
1. Ticket: componente Core / App nativa / Registry
2. Rama desde develop (o feature/*)
3. Desarrollo + pruebas en appdev (:9101)
4. Merge a develop
5. Deploy solo dev/staging plataforma — NUNCA prod/relatic sin cutover de app
```

---

## Flujo integración (Carril 3)

```text
1. App declarada "lista" (criterios Master Plan Etapa 5)
2. Staging con org IIUS o Relatic (datos de prueba o copia acordada)
3. Flag: app_runtime=plataforma para ESA app en ESA org
4. Validación funcional + sign-off
5. Ventana prod: cutover solo esa app
6. Resto de apps del cliente siguen Legacy
```

---

## Matriz org × app × estado (ejemplo IIUS)

| App | Estado hoy | Carril para cambios hoy |
|-----|------------|-------------------------|
| EMembership | Legacy | 1 |
| EEvents | Legacy | 1 |
| ECertificates | Legacy | 1 |
| EAppointments | Legacy | 1 |
| Academic | Legacy | 1 |
| EPosOne | — (no aplica) | 2 cuando exista |

Cuando EMembership pase a Plataforma para IIUS, nuevas features de membresía van al carril 2; urgencias en prod legacy solo hasta fecha de retiro acordada.

---

## Plantilla de ticket

Copiar en cada issue / chat de trabajo:

```text
Cliente:     IIUS | Relatic | Plataforma (dev)
App:         EMembership | ECertificates | Core | EPosOne | …
Estado app:  Legacy | en_migracion | plataforma
Carril:      1 | 2 | 3
Tag base:    (si carril 1) ej. iius-freeze-20260527
¿Hotfix?:    sí / no
Criterio done: (smoke test concreto)
```

---

## Pregunta rápida: “¿Dónde hago este cambio?”

| Pregunta | Respuesta |
|----------|-----------|
| IIUS pide nuevo tipo de certificado y ECertificates está Legacy | **Carril 1** — hotfix desde tag IIUS |
| Mismo caso pero ECertificates ya Plataforma para IIUS | **Carril 2** — código plataforma + deploy cutover ya hecho |
| Construir Launcher | **Carril 2** |
| Probar EMembership nueva para IIUS antes de prod | **Carril 3** staging |
| Bug en appdev mientras construís EPosOne | **Carril 2** (no afecta IIUS si Etapa 0 se respeta) |
| ¿Puedo hacer git pull develop en relatic? | **No** — solo tag acordado |

---

## Reglas de deploy (recordatorio)

- Prod / Relatic: **solo tag o commit explícito** ([`CHECKLIST_ACTUALIZACION_Y_CLIENTES.md`](CHECKLIST_ACTUALIZACION_Y_CLIENTES.md)).
- Dev: `develop` libre para plataforma.
- Tras pull en silo cliente: `bash app/scripts/post_deploy_cleanup.sh <silo>` si aplica.

---

## Lección certificados (2026)

Refactor amplio en `develop` (módulo certificates) rompió rutas PDF membresía; se corrigió en develop. **IIUS/Relatic no debieron recibir ese refactor** hasta integración explícita de ECertificates.

**Política:** cambios de arquitectura en módulos compartidos van a carril 2; clientes en Legacy solo reciben parches desde su tag.

---

*Operativo v1.0 — 2026-07-08*
