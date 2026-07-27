# EN1 Release v1.0.0 — EPosOne

| Campo | Valor |
|-------|--------|
| Producto foco | **EPosOne** (pipeline reutilizable para todos los productos EN1) |
| Versión | **v1.0.0** (publicado) |
| RC previo | `v1.0.0-rc1` (mismo commit) |
| Fecha freeze | 2026-07-27 |
| Fecha GO LIVE | 2026-07-27 |
| Proceso | [ADR-018](../ADR-018-RELEASE-MANAGEMENT.md) |
| Entrada cliente | [ADR-017](../ADR-017-CUSTOMER-ENTRY-POINT-PRODUCT-PORTAL.md) |

---

## 1. Feature Freeze / Release — entrega oficial

| Entrega | Valor |
|---------|--------|
| **Commit** | `d20bee4` — `merge(develop): EPosOne Business USD 49.95` |
| **Tags** | `v1.0.0-rc1` · **`v1.0.0`** |
| **Fecha GO LIVE** | 2026-07-27 |
| **Staging** | `v1.0.0` (`d20bee4`) |
| **Prod** | `v1.0.0` (`d20bee4`) |

### Congelamiento post-release

- Nuevas features → nuevo ciclo RC (ADR-018).
- Fixes críticos → `v1.0.x` con el mismo pipeline.

---

## 2. Changelog (v1.0.0)

### Comercial / landing (ADR-017)

- Landing oficial EPosOne en EN1: host `eposone.easytech.services` (no WordPress).
- Hero split con gráfica comercial; planes Starter / Business / Enterprise.
- Precios: Starter **USD 29.95**, Business **USD 49.95**, Enterprise **USD 79.95**; prueba 15 días.
- Servicios incluidos / opcionales; módulos CRM/Marketing marcados como adicionales.
- Portal auth + lanzador inteligente (1 producto → home; N → Mis Productos).

### Plataforma (base)

- ProductContext / Host map / Subscription Registry / entitlements (ADR-011…017).
- Superficies: landing producto, Portal ETS, app producto, `appprd` técnico.

---

## 3. Checklist QA funcional (Fase 3)

Marcar al validar. Smoke automático GO LIVE: landing HTTP 200 + planes 29.95/49.95/79.95 en prod.

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

- [x] https://eposone.easytech.services/ — hero, planes, FAQ, demo, Entrar (smoke GO LIVE)
- [ ] Entrar → auth EN1 (validación humana)

---

## 4. Performance (Fase 4)

- [x] Servicios staging/prod **active** tras checkout `v1.0.0`
- [ ] Revisión humana de logs / CPU / workers

---

## 5. Backup producción (Fase 5) — ejecutado

| Campo | Valor |
|-------|--------|
| Fecha | 20260727_175716 |
| Dump | `/opt/easynodeone/prod/backups/pg_backup_easynodeone_prod_20260727_175716.dump` |
| Meta | `/opt/easynodeone/prod/backups/RESTORE_POINT_20260727_175716.txt` |
| Commit al backup | `d20bee4` |

---

## 6. Rollback &lt; 15 min (Fase 6)

Si hay que revertir **después** de un release futuro distinto de `d20bee4`:

```bash
PREV=v1.0.0   # o el tag anterior documentado
cd /opt/easynodeone/prod/app
git -c safe.directory=/opt/easynodeone/prod/app fetch origin --tags
git -c safe.directory=/opt/easynodeone/prod/app checkout "$PREV"
export EASYNODEONE_DEPLOY_PROD_CONFIRM=YES
# Restaurar dump SOLO si hubo migración incompatible:
# pg_restore … /opt/easynodeone/prod/backups/pg_backup_easynodeone_prod_20260727_175716.dump
sudo systemctl restart easynodeone-prod
```

---

## 7. GO LIVE producción (Fase 7) — hecho

- [x] Tag `v1.0.0` = `d20bee4`
- [x] Staging + prod en `v1.0.0`
- [x] Reinicio servicios
- [x] Smoke landing prod

---

## 8. Smoke test producción (Fase 8) — parcial

- [x] Landing pública operativa (planes / precios)
- [ ] Org de prueba: login, provisioning, pedido, pago, turno (humano)

---

## 9. Publicación comercial (Fase 9)

| Ítem | Estado |
|------|--------|
| Landing en EN1 | **Hecho** |
| Host `eposone.easytech.services` | **Activo** |
| Auth EN1 / launcher | **Hecho** |

---

## 10. Infra (Fase 10)

| Host | Rol |
|------|-----|
| `eposone.easytech.services` | Cliente — producto |
| `app.easytech.services` | Cliente — Portal multiproducto |
| `appprd.easynodeone.com` | **Técnico** — no marketing |

---

## 11. Riesgos pendientes

| Riesgo | Severidad | Mitigación |
|--------|-----------|------------|
| QA operativa completa no firmada (pedido/caja/licencias) | Media | Completar checklist §3 en staging/prod de prueba |
| Sin host `eposone-dev` | Baja | Opcional DNS Dev |
| Endurecer ocultación `appprd` en marketing | Baja | Ops / DNS / copy |

---

## 12. Firmas

| Rol | Nombre | Fecha | OK |
|-----|--------|-------|-----|
| Feature freeze | Codito | 2026-07-27 | x |
| Backup prod | Codito | 2026-07-27 | x |
| GO LIVE | Codito (GO usuario) | 2026-07-27 | x |
| QA staging completa | | | |
