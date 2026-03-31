# Instrucciones para Configurar Verificación Automática de Pagos Yappy

## 📋 Resumen

El sistema de verificación automática de pagos Yappy está implementado y listo para usar. Solo necesita configurarse el cron job para que se ejecute automáticamente cada 5 minutos.

## 🔧 Opción 1: Usar Script Automático (Recomendado)

```bash
cd /home/relaticpanama2025/projects/membresia-relatic/backend
./scripts/backend/setup_yappy_cron.sh
```

## 🔧 Opción 2: Configuración Manual

### Paso 1: Abrir el editor de crontab

```bash
crontab -e
```

### Paso 2: Agregar la siguiente línea

```bash
# Verificación automática de pagos Yappy cada 5 minutos
*/5 * * * * /home/relaticpanama2025/projects/membresia-relatic/venv/bin/python3 /home/relaticpanama2025/projects/membresia-relatic/backend/verify_yappy_payments_cron.py >> /home/relaticpanama2025/projects/membresia-relatic/logs/yappy_verification.log 2>&1
```

### Paso 3: Guardar y salir

- En `nano`: `Ctrl+X`, luego `Y`, luego `Enter`
- En `vi`: `:wq`

## ✅ Verificar que está funcionando

### Ver el cron job configurado:

```bash
crontab -l | grep yappy
```

### Ver los logs en tiempo real:

```bash
tail -f /home/relaticpanama2025/projects/membresia-relatic/logs/yappy_verification.log
```

### Ejecutar manualmente para probar:

```bash
cd /home/relaticpanama2025/projects/membresia-relatic/backend
python3 verify_yappy_payments_cron.py
```

## 🔍 Qué hace el cron job

1. Se ejecuta cada 5 minutos automáticamente
2. Busca todos los pagos pendientes de Yappy (últimas 24 horas)
3. Para cada pago:
   - Si tiene `yappy_transaction_id`, verifica directamente con la API de Yappy
   - Si no tiene, intenta verificar con la referencia interna
   - Si el pago está confirmado en Yappy, actualiza el estado a `succeeded`
   - Procesa el carrito automáticamente
   - Envía notificaciones al usuario

## 📊 Monitoreo

### Ver estadísticas de pagos:

```bash
cd /home/relaticpanama2025/projects/membresia-relatic/backend
python3 check_yappy_payments.py
```

### Ver últimos logs:

```bash
tail -n 50 /home/relaticpanama2025/projects/membresia-relatic/logs/yappy_verification.log
```

## ⚠️ Notas Importantes

1. **Credenciales de Yappy**: Asegúrate de tener configuradas las variables de entorno:
   - `YAPPY_API_KEY`
   - `YAPPY_MERCHANT_ID`
   - `YAPPY_WEBHOOK_SECRET` (opcional pero recomendado)

2. **Permisos**: El script debe tener permisos de ejecución:
   ```bash
   chmod +x /home/relaticpanama2025/projects/membresia-relatic/backend/verify_yappy_payments_cron.py
   ```

3. **Logs**: Los logs se guardan en:
   ```
   /home/relaticpanama2025/projects/membresia-relatic/logs/yappy_verification.log
   ```

## 🚀 Sistema Completo

El sistema ahora tiene **3 mecanismos** para confirmar pagos:

1. **Webhook automático** (inmediato) - `/webhook/yappy`
2. **Verificación automática cada 5 minutos** (cron job) - Este documento
3. **Verificación manual** (después de 5 minutos) - Interfaz web

Todos están implementados y funcionando. Solo falta configurar el cron job.
