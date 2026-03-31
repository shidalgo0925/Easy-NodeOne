#!/bin/bash
# Script para configurar el cron job de verificación automática de pagos Yappy

echo "🔧 Configurando cron job para verificación automática de pagos Yappy..."

# Verificar si crontab está disponible
if ! command -v crontab &> /dev/null; then
    echo "❌ crontab no está disponible en este sistema"
    echo ""
    echo "📋 Alternativas:"
    echo "1. Instalar cron: sudo apt-get install cron (Debian/Ubuntu)"
    echo "2. Usar systemd timer (si está disponible)"
    echo "3. Configurar manualmente el cron job"
    echo ""
    echo "📝 Para configurar manualmente, ejecuta:"
    echo "   crontab -e"
    echo ""
    echo "   Y agrega esta línea:"
    echo "   */5 * * * * /home/relaticpanama2025/projects/membresia-relatic/venv/bin/python3 /home/relaticpanama2025/projects/membresia-relatic/backend/verify_yappy_payments_cron.py >> /home/relaticpanama2025/projects/membresia-relatic/logs/yappy_verification.log 2>&1"
    exit 1
fi

# Crear directorio de logs si no existe
mkdir -p /home/relaticpanama2025/projects/membresia-relatic/logs

# Verificar si el cron job ya existe
if crontab -l 2>/dev/null | grep -q "verify_yappy_payments_cron.py"; then
    echo "⚠️ El cron job ya está configurado"
    crontab -l | grep "verify_yappy_payments_cron.py"
    echo ""
    read -p "¿Deseas reemplazarlo? (s/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Ss]$ ]]; then
        echo "✅ Operación cancelada"
        exit 0
    fi
fi

# Obtener crontab actual
(crontab -l 2>/dev/null; echo "") | grep -v "verify_yappy_payments_cron.py" > /tmp/crontab_backup.txt

# Agregar nuevo cron job
echo "# Verificación automática de pagos Yappy cada 5 minutos" >> /tmp/crontab_backup.txt
echo "*/5 * * * * /home/relaticpanama2025/projects/membresia-relatic/venv/bin/python3 /home/relaticpanama2025/projects/membresia-relatic/backend/verify_yappy_payments_cron.py >> /home/relaticpanama2025/projects/membresia-relatic/logs/yappy_verification.log 2>&1" >> /tmp/crontab_backup.txt

# Instalar nuevo crontab
crontab /tmp/crontab_backup.txt

if [ $? -eq 0 ]; then
    echo "✅ Cron job configurado exitosamente"
    echo ""
    echo "📋 Cron job configurado:"
    crontab -l | grep "verify_yappy_payments_cron.py"
    echo ""
    echo "📝 El script se ejecutará cada 5 minutos"
    echo "📁 Los logs se guardarán en: /home/relaticpanama2025/projects/membresia-relatic/logs/yappy_verification.log"
    echo ""
    echo "🔍 Para verificar que está funcionando:"
    echo "   tail -f /home/relaticpanama2025/projects/membresia-relatic/logs/yappy_verification.log"
else
    echo "❌ Error al configurar el cron job"
    exit 1
fi

# Limpiar archivo temporal
rm -f /tmp/crontab_backup.txt
