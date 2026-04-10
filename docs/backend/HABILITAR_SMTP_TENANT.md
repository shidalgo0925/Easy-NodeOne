# Habilitar SMTP AUTH a Nivel de Tenant (Organización)

## Problema

El error `5.7.139 SmtpClientAuthentication is disabled for the Tenant` indica que SMTP AUTH está deshabilitado **a nivel de toda la organización**, no solo del usuario.

Aunque habilitaste "SMTP autenticado" para el usuario individual, necesitas habilitarlo también a nivel de tenant.

## Solución: Habilitar SMTP AUTH a Nivel de Tenant

### Opción 1: Exchange Admin Center (Recomendado)

1. **Ve a Exchange Admin Center:**
   - https://admin.exchange.microsoft.com
   - Inicia sesión con una cuenta de administrador

2. **Habilitar SMTP AUTH para la organización:**
   - Ve a **Configuración** → **Correo** → **Autenticación**
   - Busca **"Autenticación SMTP básica"** o **"SMTP AUTH"**
   - Habilita la opción para **"Toda la organización"** o **"Usuarios específicos"**
   - Si eliges usuarios específicos, agrega `info@example.com`
   - Guarda los cambios

### Opción 2: PowerShell (Más Directo)

Si tienes acceso a PowerShell de Exchange Online:

```powershell
# Conectar a Exchange Online
Connect-ExchangeOnline

# Habilitar SMTP AUTH para toda la organización
Set-TransportConfig -SmtpClientAuthenticationDisabled $false

# O habilitar solo para usuarios específicos
Set-CASMailbox -Identity "info@example.com" -SmtpClientAuthenticationDisabled $false

# Verificar configuración
Get-TransportConfig | Select SmtpClientAuthenticationDisabled
Get-CASMailbox -Identity "info@example.com" | Select SmtpClientAuthenticationDisabled
```

### Opción 3: Microsoft 365 Admin Center

1. **Ve a:** https://admin.microsoft.com
2. **Configuración** → **Configuración de la organización**
3. **Correo** → **Autenticación**
4. Busca **"Autenticación SMTP básica"**
5. Habilita para **"Toda la organización"** o **"Usuarios específicos"**
6. Guarda los cambios

## Verificación

Después de habilitar:

1. **Espera 15-30 minutos** para que los cambios se propaguen
2. Prueba de nuevo desde `/admin/email`
3. El error debería desaparecer

## Nota Importante

- Necesitas permisos de **Administrador Global** o **Administrador de Exchange**
- Los cambios pueden tardar hasta 30 minutos en propagarse
- Si no tienes estos permisos, contacta al administrador de Microsoft 365

## Alternativa: Usar Microsoft Graph API

Si no puedes habilitar SMTP AUTH, puedes usar Microsoft Graph API para enviar emails (requiere más configuración pero es más seguro).
