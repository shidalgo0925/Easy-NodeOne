# Instrucciones para Subir el QR de Yappy

## Desde Windows al Servidor Linux

### Opción 1: Usando SCP (desde Git Bash o Terminal)

```bash
# Desde Git Bash en Windows (usando la clave SSH)
scp -i ~/.ssh/deploy-key "C:\Users\shida\Documents\0. Tecnologia\10. Easy NodeOne\Imagenes\qr.JPG" nodeone@34.66.214.83:/var/www/nodeone/static/images/yappy-qr-multiserviciostk.png
```

**Nota:** Si `~/.ssh/deploy-key` no funciona, usa la ruta completa:
```bash
scp -i /c/Users/shida/.ssh/deploy-key "C:\Users\shida\Documents\0. Tecnologia\10. Easy NodeOne\Imagenes\qr.JPG" nodeone@34.66.214.83:/var/www/nodeone/static/images/yappy-qr-multiserviciostk.png
```

### Opción 2: Usando WinSCP (Interfaz Gráfica)

1. Abre WinSCP
2. Conecta al servidor: `34.66.214.83`
3. Usuario: `nodeone`
4. Navega a: `/var/www/nodeone/static/images/`
5. Arrastra el archivo `qr.JPG` desde tu carpeta
6. Renómbralo a: `yappy-qr-multiserviciostk.png`

### Opción 3: Usando FileZilla (FTP/SFTP)

1. Abre FileZilla
2. Conecta por SFTP a: `34.66.214.83`
3. Usuario: `nodeone`
4. Navega a: `/var/www/nodeone/static/images/`
5. Sube `qr.JPG` y renómbralo a `yappy-qr-multiserviciostk.png`

## Después de subir

El archivo debe quedar en:
`/var/www/nodeone/static/images/yappy-qr-multiserviciostk.png`

**Nota:** Si subes como JPG, el servidor lo convertirá automáticamente o puedes renombrarlo a .png (los navegadores aceptan JPG con extensión PNG).


