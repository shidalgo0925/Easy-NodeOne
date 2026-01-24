#!/bin/bash
# Script para configurar systemd timer para verificación automática de pagos Yappy

echo "🔧 Configurando systemd timer para verificación automática de pagos Yappy..."

# Verificar si estamos como root o tenemos permisos sudo
if [ "$EUID" -ne 0 ]; then 
    echo "⚠️ Este script requiere permisos de administrador"
    echo "   Ejecuta con: sudo ./setup_yappy_systemd.sh"
    exit 1
fi

# Crear directorio de logs si no existe
mkdir -p /home/relaticpanama2025/projects/membresia-relatic/logs
chown relaticpanama2025:relaticpanama2025 /home/relaticpanama2025/projects/membresia-relatic/logs

# Copiar archivos de servicio y timer
SCRIPT_DIR="/home/relaticpanama2025/projects/membresia-relatic/backend"
SYSTEMD_DIR="/etc/systemd/system"

cp "$SCRIPT_DIR/yappy-verification.service" "$SYSTEMD_DIR/"
cp "$SCRIPT_DIR/yappy-verification.timer" "$SYSTEMD_DIR/"

# Recargar systemd
systemctl daemon-reload

# Habilitar y iniciar el timer
systemctl enable yappy-verification.timer
systemctl start yappy-verification.timer

if [ $? -eq 0 ]; then
    echo "✅ Systemd timer configurado exitosamente"
    echo ""
    echo "📋 Estado del timer:"
    systemctl status yappy-verification.timer --no-pager -l
    echo ""
    echo "🔍 Comandos útiles:"
    echo "   Ver estado: sudo systemctl status yappy-verification.timer"
    echo "   Ver logs: tail -f /home/relaticpanama2025/projects/membresia-relatic/logs/yappy_verification.log"
    echo "   Ejecutar manualmente: sudo systemctl start yappy-verification.service"
    echo "   Detener: sudo systemctl stop yappy-verification.timer"
    echo "   Deshabilitar: sudo systemctl disable yappy-verification.timer"
else
    echo "❌ Error al configurar el timer"
    exit 1
fi
