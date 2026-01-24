# 🔐 Configuración de Login Social (OAuth)

Este documento explica cómo configurar el login social con Google, Facebook y LinkedIn.

---

## 📋 Requisitos Previos

1. **Authlib instalado**: `pip install authlib==1.3.0`
2. **Credenciales OAuth** de cada proveedor
3. **Variables de entorno** configuradas

---

## 🔧 Configuración por Proveedor

### **1. Google OAuth**

#### **Paso 1: Crear Proyecto en Google Cloud Console**
1. Ve a [Google Cloud Console](https://console.cloud.google.com/)
2. Crea un nuevo proyecto o selecciona uno existente
3. Habilita la API "Google+ API" o "People API"

#### **Paso 2: Crear Credenciales OAuth 2.0**
1. Ve a **APIs & Services** > **Credentials**
2. Haz clic en **Create Credentials** > **OAuth client ID**
3. Selecciona **Web application**
4. Configura:
   - **Name**: RelaticPanama Login
   - **Authorized JavaScript origins**: 
     - `https://miembros.relatic.org`
     - `http://localhost:9000` (para desarrollo)
   - **Authorized redirect URIs**:
     - `https://miembros.relatic.org/auth/google/callback`
     - `http://localhost:9000/auth/google/callback` (para desarrollo)

#### **Paso 3: Obtener Credenciales**
- **Client ID**: Copia el Client ID
- **Client Secret**: Copia el Client Secret

#### **Paso 4: Configurar Variables de Entorno**
```bash
export GOOGLE_CLIENT_ID="tu-client-id.apps.googleusercontent.com"
export GOOGLE_CLIENT_SECRET="tu-client-secret"
```

---

### **2. Facebook OAuth**

#### **Paso 1: Crear App en Facebook Developers**
1. Ve a [Facebook Developers](https://developers.facebook.com/)
2. Crea una nueva app
3. Selecciona tipo "Consumer" o "Business"

#### **Paso 2: Configurar Facebook Login**
1. En el dashboard, agrega el producto **Facebook Login**
2. Configura:
   - **Valid OAuth Redirect URIs**:
     - `https://miembros.relatic.org/auth/facebook/callback`
     - `http://localhost:9000/auth/facebook/callback` (para desarrollo)

#### **Paso 3: Obtener Credenciales**
- Ve a **Settings** > **Basic**
- **App ID**: Tu Client ID
- **App Secret**: Tu Client Secret (haz clic en "Show")

#### **Paso 4: Configurar Variables de Entorno**
```bash
export FACEBOOK_CLIENT_ID="tu-app-id"
export FACEBOOK_CLIENT_SECRET="tu-app-secret"
```

---

### **3. LinkedIn OAuth**

#### **Paso 1: Crear App en LinkedIn Developers**
1. Ve a [LinkedIn Developers](https://www.linkedin.com/developers/)
2. Crea una nueva app
3. Completa la información requerida

#### **Paso 2: Configurar Redirect URLs**
1. Ve a **Auth** en la configuración de tu app
2. Agrega **Redirect URLs**:
   - `https://miembros.relatic.org/auth/linkedin/callback`
   - `http://localhost:9000/auth/linkedin/callback` (para desarrollo)

#### **Paso 3: Obtener Credenciales**
- **Client ID**: En la sección **Auth**
- **Client Secret**: Genera un nuevo secret si es necesario

#### **Paso 4: Configurar Variables de Entorno**
```bash
export LINKEDIN_CLIENT_ID="tu-client-id"
export LINKEDIN_CLIENT_SECRET="tu-client-secret"
```

---

## 🔐 Configuración en el Sistema

### **Opción 1: Variables de Entorno (Recomendado)**

Agrega las variables al archivo `.env` o configuración del sistema:

```bash
# Google OAuth
GOOGLE_CLIENT_ID=tu-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=tu-client-secret

# Facebook OAuth
FACEBOOK_CLIENT_ID=tu-app-id
FACEBOOK_CLIENT_SECRET=tu-app-secret

# LinkedIn OAuth
LINKEDIN_CLIENT_ID=tu-client-id
LINKEDIN_CLIENT_SECRET=tu-client-secret

# Base URL (importante para callbacks)
BASE_URL=https://miembros.relatic.org
```

### **Opción 2: Configuración Directa en app.py**

Puedes modificar directamente en `backend/app.py`:

```python
app.config['GOOGLE_CLIENT_ID'] = 'tu-client-id'
app.config['GOOGLE_CLIENT_SECRET'] = 'tu-client-secret'
# ... etc
```

---

## ✅ Verificación

### **1. Verificar Instalación**
```bash
cd /home/relaticpanama2025/projects/membresia-relatic
source venv/bin/activate
python -c "import authlib; print('✅ Authlib instalado')"
```

### **2. Verificar Configuración**
1. Inicia el servidor
2. Ve a `/login` o `/register`
3. Deberías ver los botones de login social
4. Si no están configurados, verás mensajes de error al hacer clic

### **3. Probar Login Social**
1. Haz clic en un botón de login social (ej: Google)
2. Deberías ser redirigido al proveedor
3. Autoriza la aplicación
4. Deberías ser redirigido de vuelta y autenticado

---

## 🔍 Troubleshooting

### **Error: "Login social no está disponible"**
- **Causa**: Authlib no está instalado
- **Solución**: `pip install authlib==1.3.0`

### **Error: "Login con [proveedor] no está configurado"**
- **Causa**: Faltan credenciales OAuth
- **Solución**: Configura las variables de entorno correspondientes

### **Error: "redirect_uri_mismatch"**
- **Causa**: La URL de callback no coincide con la configurada en el proveedor
- **Solución**: Verifica que las URLs en el proveedor coincidan exactamente con `BASE_URL/auth/[proveedor]/callback`

### **Error: "invalid_client"**
- **Causa**: Client ID o Secret incorrectos
- **Solución**: Verifica las credenciales en las variables de entorno

---

## 📝 Notas Importantes

1. **Seguridad**: Nunca commitees las credenciales OAuth en el repositorio
2. **Callbacks**: Las URLs de callback deben ser HTTPS en producción
3. **Scopes**: Los scopes solicitados están configurados para obtener email y perfil básico
4. **Email Verificado**: Los usuarios de login social tienen `email_verified=True` automáticamente
5. **Sin Password**: Los usuarios de login social no tienen password_hash (nullable)

---

## 🚀 Próximos Pasos

Una vez configurado el login social, puedes:
1. Probar el login con cada proveedor
2. Verificar que se crean usuarios correctamente
3. Verificar que se vinculan cuentas existentes
4. Configurar SSO (Single Sign-On) si es necesario

---

**Última actualización**: Diciembre 2025




