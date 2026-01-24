# ✅ Resumen de Instalación - Integración con Odoo

## Estado: INSTALACIÓN COMPLETADA

### Archivos Creados

1. ✅ `backend/odoo_integration_service.py` - Servicio de integración
2. ✅ `INTEGRACION_ODOO.md` - Documentación completa
3. ✅ `QUICK_START_ODOO.md` - Guía rápida
4. ✅ `configure_odoo_integration.sh` - Script interactivo
5. ✅ `setup_odoo_env.sh` - Script de configuración automática

### Integraciones Realizadas

✅ Función `send_payment_to_odoo()` integrada en:
- Confirmación de pago PayPal
- Confirmación de pago Stripe (webhook)
- Aprobación manual de pago (admin)
- Página de éxito de pago

### Configuración del Servicio

✅ Variables de entorno agregadas al servicio systemd:
- `ODOO_INTEGRATION_ENABLED=true`
- `ODOO_API_URL=https://odoo.relatic.org/api/relatic/v1/sale`
- `ODOO_API_KEY=CAMBIAR_CON_API_KEY_REAL` ⚠️
- `ODOO_HMAC_SECRET=CAMBIAR_CON_HMAC_SECRET_REAL` ⚠️
- `ODOO_ENVIRONMENT=prod`

## ⚠️ ACCIÓN REQUERIDA

### Paso 1: Configurar Credenciales

Editar el servicio systemd con las credenciales reales:

```bash
sudo nano /etc/systemd/system/membresia-relatic.service
```

O editar el script y ejecutarlo de nuevo:

```bash
nano setup_odoo_env.sh
# Cambiar líneas 18-22 con los valores reales
./setup_odoo_env.sh
```

**Valores necesarios:**
- `ODOO_API_KEY`: La misma que está en Odoo (`relatic_integration.api_key`)
- `ODOO_HMAC_SECRET`: La misma que está en Odoo (`relatic_integration.hmac_secret`)

### Paso 2: Reiniciar el Servicio

```bash
sudo systemctl daemon-reload
sudo systemctl restart membresia-relatic.service
sudo systemctl status membresia-relatic.service
```

### Paso 3: Verificar

```bash
# Verificar variables configuradas
sudo systemctl show membresia-relatic.service | grep ODOO

# Ver logs en tiempo real
sudo journalctl -u membresia-relatic.service -f | grep -i odoo
```

## 🧪 Testing

1. Realizar un pago de prueba en membresia-relatic
2. Verificar logs:
   ```bash
   sudo journalctl -u membresia-relatic.service --since "5 minutes ago" | grep -i odoo
   ```
3. Verificar en Odoo:
   - Contabilidad → Relatic Integration → Logs de Sincronización
   - Buscar el Order ID más reciente

## 📊 Verificación en Odoo

1. **Logs de Sincronización**:
   - Menú: Contabilidad → Relatic Integration → Logs de Sincronización
   - Buscar por Order ID (ej: `ORD-2026-00021`)

2. **Facturas Creadas**:
   - Menú: Contabilidad → Clientes → Facturas
   - Buscar por "Origen" = Order ID

3. **Contactos**:
   - Menú: Contactos → Contactos
   - Buscar por email o etiqueta "RELATIC_MIEMBRO"

## 🔧 Troubleshooting

### No se envían webhooks

1. Verificar que `ODOO_INTEGRATION_ENABLED=true`
2. Verificar credenciales (API Key y HMAC Secret)
3. Ver logs: `sudo journalctl -u membresia-relatic.service -f`

### Error 401 - Invalid API Key

- Verificar que `ODOO_API_KEY` coincida con `relatic_integration.api_key` en Odoo

### Error 401 - Invalid Signature

- Verificar que `ODOO_HMAC_SECRET` coincida con `relatic_integration.hmac_secret` en Odoo

### Error 422 - Product Not Found

- Verificar que existan productos con SKU en Odoo:
  - MEMB-ANUAL
  - MEMB-BASICO
  - MEMB-PREMIUM
  - MEMB-DELUXE
- O activar `relatic_integration.auto_create_product = True` en Odoo

## 📝 Notas

- El webhook **no bloquea** el flujo principal si falla
- Los errores se registran en logs pero no afectan la confirmación del pago
- La integración es **idempotente**: enviar el mismo pago múltiples veces no crea duplicados
- El Order ID se genera como: `ORD-{YEAR}-{PAYMENT_ID:05d}`

## ✅ Checklist Final

- [x] Servicio de integración creado
- [x] Integración en app.py completada
- [x] Variables de entorno agregadas al servicio systemd
- [ ] **Configurar credenciales reales (API Key y HMAC Secret)**
- [ ] **Reiniciar servicio**
- [ ] **Probar con pago de prueba**
- [ ] **Verificar en Odoo**

---

**Fecha de instalación**: 2026-01-20  
**Estado**: ✅ Instalación completada - Pendiente configuración de credenciales
