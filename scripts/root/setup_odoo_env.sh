#!/bin/bash
# Script para configurar variables de entorno de Odoo en el servicio systemd

SERVICE_FILE="/etc/systemd/system/nodeone.service"
BACKUP_FILE="/etc/systemd/system/nodeone.service.backup.$(date +%Y%m%d_%H%M%S)"

echo "🔧 Configurando integración con Odoo en Easy NodeOne"
echo ""

# Verificar que el archivo existe
if [ ! -f "$SERVICE_FILE" ]; then
    echo "❌ Archivo de servicio no encontrado: $SERVICE_FILE"
    exit 1
fi

# Hacer backup
sudo cp "$SERVICE_FILE" "$BACKUP_FILE"
echo "✅ Backup creado: $BACKUP_FILE"
echo ""

# Valores por defecto - EDITAR ESTOS VALORES
ODOO_ENABLED="true"
ODOO_API_URL="https://odoo.example.com/api/v1/sale"
ODOO_API_KEY="CAMBIAR_CON_API_KEY_REAL"
ODOO_HMAC_SECRET="CAMBIAR_CON_HMAC_SECRET_REAL"
ODOO_ENVIRONMENT="prod"

echo "📋 Configuración a aplicar:"
echo "   ODOO_INTEGRATION_ENABLED=$ODOO_ENABLED"
echo "   ODOO_API_URL=$ODOO_API_URL"
echo "   ODOO_API_KEY=$ODOO_API_KEY"
echo "   ODOO_HMAC_SECRET=$ODOO_HMAC_SECRET"
echo "   ODOO_ENVIRONMENT=$ODOO_ENVIRONMENT"
echo ""

# Crear archivo temporal con las nuevas variables
TMP_FILE=$(mktemp)

# Leer el archivo actual y procesar
while IFS= read -r line; do
    echo "$line" >> "$TMP_FILE"
    
    # Si encontramos [Service], agregar las variables después
    if [[ "$line" == "[Service]" ]]; then
        # Verificar si ya existen variables ODOO
        if ! grep -q "ODOO_INTEGRATION_ENABLED" "$SERVICE_FILE"; then
            echo "" >> "$TMP_FILE"
            echo "# Variables de entorno para integración con Odoo" >> "$TMP_FILE"
            echo "Environment=\"ODOO_INTEGRATION_ENABLED=$ODOO_ENABLED\"" >> "$TMP_FILE"
            echo "Environment=\"ODOO_API_URL=$ODOO_API_URL\"" >> "$TMP_FILE"
            echo "Environment=\"ODOO_API_KEY=$ODOO_API_KEY\"" >> "$TMP_FILE"
            echo "Environment=\"ODOO_HMAC_SECRET=$ODOO_HMAC_SECRET\"" >> "$TMP_FILE"
            echo "Environment=\"ODOO_ENVIRONMENT=$ODOO_ENVIRONMENT\"" >> "$TMP_FILE"
        fi
    fi
done < "$SERVICE_FILE"

# Si ya existían variables ODOO, actualizarlas
if grep -q "ODOO_INTEGRATION_ENABLED" "$SERVICE_FILE"; then
    echo "⚠️  Variables ODOO ya existen. Actualizando..."
    # Remover líneas existentes y agregar nuevas
    grep -v "ODOO_" "$SERVICE_FILE" > "$TMP_FILE"
    
    # Agregar las nuevas variables después de [Service]
    python3 << EOF
with open("$TMP_FILE", "r") as f:
    content = f.read()

odoo_vars = """# Variables de entorno para integración con Odoo
Environment="ODOO_INTEGRATION_ENABLED=$ODOO_ENABLED"
Environment="ODOO_API_URL=$ODOO_API_URL"
Environment="ODOO_API_KEY=$ODOO_API_KEY"
Environment="ODOO_HMAC_SECRET=$ODOO_HMAC_SECRET"
Environment="ODOO_ENVIRONMENT=$ODOO_ENVIRONMENT"
"""

# Insertar después de [Service]
if "[Service]" in content:
    idx = content.find("[Service]")
    next_line = content.find("\\n", idx) + 1
    content = content[:next_line] + odoo_vars + "\\n" + content[next_line:]
    
    with open("$TMP_FILE", "w") as f:
        f.write(content)
EOF
fi

# Copiar el archivo temporal al servicio
sudo cp "$TMP_FILE" "$SERVICE_FILE"
rm "$TMP_FILE"

echo "✅ Variables configuradas en el servicio"
echo ""
echo "🔄 Recargando systemd..."
sudo systemctl daemon-reload

echo ""
echo "✅ Configuración completada"
echo ""
echo "⚠️  IMPORTANTE:"
echo "   1. Edita este script (líneas 18-22) y cambia ODOO_API_KEY y ODOO_HMAC_SECRET"
echo "   2. O edita directamente: sudo nano $SERVICE_FILE"
echo "   3. Reinicia el servicio: sudo systemctl restart nodeone.service"
echo ""
echo "📝 Para verificar la configuración:"
echo "   sudo systemctl show nodeone.service | grep ODOO"
echo ""
