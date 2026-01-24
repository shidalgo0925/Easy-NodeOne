# Configuración de Microsoft Office 365 para Envío de Emails

## Configuración SMTP de Office 365

### Parámetros de Conexión

- **Servidor SMTP:** `smtp.office365.com`
- **Puerto:** `587` (recomendado con TLS) o `25`
- **Seguridad:** TLS (STARTTLS)
- **Autenticación:** Usuario y contraseña de Office 365

### Ventajas de Office 365

✅ No requiere App Passwords (a diferencia de Gmail)
✅ Usa tu contraseña normal de Office 365
✅ Más confiable para envío de emails corporativos
✅ Mejor para emails transaccionales

## Pasos de Configuración

### Opción 1: Configurar desde el Panel de Administración (Recomendado)

1. **Ir a `/admin/email`** en el panel de administración

2. **Configurar los siguientes valores:**
   - **Servidor SMTP:** `smtp.office365.com`
   - **Puerto:** `587`
   - **Usar TLS:** ✅ Activado
   - **Usar SSL:** ❌ Desactivado
   - **Usuario/Email:** `tu_email@tudominio.com` (tu cuenta de Office 365)
   - **Contraseña:** Tu contraseña normal de Office 365
   - **Remitente por Defecto:** `tu_email@tudominio.com` o `noreply@tudominio.com`
   - **Usar Variables de Entorno:** ❌ Desactivado (si quieres guardar en BD)

3. **Hacer clic en "Guardar Configuración"**

4. **Probar el envío:**
   - Hacer clic en "Probar Envío"
   - Verificar que llegue el correo de prueba

### Opción 2: Usar Variables de Entorno

Si prefieres usar variables de entorno (más seguro):

1. **Editar el archivo del servicio systemd:**
   ```bash
   sudo nano /etc/systemd/system/membresia-relatic.service
   ```

2. **Agregar en la sección `[Service]`:**
   ```ini
   Environment="MAIL_SERVER=smtp.office365.com"
   Environment="MAIL_PORT=587"
   Environment="MAIL_USE_TLS=True"
   Environment="MAIL_USE_SSL=False"
   Environment="MAIL_USERNAME=tu_email@tudominio.com"
   Environment="MAIL_PASSWORD=tu_contraseña"
   Environment="MAIL_DEFAULT_SENDER=tu_email@tudominio.com"
   ```

3. **Recargar y reiniciar:**
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl restart membresia-relatic.service
   ```

4. **En el panel `/admin/email`:**
   - Activar "Usar Variables de Entorno"
   - Guardar configuración

## Configuración Detallada

### Valores Recomendados

| Parámetro | Valor |
|-----------|-------|
| Servidor SMTP | `smtp.office365.com` |
| Puerto | `587` |
| TLS | ✅ Activado |
| SSL | ❌ Desactivado |
| Autenticación | Usuario y contraseña |
| Usuario | `tu_email@tudominio.com` |
| Contraseña | Tu contraseña de Office 365 |
| Remitente | `tu_email@tudominio.com` |

### Puertos Alternativos

- **Puerto 587** (recomendado): Usa STARTTLS, funciona en la mayoría de redes
- **Puerto 25**: Puede estar bloqueado por algunos ISPs
- **Puerto 465**: Requiere SSL (no recomendado para O365)

## Verificación

### 1. Probar desde el Panel

1. Ir a `/admin/email`
2. Hacer clic en "Probar Envío"
3. Verificar que llegue el correo de prueba

### 2. Revisar Logs

```bash
sudo journalctl -u membresia-relatic.service -f
```

Buscar mensajes como:
- ✅ `Email enviado exitosamente`
- ❌ `Error enviando email` (si hay problemas)

### 3. Verificar en EmailLog

- Ir a `/admin/email/logs`
- Verificar que los emails se registren correctamente

## Solución de Problemas

### Error: "Authentication failed"

**Causas:**
- Usuario o contraseña incorrectos
- Cuenta bloqueada o suspendida
- Autenticación multifactor (MFA) requerida

**Soluciones:**
- Verificar credenciales
- Si tienes MFA, puede que necesites una contraseña de aplicación (menos común en O365)
- Verificar que la cuenta esté activa

### Error: "Connection timeout"

**Causas:**
- Puerto bloqueado por firewall
- Red no permite conexiones SMTP

**Soluciones:**
- Verificar que el puerto 587 esté abierto
- Probar con puerto 25 (si está disponible)
- Verificar configuración de firewall

### Error: "STARTTLS failed"

**Causas:**
- TLS no está habilitado
- Problema de certificado SSL

**Soluciones:**
- Asegurar que "Usar TLS" esté activado
- Verificar que el puerto sea 587 (no 465)

## Notas Importantes

- **Seguridad:** Office 365 es más seguro que Gmail para emails corporativos
- **Límites:** Office 365 tiene límites de envío (normalmente 10,000 emails/día para cuentas estándar)
- **Autenticación:** No requiere App Passwords como Gmail
- **MFA:** Si tienes MFA activado, puede que necesites una contraseña de aplicación (configurar en Azure AD)

## Migración desde Gmail

Si estás migrando desde Gmail:

1. Actualizar la configuración SMTP en `/admin/email`
2. Cambiar servidor de `smtp.gmail.com` a `smtp.office365.com`
3. Actualizar credenciales
4. Probar envío
5. Verificar que los emails lleguen correctamente


