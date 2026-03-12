#!/bin/bash
# Script para configurar la integración con Odoo

echo "🔧 Configurando integración con Odoo..."

# Verificar si el servicio existe
if [ ! -f /etc/systemd/system/nodeone.service ]; then
    echo "❌ Servicio nodeone.service no encontrado"
    exit 1
fi

# Solicitar configuración
echo ""
echo "📝 Por favor, proporciona la siguiente información:"
echo ""

read -p "¿Habilitar integración con Odoo? (true/false) [false]: " ENABLED
ENABLED=${ENABLED:-false}

if [ "$ENABLED" = "true" ]; then
    read -p "URL del API de Odoo [https://odoo.relatic.org/api/relatic/v1/sale]: " API_URL
    API_URL=${API_URL:-https://odoo.relatic.org/api/relatic/v1/sale}
    
    read -p "API Key de Odoo: " API_KEY
    if [ -z "$API_KEY" ]; then
        echo "❌ API Key es requerida"
        exit 1
    fi
    
    read -p "HMAC Secret de Odoo: " HMAC_SECRET
    if [ -z "$HMAC_SECRET" ]; then
        echo "❌ HMAC Secret es requerido"
        exit 1
    fi
    
    read -p "Ambiente (prod/dev/test) [prod]: " ENVIRONMENT
    ENVIRONMENT=${ENVIRONMENT:-prod}
    
    # Crear archivo temporal con el servicio actualizado
    TMP_FILE=$(mktemp)
    
    # Leer el servicio actual y agregar las variables de entorno
    cat /etc/systemd/system/nodeone.service | \
        sed '/\[Service\]/a Environment="ODOO_INTEGRATION_ENABLED='"$ENABLED"'"' | \
        sed '/ODOO_INTEGRATION_ENABLED/a Environment="ODOO_API_URL='"$API_URL"'"' | \
        sed '/ODOO_API_URL/a Environment="ODOO_API_KEY='"$API_KEY"'"' | \
        sed '/ODOO_API_KEY/a Environment="ODOO_HMAC_SECRET='"$HMAC_SECRET"'"' | \
        sed '/ODOO_HMAC_SECRET/a Environment="ODOO_ENVIRONMENT='"$ENVIRONMENT"'"' > "$TMP_FILE"
    
    # Verificar si ya existen las variables (para actualizar en lugar de duplicar)
    if grep -q "ODOO_INTEGRATION_ENABLED" /etc/systemd/system/nodeone.service; then
        echo "⚠️  Las variables de Odoo ya existen. Actualizando..."
        # Crear versión actualizada sin duplicados
        python3 << EOF
import re

with open('/etc/systemd/system/nodeone.service', 'r') as f:
    content = f.read()

# Remover líneas existentes de Odoo
content = re.sub(r'Environment="ODOO_.*"\n', '', content)

# Agregar nuevas variables después de [Service]
content = re.sub(
    r'(\[Service\])',
    r'\1\nEnvironment="ODOO_INTEGRATION_ENABLED='"$ENABLED"'"\nEnvironment="ODOO_API_URL='"$API_URL"'"\nEnvironment="ODOO_API_KEY='"$API_KEY"'"\nEnvironment="ODOO_HMAC_SECRET='"$HMAC_SECRET"'"\nEnvironment="ODOO_ENVIRONMENT='"$ENVIRONMENT"'"',
    content
)

with open('/etc/systemd/system/nodeone.service', 'w') as f:
    f.write(content)
EOF
    else
        # Agregar variables nuevas
        sudo cp "$TMP_FILE" /etc/systemd/system/nodeone.service
    fi
    
    rm "$TMP_FILE"
    
    echo ""
    echo "✅ Variables de entorno agregadas al servicio"
    echo ""
    echo "📋 Configuración:"
    echo "   ODOO_INTEGRATION_ENABLED=$ENABLED"
    echo "   ODOO_API_URL=$API_URL"
    echo "   ODOO_API_KEY=${API_KEY:0:10}..."
    echo "   ODOO_HMAC_SECRET=${HMAC_SECRET:0:10}..."
    echo "   ODOO_ENVIRONMENT=$ENVIRONMENT"
    echo ""
    echo "🔄 Recargando systemd..."
    sudo systemctl daemon-reload
    
    echo ""
    echo "✅ Configuración completada"
    echo ""
    echo "⚠️  IMPORTANTE: Reinicia el servicio para aplicar los cambios:"
    echo "   sudo systemctl restart nodeone.service"
    echo ""
else
    echo "ℹ️  Integración con Odoo deshabilitada"
fi
