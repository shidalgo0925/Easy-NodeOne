# 📊 Análisis de Estructura - nodeone

## 🎯 Resumen General

**Proyecto:** Sistema de Membresía Easy NodeOne  
**Tecnología:** Flask (Python) + SQLite/PostgreSQL  
**Estado:** En desarrollo activo  
**Ubicación:** `/var/www/nodeone`

---

## 📁 Estructura de Directorios

```
nodeone/
├── backend/                    # Código Python del backend
│   ├── app.py                 # Aplicación Flask principal (569 líneas)
│   ├── event_routes.py        # Rutas de eventos/citas (1276+ líneas)
│   ├── remove_duplicates.py   # Script de limpieza de BD
│   └── instance/              # Base de datos SQLite
│       └── membership_legacy.db
│
├── templates/                  # Templates HTML (Jinja2)
│   ├── base.html              # Template base con sidebar
│   ├── index.html             # Página principal
│   ├── login.html             # Login
│   ├── register.html          # Registro
│   ├── dashboard.html          # Dashboard usuario
│   ├── membership.html         # Gestión de membresía
│   ├── benefits.html           # Beneficios
│   ├── services.html           # Servicios
│   ├── office365.html          # Office 365
│   ├── profile.html            # Perfil usuario
│   ├── settings.html           # Configuración
│   ├── notifications.html      # Notificaciones
│   ├── help.html               # Ayuda
│   ├── checkout.html           # Checkout pagos
│   ├── payment_success.html    # Éxito pago
│   ├── subscription_form.html  # Formulario suscripción
│   │
│   ├── admin/                  # Templates administrativos
│   │   ├── dashboard.html      # Panel admin
│   │   ├── users.html          # Gestión usuarios
│   │   └── memberships.html    # Gestión membresías
│   │
│   └── events/                 # Templates de eventos
│       ├── list.html           # Lista de eventos
│       └── detail.html         # Detalle evento
│
├── static/                     # Archivos estáticos
│   ├── css/
│   │   └── custom.css          # Estilos personalizados
│   └── images/
│       ├── favicon.svg         # Favicon (nueva paleta)
│       └── logo-primary.svg    # Logo (nueva paleta)
│
├── venv/                       # Entorno virtual Python
├── instance/                   # Base de datos (alternativa)
├── requirements.txt            # Dependencias Python
├── config.py                   # Configuración
├── README.md                   # Documentación principal
└── *.sh                        # Scripts de gestión
```

---

## 🔧 Componentes Principales

### 1. Backend (`backend/app.py`)

#### Modelos de Base de Datos:
- **User**: Usuarios del sistema
  - Campos: email, password_hash, first_name, last_name, phone, is_admin
  - Relaciones: memberships, payments, subscriptions
  
- **Membership**: Membresías (sistema legacy)
  - Campos: user_id, membership_type, start_date, end_date, is_active, payment_status
  
- **Subscription**: Suscripciones activas (sistema nuevo)
  - Campos: user_id, payment_id, membership_type, status, start_date, end_date, auto_renew
  
- **Payment**: Registro de pagos
  - Campos: user_id, stripe_payment_intent_id, amount, currency, status
  
- **Benefit**: Beneficios por tipo de membresía
  - Campos: name, description, membership_type, is_active

#### Rutas Principales:
- **Públicas:**
  - `/` - Página principal
  - `/register` - Registro
  - `/login` - Login
  
- **Autenticadas:**
  - `/dashboard` - Dashboard usuario
  - `/membership` - Gestión membresía
  - `/benefits` - Beneficios
  - `/services` - Servicios
  - `/office365` - Office 365
  - `/profile` - Perfil
  - `/settings` - Configuración
  - `/notifications` - Notificaciones
  - `/help` - Ayuda
  
- **Pagos:**
  - `/checkout/<membership_type>` - Checkout
  - `/create-payment-intent` - Crear Payment Intent (Stripe)
  - `/payment-success` - Éxito pago
  - `/payment-cancel` - Cancelación pago
  - `/stripe-webhook` - Webhook Stripe
  
