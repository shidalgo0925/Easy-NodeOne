# Sprint UX — EN1 Platform → Transición entre Aplicaciones

| Campo | Valor |
|-------|--------|
| Estado | Especificación aprobada (9 jul 2026) — **UX-T1…T4 hechos en dev** · T5 opcional con GO |
| Carril | 2 — Plataforma |
| Edición | Solo `/opt/easynodeone/dev/app` · rama `develop` |
| Master Plan | [`EN1_PLATFORM_MASTER_PLAN.md`](EN1_PLATFORM_MASTER_PLAN.md) (Regla 5) |
| Roadmap | [`EN1_ROADMAP.md`](EN1_ROADMAP.md) § Plataforma — EPosOne |

**Comentario / plan.** No implementar fuera de este alcance. Sin GO explícito por ticket: no editar código.

---

## 1. Objetivo

La arquitectura actual (**Plataforma → App con menú propio**) **se mantiene**.

**No** volver a mezclar EPosOne dentro del menú del ERP.

Este sprint **no** cambia la arquitectura. Mejora la **experiencia** para que el cambio entre aplicaciones sea **natural y evidente**.

Estado esperado al cerrar:

```text
Login
  → EasyNodeOne Platform
  → Mis aplicaciones
  → EPosOne
  → “Ahora estoy usando EPosOne”
  → trabaja normalmente
  → ← Mis aplicaciones
  → vuelve a EasyNodeOne Platform
```

**Nunca** debe sentirse que “el menú cambió de repente”.  
Debe sentirse que **cambió de aplicación**.

---

## 2. Visión congelada (no negociable)

EasyNodeOne es una **plataforma**.  
Las aplicaciones (EPosOne, EPayRoll, EClassOne, …) son **productos** independientes que consumen el Core.

Flujo oficial:

```text
Login → EasyNodeOne Platform → Launcher / Mis aplicaciones → EPosOne
```

Mientras esté en EPosOne, el usuario **no** debe sentir que navega dentro del ERP.

**Las Apps no son módulos. Las Apps son productos.**

---

## 3. Lo que NO debe hacerse

| Prohibido | Motivo |
|-----------|--------|
| Integrar EPosOne otra vez como ítem “más” del menú ERP (mezcla de dominios) | Rompe Regla 5 |
| Mostrar Comercial / Finanzas / CRM **ERP** mientras se está en `/admin/eposone/*` | Confunde contexto |
| Usar copy “Salir de EN1” / “Salir a EN1” | El usuario no salió de EN1 |
| Tratar el atajo “EPosOne” en sidebar ERP classic como solución definitiva | Solo **temporal** |
| Dejar analítica POS como `/admin/analytics/...?source=eposone` como diseño de producto | Es parche técnico |
| Mostrar al usuario términos como “Core Compuesto” | No aporta valor |

---

## 4. Fases

### Fase 1 — Arquitectura (mantener; ya en curso)

- Menú propio de EPosOne.
- Menú propio de Plataforma.
- **No** mezclar dominios.
- Shell nativo en rutas `/admin/eposone/*`.
- Ítem “EPosOne” en ERP classic = **atajo temporal** (documentado en código/roadmap).

### Fase 2 — Antes del release (este sprint UX)

Experiencia de cambio entre aplicaciones (tickets §6).

---

## 5. Requisitos de producto (Fase 2)

### 5.1 Cambio de contexto

Al entrar a EPosOne debe quedar claro: **ahora trabaja dentro del POS**.

- Transición visual clara (no hace falta animación compleja).
- Señales: identidad de app + retorno visible + (opcional) micro-transición CSS / fade corto.

### 5.2 Identidad propia de EPosOne

Dentro de EPosOne **todo** habla de EPosOne:

- Logo / nombre **EPosOne**
- Color / acento propio (variables CSS de app)
- Encabezado / chrome de app propio

Producto, no “otra pantalla del ERP”.

### 5.3 Punto de retorno (obligatorio)

Control **siempre visible** hacia launcher / plataforma.

**Copy permitido (uno, consistente):**

- `← Mis aplicaciones`
- `← Plataforma EasyNodeOne`

**Prohibido:** “Salir de EN1”, “Salir a EN1”.

Comportamiento: navega al **Launcher** (`/platform/apps` o equivalente), **no** logout.

### 5.4 Launcher = entrada oficial

- Launcher / Mis aplicaciones = entrada oficial a todas las apps.
- Enlace “EPosOne” en sidebar ERP classic = **solo temporal** hasta cutover launcher.
- En código: comentario `TEMPORAL — atajo classic hasta cutover launcher`.

### 5.5 Menús

- Menú propio EPosOne (dominios).
- **No** reutilizar menú ERP dentro de EPosOne.

### 5.6 Analítica — decisión de producto

**Prohibido como diseño:** `/analytics?source=eposone` (o equivalente).

| Tipo | Dónde | Ejemplos |
|------|--------|----------|
| Analítica del POS | **Dentro de EPosOne** | Ventas, pedidos, caja, ticket promedio, top productos, horas pico, vendedores, inventario |
| Analítica Plataforma | **EN1 / Plataforma** | KPIs corporativos, comparativo entre apps, facturación total, orgs, usuarios, licencias |

