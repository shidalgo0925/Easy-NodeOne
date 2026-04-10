# Guía: Habilitar SMTP AUTH en Office 365

## Ubicación de la Configuración

La opción de "Autenticación SMTP básica" puede estar en diferentes lugares según la versión del admin center:

### Opción 1: En la pestaña "Correo" del usuario

1. Ve a: https://admin.microsoft.com
2. **Usuarios** → **Usuarios activos**
3. Busca y haz clic en **info@example.com**
4. Haz clic en la pestaña **"Correo"** (no "General")
5. Busca la sección **"Autenticación SMTP básica"** o **"SMTP AUTH"**
6. Habilita la opción
7. Guarda los cambios

### Opción 2: En "Aplicaciones de correo electrónico"

1. En la página del usuario info@example.com
2. Busca la sección **"Aplicaciones de correo electrónico"**
3. Haz clic en **"Administrar aplicaciones de correo"**
4. Busca **"Autenticación SMTP básica"** o **"Otras aplicaciones de correo electrónico permitidas"**
5. Habilita la opción
6. Guarda los cambios

### Opción 3: En Exchange Admin Center (más detallado)

1. Ve a: https://admin.exchange.microsoft.com
2. **Destinatarios** → **Buzones**
3. Busca **info@example.com**
4. Haz doble clic para abrir las propiedades
5. Ve a la pestaña **"Correo"** o **"Funciones de buzón"**
6. Busca **"Autenticación SMTP básica"**
7. Habilita la opción
8. Guarda los cambios

### Opción 4: Usando PowerShell (más rápido)

Si tienes acceso a PowerShell:

```powershell
# Conectar a Exchange Online
Connect-ExchangeOnline

# Habilitar SMTP AUTH para el usuario
Set-CASMailbox -Identity "info@example.com" -SmtpClientAuthenticationDisabled $false

# Verificar que está habilitado
Get-CASMailbox -Identity "info@example.com" | Select SmtpClientAuthenticationDisabled
```

## Verificación

Después de habilitar:

1. Espera 5-10 minutos para que los cambios se propaguen
2. Prueba el envío desde `/admin/email`
3. Si aún falla, verifica que la opción esté realmente habilitada

## Nota Importante

- Si no ves la opción, puede que necesites permisos de administrador
- Algunos planes de Office 365 pueden tener esta opción en diferentes ubicaciones
- Si tienes MFA activado, puede que también necesites una contraseña de aplicación