- **API:**
  - `/api/user/membership` - Info membresía usuario
  
- **Administración:**
  - `/admin` - Panel admin (requiere `is_admin=True`)
  - `/admin/users` - Gestión usuarios
  - `/admin/memberships` - Gestión membresías

#### Funcionalidades:
- ✅ Autenticación con Flask-Login
- ✅ Sistema de membresías (4 tipos: basic, pro, premium, deluxe)
- ✅ Integración Stripe (modo demo y producción)
- ✅ Envío de emails (Flask-Mail)
- ✅ Decorador `@admin_required` para rutas admin

---

### 2. Eventos (`backend/event_routes.py`)

#### Blueprints:
- **`events_bp`** (`/events`) - Portal de miembros
- **`admin_events_bp`** (`/admin/events`) - Panel administrativo
- **`events_api_bp`** (`/api/events`) - API pública JSON

#### Modelos Referenciados (no definidos en app.py):
- **Event**: Eventos/citas
- **EventImage**: Imágenes de eventos
- **Discount**: Descuentos
- **EventDiscount**: Relación eventos-descuentos
- **ActivityLog**: Log de actividades

#### Rutas de Eventos:
- **Miembros:**
  - `GET /events/` - Lista de eventos
  - `GET /events/<slug>` - Detalle evento
  
- **Admin:**
  - `GET /admin/events/` - Lista eventos (admin)
  - `GET /admin/events/create` - Crear evento
  - `POST /admin/events/create` - Guardar evento
  - `GET /admin/events/<id>/edit` - Editar evento
  - `POST /admin/events/<id>/edit` - Actualizar evento
  - `POST /admin/events/<id>/delete` - Eliminar evento
  - `GET /admin/events/discounts` - Lista descuentos
  - `GET /admin/events/discounts/create` - Crear descuento
  - `GET /admin/events/discounts/<id>/edit` - Editar descuento
  - `POST /admin/events/discounts/<id>/delete` - Eliminar descuento
  
- **API:**
  - `GET /api/events/` - Lista eventos (JSON)
  - `GET /api/events/<slug>` - Detalle evento (JSON)

#### Problemas Identificados:
⚠️ **CRÍTICO:** `event_routes.py` importa modelos que NO están definidos en `app.py`:
- `Event`, `EventImage`, `Discount`, `EventDiscount`, `ActivityLog`
- También importa `admin_decorators.admin_required` que no existe
- Los modelos se inicializan dinámicamente con `init_models()` pero nunca se definen

⚠️ **FALTA:** Templates administrativos de eventos:
- `templates/admin/events/list.html`
- `templates/admin/events/form.html`
- `templates/admin/events/discount_list.html`
- `templates/admin/events/discount_form.html`

---

### 3. Frontend (Templates)

#### Template Base (`templates/base.html`):
- ✅ Navbar con logo Easy NodeOne
- ✅ Sidebar lateral (estilo Sufee) - **VISIBLE en Dashboard**
- ✅ Sistema de bloques Jinja2 (`{% block content %}`)
- ✅ Flash messages
- ✅ Footer
- ✅ Favicon y logo SVG (nueva paleta de colores)
- ✅ CSS variables para paleta de colores
- ✅ JavaScript para toggle sidebar

#### Paleta de Colores Implementada:
```css
--yellow-top: #FFD700
--orange-bottom: #FF8C00
--cyan-top: #00CED1
--turquoise-bottom: #40E0D0
--royal-blue: #4169E1
--black: #000000
```

#### Templates por Categoría:

**Públicos:**
- `index.html` - Landing page
- `login.html` - Login
- `register.html` - Registro

**Usuario Autenticado:**
- `dashboard.html` - Dashboard principal
- `membership.html` - Gestión membresía
- `benefits.html` - Lista de beneficios
- `services.html` - Servicios disponibles
- `office365.html` - Office 365
- `profile.html` - Perfil usuario
- `settings.html` - Configuración
- `notifications.html` - Notificaciones
- `help.html` - Ayuda