Nunca mezclar. KPIs POS bajo rutas/nav de EPosOne; no “filtrar” la pantalla plataforma.

### 5.7 Terminología UI

| Evitar | Preferir |
|--------|----------|
| Core Compuesto | Accesos rápidos / Operaciones frecuentes / Herramientas / Enlaces útiles |

### 5.8 Dashboard EPosOne

Prioridad visual / operativa:

- Ventas del día, pedidos abiertos, caja abierta, stock crítico / alertas  
- Productos más vendidos, últimas ventas, accesos rápidos  

Menos texto descriptivo; empty states cortos.

---

## 6. Tickets y orden de PRs (Dev EN1)

**Regla:** 1 chat / 1 PR por ticket cuando sea posible. Commit/push solo si el usuario lo pide.

| Orden | ID | Título | Alcance | Archivos orientativos | DoD del ticket |
|------:|----|--------|---------|----------------------|----------------|
| 1 | **UX-T1** | Retorno + identidad shell EPosOne | Control `← Mis aplicaciones` (o Plataforma EN1) → `/platform/apps`; branding EPosOne en chrome (logo/nombre/acento); micro-señal de contexto | `app_shell.py`, templates shell EPosOne / `platform_app_shell*`, CSS app, `app_nav.py` | Retorno visible en `/admin/eposone/*`; copy correcto; no logout; tests shell/nav |
| 2 | **UX-T2** | Atajo ERP classic = temporal | Documentar en `nav_menu.py` + roadmap; no ampliar atajo; opcional: badge “App” o tooltip | `nav_menu.py`, `EN1_ROADMAP.md` | Comentario `TEMPORAL`; roadmap actualizado |
| 3 | **UX-T3** | Dashboard copy + empty states | Quitar “Core Compuesto”; accesos rápidos; menos prosa; métricas primero | Templates/dashboard EPosOne | Sin “Core Compuesto”; UI más operativa |
| 4 | **UX-T4** | Analítica POS dentro de EPosOne | KPIs POS en nav/rutas EPosOne; dejar de usar `?source=eposone` como diseño; analítica global queda en Plataforma | `modules/eposone/nav.py`, rutas analytics o wrapper EP1, enlaces desde dashboard | Sin dependencia de producto en `source=eposone`; entrada desde menú EP1 |
| 5 | **UX-T5** | (Opcional) Transición visual entrada | Fade/overlay corto al setear app activa / entrar a `/admin/eposone/*` | Shell + CSS | Percepción “entré a app”, no “menú roto” |

**Orden recomendado de PRs:** T1 → T2 → T3 → T4 → T5.

**Fuera de este sprint:** cutover masivo a modo `apps` en clientes; EPayRoll/EClassOne; rediseño ERP classic; deploy Relatic/IIUS/prod; consolidación total `nav_menu` vs `eposone/nav` (salvo lo mínimo para T1/T4).

---

## 7. Definition of Done (sprint)

- [ ] Usuario entiende que cambió de aplicación (identidad + retorno).
- [ ] Control `← Mis aplicaciones` o `← Plataforma EasyNodeOne` visible en shell EPosOne → Launcher.
- [ ] En `/admin/eposone/*` no aparece menú ERP plataforma.
- [x] Atajo “EPosOne” en ERP classic documentado como **temporal** (UX-T2).
- [x] Analítica POS en EPosOne (UX-T4: `/admin/eposone/analytics`; sin `?source=eposone`).
- [x] Sin “Core Compuesto” en UI tocada; dashboard más visual (UX-T3).
- [ ] Solo Dev EN1; tests mínimos shell/nav si aplica.
- [ ] UX-T5 (opcional) micro-transición visual.

---

## 8. Referencias de código

| Tema | Ubicación |
|------|-----------|
| Shell / contexto app | `backend/nodeone/core/platform/app_shell.py` |
| Nav nativa EPosOne | `backend/nodeone/core/platform/app_nav.py`, `modules/eposone/nav.py` |
| Launcher | `platform/launcher.py`, `/platform/apps` |
| Atajo temporal ERP | `nav_menu.py` (`_SIDEBAR_TOP_LEVEL_AREA_IDS`) |
| Carriles | [`EN1_PLATFORM_CARRILES_Y_SOPORTE.md`](EN1_PLATFORM_CARRILES_Y_SOPORTE.md) |

---

## 9. Protocolo

1. Plan = este documento.  
2. **GO** por entregable (ej. `GO UX-T1`).  
3. Sin GO → no editar.  
4. Commit/push solo si se pide.  
5. **1 chat = 1 tarea** (recomendado: un chat por ticket UX-T*).

---

## 10. Mensaje corto al programador

> Mantén arquitectura Plataforma → App. No mezcles EPosOne en el menú ERP.  
> Sprint = UX de transición: identidad EPosOne, retorno «← Mis aplicaciones» / «← Plataforma EasyNodeOne» al launcher, launcher como entrada oficial, atajo ERP classic solo temporal.  
> Analítica POS dentro de EPosOne; analítica global en Plataforma; nada de `?source=eposone` como diseño.  
> Quita “Core Compuesto”; dashboard más visual.  
> Solo Dev EN1. Tickets UX-T1…T5. No implementar fuera de alcance sin GO por ticket.
