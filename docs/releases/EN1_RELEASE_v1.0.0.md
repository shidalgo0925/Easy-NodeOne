# EN1 Release v1.0.0 — EPosOne (Release Candidate)

| Campo | Valor |
|-------|--------|
| Producto foco | **EPosOne** (pipeline reutilizable para todos los productos EN1) |
| Versión | **v1.0.0-rc1** (Release Candidate) |
| Release final | **v1.0.0** — solo tras **GO LIVE** |
| Fecha freeze | 2026-07-27 |
| Proceso | [ADR-018](../ADR-018-RELEASE-MANAGEMENT.md) |
| Entrada cliente | [ADR-017](../ADR-017-CUSTOMER-ENTRY-POINT-PRODUCT-PORTAL.md) |

---

## 1. Feature Freeze — entrega oficial

| Entrega | Valor |
|---------|--------|
| **Commit RC (código)** | `d20bee4` — `merge(develop): EPosOne Business USD 49.95` |
| **Tag** | `v1.0.0-rc1` → apunta a `d20bee4` |
| **Fecha** | 2026-07-27 |
| **Ramas** | `main` y `develop` contienen el RC; docs de proceso pueden ir en commits posteriores |
| **Staging HEAD** | Debe ser `d20bee4` / `v1.0.0-rc1` |
| **Prod HEAD (pre GO LIVE)** | Ya estaba en `d20bee4` al freeze; **no** redeploy hasta GO LIVE / firma QA |

### Congelamiento

- No nuevas features en `develop` hasta cerrar v1.0.0 (GO LIVE + smoke).
- Solo correcciones **críticas** con acuerdo explícito (parche → nuevo rc si hace falta).

---

## 2. Changelog (v1.0.0-rc1)

### Comercial / landing (ADR-017)

- Landing oficial EPosOne en EN1: host `eposone.easytech.services` (no WordPress).
- Hero split con gráfica comercial; planes Starter / Business / Enterprise.
- Precios: Starter **USD 29.95**, Business **USD 49.95**, Enterprise **USD 79.95**; prueba 15 días.
- Servicios incluidos / opcionales; módulos CRM/Marketing marcados como adicionales.
- Portal auth + lanzador inteligente (1 producto → home; N → Mis Productos).

### Plataforma (base del RC)

- ProductContext / Host map / Subscription Registry / entitlements (ADR-011…017).
- Superficies: landing producto, Portal ETS, app producto, `appprd` técnico.

### Fuera de este RC (no bloquea el tag; ver riesgos)

- QA funcional completa (Fase 3) firmada.
- Backup formal prod (Fase 5) ejecutado en ventana GO LIVE.
- Ocultación completa de `appprd` en marketing/DNS (Fase 10) — política documentada; hardening nginx pendiente de ops.

---

## 3. Checklist QA funcional (Fase 3) — staging

Marcar al validar. Responsable: ________ Fecha: ________

### Portal / Auth

- [ ] Login
- [ ] Logout
- [ ] Recuperación de contraseña
- [ ] Registro
- [ ] Portal Mis Productos (multiproducto)

### Organización

- [ ] Crear organización
- [ ] Crear sucursal
- [ ] Crear cajas POS

### Licenciamiento

- [ ] Trial
- [ ] Business
- [ ] Enterprise
- [ ] Suspender
- [ ] Reactivar

### Provisioning

- [ ] Registrar dispositivo
- [ ] Reprovisionar
- [ ] Bootstrap

### EPosOne operación

- [ ] Productos
- [ ] Clientes
- [ ] Pedidos
- [ ] Pagos / pago mixto
- [ ] Tickets abiertos
- [ ] Impresión
- [ ] Turnos / arqueo / cierre
- [ ] Sincronización
- [ ] Dashboard / totales / reportes

### Seguridad

- [ ] Tenant isolation
- [ ] Roles / permisos
- [ ] Entitlements

### Landing comercial