**Pagos:**
- `checkout.html` - Checkout Stripe
- `payment_success.html` - Confirmación pago
- `subscription_form.html` - Formulario suscripción $30

**Eventos:**
- `events/list.html` - Lista eventos
- `events/detail.html` - Detalle evento

**Admin:**
- `admin/dashboard.html` - Panel admin
- `admin/users.html` - Gestión usuarios
- `admin/memberships.html` - Gestión membresías
- ⚠️ **FALTAN:** `admin/events/*.html`

---

## 📊 Estadísticas del Código

- **Archivos Python:** 3
  - `app.py`: ~569 líneas
  - `event_routes.py`: ~1276+ líneas (con código duplicado)
  - `remove_duplicates.py`: Script auxiliar

- **Templates HTML:** 21 archivos
- **Archivos CSS:** 1 (`custom.css`)
- **Archivos JavaScript:** 0 (inline en templates)
- **Archivos de Imagen:** 2 SVG (favicon, logo)

---

## ⚠️ Problemas Identificados

### 1. Modelos Faltantes en `app.py`
Los siguientes modelos son referenciados en `event_routes.py` pero NO están definidos:
- `Event`
- `EventImage`
- `Discount`
- `EventDiscount`
- `ActivityLog`

**Solución:** Definir estos modelos en `app.py` o crear un archivo `models.py` separado.

### 2. Decorador Faltante
`event_routes.py` importa `admin_decorators.admin_required` que no existe.

**Solución:** El decorador `admin_required` está definido en `app.py` (línea 495), pero `event_routes.py` intenta importarlo desde un módulo separado.

### 3. Templates Faltantes
Faltan templates para el panel admin de eventos:
- `templates/admin/events/list.html`
- `templates/admin/events/form.html`
- `templates/admin/events/discount_list.html`
- `templates/admin/events/discount_form.html`

### 4. Blueprints No Registrados
Los blueprints de eventos (`events_bp`, `admin_events_bp`, `events_api_bp`) probablemente no están registrados en `app.py`.

**Solución:** Agregar en `app.py`:
```python
from event_routes import events_bp, admin_events_bp, events_api_bp
app.register_blueprint(events_bp)
app.register_blueprint(admin_events_bp)
app.register_blueprint(events_api_bp)
```

### 5. Código Duplicado
`event_routes.py` contiene código duplicado (múltiples definiciones del mismo archivo).

---

## ✅ Funcionalidades Implementadas

- ✅ Sistema de autenticación completo
- ✅ Gestión de membresías (3 tipos)
- ✅ Integración Stripe (modo demo)
- ✅ Panel administrativo básico (usuarios, membresías)
- ✅ Sidebar lateral funcional
- ✅ Paleta de colores nueva implementada
- ✅ Favicon y logo SVG
- ✅ Sistema de beneficios
- ✅ Módulos: Services, Office365, Profile, Settings, Notifications, Help

---

## 🚧 Pendientes

1. **Definir modelos de eventos** en `app.py`
2. **Registrar blueprints** de eventos en `app.py`
3. **Crear templates** administrativos de eventos
4. **Corregir importaciones** en `event_routes.py`
5. **Limpiar código duplicado** en `event_routes.py`
6. **Conectar panel admin de eventos** completamente

---

## 📦 Dependencias

```
Flask==2.3.3
Flask-SQLAlchemy==3.0.5
Flask-Login==0.6.3
Werkzeug==2.3.7
python-dotenv==1.0.0
gunicorn==21.2.0
psycopg2-binary==2.9.7
stripe==7.8.0
Flask-Mail==0.9.1
requests==2.31.0
```

---

## 🔗 Enlaces Importantes

- **Dominio:** app.example.com
- **Puerto:** 9000 (desarrollo) / 8080 (producción)
- **Base de datos:** SQLite (`backend/instance/membership_legacy.db`)

---

**Última actualización:** $(date)
**Análisis generado por:** Auto (Cursor AI)

