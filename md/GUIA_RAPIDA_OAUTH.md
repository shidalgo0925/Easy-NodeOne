# 🚀 Guía Rápida: Configurar Login Social (OAuth)

## ⚡ Configuración Rápida de Google OAuth

### **Paso 1: Obtener Credenciales de Google**

1. Ve a [Google Cloud Console](https://console.cloud.google.com/)
2. Crea o selecciona un proyecto
3. Ve a **APIs & Services** > **Credentials**
4. Haz clic en **+ CREATE CREDENTIALS** > **OAuth client ID**
5. Si es la primera vez, configura la pantalla de consentimiento OAuth
6. Selecciona **Web application**
7. Configura:
   - **Name**: RelaticPanama
   - **Authorized JavaScript origins**: 
     - `https://miembros.relatic.org`
   - **Authorized redirect URIs**:
     - `https://miembros.relatic.org/auth/google/callback`

8. Copia el **Client ID** y **Client Secret**

### **Paso 2: Configurar en el Sistema**

Tienes dos opciones:

#### **Opción A: Variables de Entorno (Recomendado)**

Agrega al archivo `.env` en la raíz del proyecto:

```bash
GOOGLE_CLIENT_ID=tu-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=tu-client-secret
BASE_URL=https://miembros.relatic.org
```

Luego reinicia el servicio:
```bash
sudo systemctl restart membresia-relatic.service
```

#### **Opción B: Configuración Directa en app.py**

Edita `backend/app.py` líneas 94-95:

```python
app.config['GOOGLE_CLIENT_ID'] = 'tu-client-id.apps.googleusercontent.com'
app.config['GOOGLE_CLIENT_SECRET'] = 'tu-client-secret'
```

### **Paso 3: Verificar**

1. Reinicia el servicio
2. Ve a `/login`
3. Haz clic en el botón "Google"
4. Deberías ser redirigido a Google para autorizar

---

## 📝 Notas Importantes

- **Nunca commitees** las credenciales en git
- Las URLs de callback deben coincidir **exactamente** con las configuradas en Google
- Para desarrollo local, agrega también `http://localhost:9000/auth/google/callback` en Google Console

---

## 🔗 Enlaces Útiles

- [Google Cloud Console](https://console.cloud.google.com/)
- [Documentación Completa](./docs/CONFIGURACION_LOGIN_SOCIAL.md)

---

**¿Necesitas ayuda?** Revisa la documentación completa en `docs/CONFIGURACION_LOGIN_SOCIAL.md`