- [ ] https://eposone.easytech.services/ (o staging host) — hero, planes, FAQ, demo, Entrar
- [ ] Entrar → auth EN1 (sin segundo login system)

---

## 4. Performance (Fase 4)

- [ ] Logs staging sin errores críticos nuevos
- [ ] Memoria / CPU aceptables tras smoke
- [ ] Workers / colas (si aplica) sanos

---

## 5. Backup producción (Fase 5) — ejecutar antes de GO LIVE

```bash
# Ejemplo — ajustar nombres; NO correr sin ventana acordada
DATE=$(date +%Y%m%d_%H%M%S)
# pg_dump de easynodeone_prod → /opt/easynodeone/prod/backups/pg_backup_prod_${DATE}.dump
# Anotar: tag/commit actual prod, path .env, nginx sites, systemd units
```

Punto de restauración: path ________ hash ________

---

## 6. Rollback &lt; 15 min (Fase 6)

**Si el GO LIVE de v1.0.0 falla**, volver al tag/commit previo documentado aquí.

Al freeze RC, prod ya está en `d20bee4`. Si un GO LIVE futuro avanza a otro commit:

```bash
PREV=<tag-o-commit-anterior>   # rellenar en el momento del GO LIVE
cd /opt/easynodeone/prod/app
git -c safe.directory=/opt/easynodeone/prod/app fetch origin --tags
git -c safe.directory=/opt/easynodeone/prod/app checkout "$PREV"
export EASYNODEONE_DEPLOY_PROD_CONFIRM=YES
# Restaurar dump SOLO si hubo migración incompatible
sudo systemctl restart easynodeone-prod
# Smoke: login + landing Host eposone + dashboard mínimo
```

Assets: estáticos en repo; no requiere build separado salvo que el release lo indique.  
Migraciones: no revertir DDL a ciegas — preferir forward-fix o restore dump.

---

## 7. GO LIVE producción (Fase 7) — bloqueado

**No modificar producción** hasta:

1. Fase 3–4 firmadas  
2. Backup Fase 5 hecho  
3. Mensaje explícito del usuario: **GO LIVE v1.0.0**

Entonces: tag `v1.0.0` (si = RC, retag mismo commit), checkout prod, deps/migraciones solo si aplican, restart, smoke (Fase 8).

---

## 8. Publicación comercial (Fase 9) — estado

| Ítem | Estado |
|------|--------|
| Landing en EN1 | **Hecho** (módulo `product_landing`) |
| Host `eposone.easytech.services` | **Activo** → prod |
| Hero / beneficios / planes / FAQ / demo / Entrar | **Hecho** |
| Auth EN1 (Entrar) | **Hecho** |
| Launcher 1 vs N productos | **Hecho** |
| WordPress | **No usado** |

---

## 9. Infra (Fase 10)

| Host | Rol |
|------|-----|
| `eposone.easytech.services` | Cliente — producto |
| `app.easytech.services` | Cliente — Portal multiproducto |
| `appprd.easynodeone.com` | **Técnico** — no marketing |

Pendiente ops: reforzar que marketing/DNS no promocionen `appprd`.

---

## 10. Riesgos pendientes

| Riesgo | Severidad | Mitigación |
|--------|-----------|------------|
| QA Fase 3 aún no firmada | Alta para declarar v1.0.0 final | Completar checklist en staging antes de GO LIVE |
| Sin host `eposone-dev` | Media (visibilidad) | Probar vía Host en :9101 o crear DNS Dev |
| Drift histórico staging/prod por pulls previos | Baja al freeze | RC tag + checkout explícito de aquí en adelante |
| Dump prod no ejecutado aún | Alta en GO LIVE | Fase 5 obligatoria antes de tocar prod |

---

## 11. Firmas

| Rol | Nombre | Fecha | OK |
|-----|--------|-------|-----|
| Feature freeze | | 2026-07-27 | |
| QA staging | | | |
| Backup prod | | | |
| GO LIVE | | | |
