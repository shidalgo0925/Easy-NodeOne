# EPosOne APK (hospedado en EN1)

Ruta canónica del archivo:

```text
static/apk/eposone/EPosOne.apk
```

URL pública (prod producto):

```text
https://eposone.easytech.services/static/apk/eposone/EPosOne.apk
```

El binario **no** se versiona en Git (`*.apk` en `.gitignore`). Se sube al silo por SCP/SFTP.

## Subir desde Windows (Git Bash)

Servidor EN1 (SSH config):

```text
Host Codito-contabo-dev
    HostName 194.60.201.29
    User dev
    IdentityFile C:/Users/shidalgo/.ssh/id_ed25519
    IdentitiesOnly yes
    PreferredAuthentications publickey
```

**Prod** (eposone.easytech.services):

```bash
scp "C:/Users/shidalgo/Downloads/EPosOne.apk" \
  Codito-contabo-dev:/opt/easynodeone/prod/app/static/apk/eposone/EPosOne.apk
```

Si la carpeta no existe o falla por permisos:

```bash
ssh Codito-contabo-dev "mkdir -p /opt/easynodeone/prod/app/static/apk/eposone"
scp "C:/Users/shidalgo/Downloads/EPosOne.apk" \
  Codito-contabo-dev:/opt/easynodeone/prod/app/static/apk/eposone/EPosOne.apk
ssh Codito-contabo-dev "chmod 644 /opt/easynodeone/prod/app/static/apk/eposone/EPosOne.apk"
```

**Dev EN1** (appdev, opcional):

```bash
scp "C:/Users/shidalgo/Downloads/EPosOne.apk" \
  Codito-contabo-dev:/opt/easynodeone/dev/app/static/apk/eposone/EPosOne.apk
```
## Variables de entorno (opcional)

| Variable | Uso |
|----------|-----|
| `NODEONE_EPOSONE_APK_URL` | URL absoluta o relativa del APK (prioridad) |
| `NODEONE_EPOSONE_PLAY_STORE_URL` | Solo si se quiere forzar Play Store |

Sin env: default `/static/apk/eposone/EPosOne.apk`.
