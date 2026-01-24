# Configuración de Gmail con Contraseña de Aplicación

## Requisitos Previos

1. **Cuenta de Gmail** activa
2. **Verificación en 2 pasos** habilitada en tu cuenta de Google
3. **Contraseña de aplicación** generada

## Pasos para Configurar

### 1. Habilitar Verificación en 2 Pasos

Si aún no tienes la verificación en 2 pasos habilitada:

1. Ve a: https://myaccount.google.com/security
2. Busca **"Verificación en 2 pasos"**
3. Sigue las instrucciones para habilitarla

### 2. Generar Contraseña de Aplicación

1. Ve a: https://myaccount.google.com/apppasswords
2. Inicia sesión si es necesario
3. En **"Seleccionar app"**, elige **"Correo"**
4. En **"Seleccionar dispositivo"**, elige **"Otro (nombre personalizado)"**
5. Escribe: `RelaticPanama` o el nombre que prefieras
6. Haz clic en **"Generar"**
7. **Copia la contraseña de 16 caracteres** (aparecerá en pantalla)

⚠️ **IMPORTANTE**: Esta contraseña solo se muestra una vez. Guárdala en un lugar seguro.

### 3. Configurar en el Sistema

Ejecuta el script de configuración:

```bash
cd /home/relaticpanama2025/projects/membresia-relatic/backend
python3 configure_gmail.py
```

O si prefieres hacerlo directamente desde Python:

```python
from app import app, db, EmailConfig
from datetime import datetime

with app.app_context():
    EmailConfig.query.update({'is_active': False})
    config = EmailConfig.query.first()
    
    if not config:
        config = EmailConfig(
            mail_server='smtp.gmail.com',
            mail_port=587,
            mail_use_tls=True,
            mail_use_ssl=False,
            mail_username='tuemail@gmail.com',
            mail_password='tu_contraseña_de_aplicación',
            mail_default_sender='tuemail@gmail.com',
            use_environment_variables=False,
            is_active=True
        )
        db.session.add(config)
    else:
        config.mail_server = 'smtp.gmail.com'
        config.mail_port = 587
        config.mail_use_tls = True
        config.mail_use_ssl = False
        config.mail_username = 'tuemail@gmail.com'
        config.mail_password = 'tu_contraseña_de_aplicación'
        config.mail_default_sender = 'tuemail@gmail.com'
        config.use_environment_variables = False
        config.is_active = True
        config.updated_at = datetime.utcnow()
    
    db.session.commit()
```

### 4. Reiniciar el Servicio

Después de configurar, reinicia el servicio:

```bash
sudo systemctl restart membresia-relatic.service
```

### 5. Probar el Envío

1. Ve al panel de administración: `/admin/email`
2. Haz clic en **"Probar Envío"**
3. Ingresa un email de prueba
4. Verifica que recibas el correo

O ejecuta el script de prueba:

```bash
python3 backend/test_email_send.py
```

## Configuración SMTP de Gmail

- **Servidor SMTP**: `smtp.gmail.com`
- **Puerto**: `587` (TLS) o `465` (SSL)
- **Seguridad**: TLS (recomendado) o SSL
- **Autenticación**: Requerida
- **Usuario**: Tu email completo de Gmail
- **Contraseña**: Contraseña de aplicación (16 caracteres)

## Solución de Problemas

### Error: "Username and Password not accepted"

- Verifica que la verificación en 2 pasos esté habilitada
- Asegúrate de usar la **contraseña de aplicación**, no tu contraseña normal
- Verifica que copiaste correctamente los 16 caracteres (sin espacios)

### Error: "Less secure app access"

- Gmail ya no permite "aplicaciones menos seguras"
- **Siempre** debes usar una contraseña de aplicación cuando tengas 2FA habilitado

### No recibo correos

- Revisa la carpeta de spam
- Verifica que el email de destino sea correcto
- Revisa los logs del servidor: `sudo journalctl -u membresia-relatic.service -n 50`

## Notas Importantes

- La contraseña de aplicación es específica para esta aplicación
- Puedes generar múltiples contraseñas de aplicación para diferentes servicios
- Si revocas una contraseña de aplicación, deberás generar una nueva
- La contraseña de aplicación no es tu contraseña de Gmail

## Referencias

- [Contraseñas de aplicación de Google](https://support.google.com/accounts/answer/185833)
- [Configuración SMTP de Gmail](https://support.google.com/mail/answer/7126229)

