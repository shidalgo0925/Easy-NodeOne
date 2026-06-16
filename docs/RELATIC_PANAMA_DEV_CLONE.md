# Relatic Panamá DEV aislado (clon producción)

**Fecha clonación:** 2026-06-08  
**Regla:** no usar para tráfico real; no apunta a `apps.relatic.org`.

---

## Origen (solo lectura — producción intacta)

| Ítem | Valor |
|------|--------|
| BD origen | `easynodeone_relatic` |
| Servicio prod | `easynodeone-relatic.service` |
| Puerto prod | `127.0.0.1:9103` |
| URL prod | https://apps.relatic.org |
| App prod | `/opt/easynodeone/relatic/app` |

**Producción:** no se modificó BD, no se reinició servicio productivo para este clon.

---

## Destino (DEV aislado)

| Ítem | Valor |
|------|--------|
| BD destino | `relatic_panama_dev` |
| Backup lógico | `/opt/easynodeone/relatic-panama-dev/backups/easynodeone_relatic_20260608_085159.dump` |
| Silo | `/opt/easynodeone/relatic-panama-dev/` |
| Código app | `/opt/easynodeone/relatic-panama-dev/app` (copia de `dev/app` + certificados 2A) |
| Uploads | `/opt/easynodeone/relatic-panama-dev/app/static/uploads/` (copia de Relatic prod) |
| `.env` | `/opt/easynodeone/relatic-panama-dev/.env` |
| Servicio systemd | `easynodeone-relatic-panama-dev.service` |
| Puerto DEV | `127.0.0.1:9105` |
| URL DEV | http://127.0.0.1:9105 |
| `BASE_URL` | `http://127.0.0.1:9105` (QR y verify usan este host) |

---

## Restore — datos al clonar

| Tabla | Filas |
|-------|------:|
| `event` | 4 |
| `event_participant` | 2 |
| `event_certificate` | 1 |
| `saas_organization` | 1 |

---

## Seguridad DEV

- `MAIL_*` vacío — sin envío SMTP real.
- `PAYPAL_CLIENT_ID/SECRET` vacío — sin cobros live.
- `FLASK_ENV=development`, `SESSION_COOKIE_SECURE=false`.
- No probar en `apps.relatic.org`.

---

## Comandos útiles

```bash
# Estado
systemctl status easynodeone-relatic-panama-dev.service

# Reiniciar (solo DEV)
sudo systemctl restart easynodeone-relatic-panama-dev.service

# Logs
sudo journalctl -u easynodeone-relatic-panama-dev.service -f

# Comprobar prod sigue activo
systemctl is-active easynodeone-relatic.service
```

---

## Validación realizada (2026-06-08)

- [x] Backup `pg_dump` generado
- [x] BD `relatic_panama_dev` creada y restaurada
- [x] Servicio DEV `active` en puerto 9105
- [x] HTTP 302 en http://127.0.0.1:9105/
- [x] Eventos / participantes / certificados visibles en BD clon
- [x] Admins de prod presentes en clon
- [x] URL verify de certificado → `http://127.0.0.1:9105/certificates/verify/...`
- [x] Producción `easynodeone-relatic` sigue `active`

---

## Uso previsto

Desarrollar y probar **certificados Relatic Nivel 2A** (plantilla institucional, logos, QR, PDF) con datos reales clonados, sin riesgo para producción.

Acceso admin: mismo usuario/contraseña que en prod (datos clonados). Abrir http://127.0.0.1:9105/admin (o vía túnel SSH si se accede desde fuera del servidor).

---

## Re-clonar (futuro)

```bash
TS=$(date +%Y%m%d_%H%M%S)
sudo -u postgres pg_dump -Fc -f /tmp/easynodeone_relatic_${TS}.dump easynodeone_relatic
sudo systemctl stop easynodeone-relatic-panama-dev.service
sudo -u postgres dropdb relatic_panama_dev
sudo -u postgres createdb relatic_panama_dev OWNER enode_relatic_user
sudo -u postgres pg_restore -d relatic_panama_dev --no-owner --role=enode_relatic_user /tmp/easynodeone_relatic_${TS}.dump
sudo systemctl start easynodeone-relatic-panama-dev.service
```

Guardar el `.dump` en `relatic-panama-dev/backups/` con `mv` y `chown nodeone`.
