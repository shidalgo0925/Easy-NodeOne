#!/bin/bash
# Script rápido para actualizar credenciales de Odoo

SERVICE_FILE="/etc/systemd/system/membresia-relatic.service"

echo "🔐 Actualizar credenciales de Odoo"
echo ""

if [ -z "$1" ] || [ -z "$2" ]; then
    echo "Uso: $0 <API_KEY> <HMAC_SECRET>"
    echo ""
    echo "Ejemplo:"
    echo "  $0 'RELATIC_API_KEY_2026' 'my_secret_key_for_hmac'"
    exit 1
fi

API_KEY="$1"
HMAC_SECRET="$2"

echo "📝 Actualizando credenciales..."
echo "   API Key: ${API_KEY:0:20}..."
echo "   HMAC Secret: ${HMAC_SECRET:0:20}..."
echo ""

# Actualizar el archivo del servicio
sudo python3 << EOF
import re

service_file = "$SERVICE_FILE"

with open(service_file, 'r') as f:
    content = f.read()

# Actualizar API_KEY
content = re.sub(
    r'Environment="ODOO_API_KEY=.*"',
    f'Environment="ODOO_API_KEY=$API_KEY"',
    content
)

# Actualizar HMAC_SECRET
content = re.sub(
    r'Environment="ODOO_HMAC_SECRET=.*"',
    f'Environment="ODOO_HMAC_SECRET=$HMAC_SECRET"',
    content
)

with open(service_file, 'w') as f:
    f.write(content)

print("✅ Credenciales actualizadas")
EOF

echo ""
echo "🔄 Recargando systemd..."
sudo systemctl daemon-reload

echo ""
echo "⚠️  Reiniciar el servicio para aplicar cambios:"
echo "   sudo systemctl restart membresia-relatic.service"
echo ""
echo "🧪 Probar conexión:"
echo "   python3 test_odoo_connection.py"
echo ""
