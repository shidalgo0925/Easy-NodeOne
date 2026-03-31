# 🚀 Quick Start - Integración con Odoo

## Configuración Rápida

### Paso 1: Ejecutar script de configuración

```bash
cd /home/relaticpanama2025/projects/membresia-relatic
./scripts/root/configure_odoo_integration.sh
```

El script te pedirá:
- ¿Habilitar integración? → `true`
- URL del API → `https://odoo.relatic.org/api/relatic/v1/sale`
- API Key → (la misma configurada en Odoo)
- HMAC Secret → (la misma configurada en Odoo)
- Ambiente → `prod`

### Paso 2: Reiniciar el servicio

```bash
sudo systemctl restart membresia-relatic.service
sudo systemctl status membresia-relatic.service
```

### Paso 3: Verificar logs

```bash
sudo journalctl -u membresia-relatic.service -f | grep -i odoo
```

## Verificación Rápida

### En membresia-relatic

1. Realizar un pago de prueba
2. Verificar logs:
   ```bash
   sudo journalctl -u membresia-relatic.service --since "5 minutes ago" | grep -i odoo
   ```

### En Odoo

1. Ir a: **Contabilidad → Relatic Integration → Logs de Sincronización**
2. Buscar el Order ID más reciente (ej: `ORD-2026-00021`)
3. Verificar que el estado sea "success"

## Configuración Manual (Alternativa)

Si prefieres configurar manualmente, edita el servicio systemd:

```bash
sudo nano /etc/systemd/system/membresia-relatic.service
```

Agregar en la sección `[Service]`:

```ini
Environment="ODOO_INTEGRATION_ENABLED=true"
Environment="ODOO_API_URL=https://odoo.relatic.org/api/relatic/v1/sale"
Environment="ODOO_API_KEY=tu_api_key_aqui"
Environment="ODOO_HMAC_SECRET=tu_hmac_secret_aqui"
Environment="ODOO_ENVIRONMENT=prod"
```

Luego:

```bash
sudo systemctl daemon-reload
sudo systemctl restart membresia-relatic.service
```

## Deshabilitar Integración

Para deshabilitar temporalmente sin eliminar la configuración:

```bash
sudo systemctl edit membresia-relatic.service
```

Agregar:

```ini
[Service]
Environment="ODOO_INTEGRATION_ENABLED=false"
```

O ejecutar el script de nuevo y seleccionar `false`.

## Troubleshooting

### No se envían webhooks

1. Verificar que `ODOO_INTEGRATION_ENABLED=true`
2. Verificar logs: `sudo journalctl -u membresia-relatic.service -f`
3. Verificar que las variables estén configuradas:
   ```bash
   sudo systemctl show membresia-relatic.service | grep ODOO
   ```

### Error 401 - Invalid API Key

- Verificar que `ODOO_API_KEY` en membresia-relatic coincida con `relatic_integration.api_key` en Odoo

### Error 401 - Invalid Signature

- Verificar que `ODOO_HMAC_SECRET` en membresia-relatic coincida con `relatic_integration.hmac_secret` en Odoo

---

**¡Listo!** La integración debería estar funcionando. 🎉
