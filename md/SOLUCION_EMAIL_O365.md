# Solución: Problema de Autenticación SMTP con Office 365

## Problema Detectado

El sistema está configurado correctamente, pero Office 365 está rechazando la autenticación SMTP con el siguiente error:

```
535, b'5.7.139 Authentication unsuccessful, SmtpClientAuthentication is disabled for the Tenant.
```

## Causa

La autenticación SMTP está **deshabilitada** en el tenant de Office 365. Esto es una configuración de seguridad de Microsoft que debe habilitarse manualmente.

## Solución

### Opción 1: Habilitar SMTP AUTH en Office 365 (Recomendado)

1. **Acceder al Centro de administración de Microsoft 365:**
   - Ve a https://admin.microsoft.com
   - Inicia sesión con una cuenta de administrador

2. **Habilitar SMTP AUTH para el tenant:**
   - Ve a **Configuración** > **Configuración de correo**
   - O directamente a: https://admin.microsoft.com/AdminPortal/Home#/Settings/Services/mail
   - Busca la opción **"Autenticación SMTP"** o **"SMTP AUTH"**
   - Habilita la autenticación SMTP para el tenant

3. **Habilitar SMTP AUTH para el usuario específico:**
   - Ve a **Usuarios activos**
   - Selecciona el usuario `info@relaticpanama.org`
   - Ve a la pestaña **Correo**
   - Habilita **"Autenticación SMTP habilitada"**

### Opción 2: Usar Microsoft Graph API (Alternativa moderna)

Si no puedes habilitar SMTP AUTH, puedes usar Microsoft Graph API para enviar emails. Esto requiere:
- Registrar una aplicación en Azure AD
- Obtener un token de acceso
- Usar la API de Microsoft Graph para enviar emails

### Opción 3: Usar un servicio de email externo

Alternativas:
- **SendGrid** (gratis hasta 100 emails/día)
- **Mailgun** (gratis hasta 5,000 emails/mes)
- **Amazon SES** (muy económico)
- **Gmail con App Password** (si tienes una cuenta Gmail)

## Verificación

Después de habilitar SMTP AUTH, prueba el envío desde:
- Panel de administración: `/admin/email` > Botón "Probar Envío"
- O ejecuta: `python3 backend/test_email_send.py`

## Notas Importantes

- La habilitación de SMTP AUTH puede tardar hasta 24 horas en aplicarse
- Algunos tenants de Office 365 tienen políticas de seguridad que bloquean SMTP AUTH por completo
- Si no puedes habilitar SMTP AUTH, considera usar Microsoft Graph API o un servicio externo

## Referencias

- [Documentación de Microsoft sobre SMTP AUTH](https://aka.ms/smtp_auth_disabled)
- [Habilitar SMTP AUTH en Office 365](https://learn.microsoft.com/en-us/exchange/clients-and-mobile-in-exchange-online/authenticated-client-smtp-submission)

