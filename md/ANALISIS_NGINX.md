# Análisis de Configuración Nginx

**Fecha:** $(date)
**Servidor:** 34.66.214.83

---

## 📋 Resumen de Configuración

### Sitios Habilitados (`/etc/nginx/sites-enabled/`)

1. **01-dev.relatic.org** ✅
   - **Subdominio:** dev.relatic.org
   - **Puerto Backend:** 5173 (relatic-frontend - Vite)
   - **SSL:** ✅ Certificado Let's Encrypt
   - **Estado:** ✅ Configurado correctamente
   - **Proxy:** http://localhost:5173
   - **Headers:** WebSocket y HMR habilitados
   - **Buffering:** Desactivado (desarrollo)

2. **02-miembros.relatic.org** ✅
   - **Subdominio:** miembros.relatic.org
   - **Puerto Backend:** 9000 (membresia-relatic - Flask)
   - **SSL:** ✅ Certificado Let's Encrypt
   - **Estado:** ✅ Configurado correctamente
   - **Proxy:** http://localhost:9000
   - **Headers:** WebSocket habilitado
   - **Buffering:** Activado (producción)

3. **helpdesk** ✅
   - **Subdominio:** helpdesk.etsrv.site
   - **Puerto Frontend:** 3001
   - **Puerto Backend API:** 8001
   - **SSL:** ✅ Certificado Let's Encrypt
   - **Estado:** ✅ Configurado correctamente

4. **apps.etsrv.site** ✅
   - **Subdominio:** apps.etsrv.site
   - **Puerto Backend:** 5001
   - **SSL:** ✅ Certificado Let's Encrypt
   - **Estado:** ✅ Configurado correctamente

5. **waconnect.etsrv.site** ⚠️
   - **Estado:** Habilitado pero no revisado

6. **waconnect.site** ⚠️
   - **Estado:** Habilitado pero no revisado

---

## 🔍 Análisis Detallado

### Configuración Principal (`nginx.conf`)

- **Worker Processes:** auto
- **Worker Connections:** 768
- **Log Format:** `debug_host` (incluye Host header)
- **Gzip:** Activado
- **SSL Protocols:** TLSv1, TLSv1.1, TLSv1.2, TLSv1.3

### Configuración de Cloudflare

Todos los sitios de `relatic.org` tienen configurados:
- **IPs de Cloudflare:** IPv4 e IPv6 ranges completos
- **Real IP Header:** CF-Connecting-IP
- **Headers Proxy:** CF-Ray, CF-Visitor, CF-Connecting-IP

### SSL/TLS

- **Certificados:** Let's Encrypt (Certbot)
- **Protocolos:** TLSv1.2 y TLSv1.3
- **Redirección HTTP → HTTPS:** ✅ Configurada en todos los sitios

---

## ✅ Estado Actual

### Configuración Correcta

1. **dev.relatic.org** → **relatic-frontend (5173)** ✅
   - Proxy correcto
   - Headers WebSocket configurados
   - SSL funcionando

2. **miembros.relatic.org** → **membresia-relatic (9000)** ✅
   - Proxy correcto
   - Headers configurados
   - SSL funcionando

### Posibles Problemas

1. **Orden de Carga:**
   - Los archivos tienen prefijos numéricos (01-, 02-) para controlar el orden
   - ✅ Orden correcto: dev.relatic.org primero, luego miembros.relatic.org

2. **Conflictos de Puerto:**
   - ✅ No hay conflictos: cada servicio usa puerto diferente
   - 5173: relatic-frontend
   - 9000: membresia-relatic
   - 3001: helpdesk-frontend
   - 8001: helpdesk-backend
   - 5001: apps.etsrv.site

3. **Logs:**
   - ✅ Logs separados por dominio
   - Formato `debug_host` para debugging

---

## 🔧 Recomendaciones

### Mantenimiento

1. **Verificar servicios corriendo:**
   ```bash
   sudo systemctl status relatic-frontend.service
   sudo systemctl status membresia-relatic.service
   ```

2. **Verificar puertos:**
   ```bash
   sudo ss -tlnp | grep -E ":5173|:9000"
   ```

3. **Probar configuración:**
   ```bash
   sudo nginx -t
   ```

4. **Recargar nginx (sin downtime):**
   ```bash
   sudo systemctl reload nginx
   ```

### Optimizaciones Futuras

1. **Rate Limiting:** Agregar rate limiting para prevenir abusos
2. **Caching:** Configurar caching para assets estáticos
3. **Compresión:** Habilitar gzip para todos los tipos de archivo
4. **Security Headers:** Agregar más headers de seguridad (como en helpdesk)

---

## 📊 Mapa de Servicios

```
Internet
   ↓
Cloudflare (SSL/TLS)
   ↓
Nginx (Reverse Proxy)
   ├── dev.relatic.org → localhost:5173 (relatic-frontend)
   ├── miembros.relatic.org → localhost:9000 (membresia-relatic)
   ├── helpdesk.etsrv.site → localhost:3001 (frontend) + localhost:8001 (API)
   └── apps.etsrv.site → localhost:5001
```

---

## 🚨 Troubleshooting

### Si dev.relatic.org no funciona:

1. Verificar que relatic-frontend esté corriendo:
   ```bash
   sudo systemctl status relatic-frontend.service
   ```

2. Verificar puerto 5173:
   ```bash
   sudo ss -tlnp | grep :5173
   ```

3. Ver logs de nginx:
   ```bash
   sudo tail -f /var/log/nginx/dev.relatic.org.error.log
   ```

### Si miembros.relatic.org no funciona:

1. Verificar que membresia-relatic esté corriendo:
   ```bash
   sudo systemctl status membresia-relatic.service
   ```

2. Verificar puerto 9000:
   ```bash
   sudo ss -tlnp | grep :9000
   ```

3. Ver logs de nginx:
   ```bash
   sudo tail -f /var/log/nginx/miembros.relatic.org.error.log
   ```

---

**Última actualización:** $(date)

