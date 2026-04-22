#!/bin/bash
#
# Script para configurar el cron job de verificación automática de pagos
# Ejecutar este script en el servidor con acceso a crontab
#

echo "=========================================="
echo "Configuración de Cron Job para Verificación de Pagos"
echo "=========================================="
echo ""

# Verificar que crontab esté disponible
if ! command -v crontab &> /dev/null; then
    echo "❌ Error: crontab no está disponible en este sistema"
    echo "   Por favor, ejecuta este script en el servidor con acceso a crontab"
    exit 1
fi

# Directorios
PROJECT_DIR="/var/www/nodeone"
BACKEND_DIR="$PROJECT_DIR/backend"
VENV_PYTHON="$PROJECT_DIR/venv/bin/python3"
LOG_FILE="$PROJECT_DIR/logs/payments_verification.log"

# Verificar que el directorio existe
if [ ! -d "$BACKEND_DIR" ]; then
    echo "❌ Error: Directorio no encontrado: $BACKEND_DIR"
    exit 1
fi

# Verificar que el script existe
if [ ! -f "$BACKEND_DIR/verify_all_payments_cron.py" ]; then
    echo "❌ Error: Script no encontrado: $BACKEND_DIR/verify_all_payments_cron.py"
    exit 1
fi

# Crear directorio de logs si no existe
mkdir -p "$PROJECT_DIR/logs"

# Crear archivo temporal con el cron job
CRON_ENTRY="*/10 * * * * cd $BACKEND_DIR && $VENV_PYTHON verify_all_payments_cron.py >> $LOG_FILE 2>&1"

echo "📋 Entrada del cron job:"
echo "$CRON_ENTRY"
echo ""

# Verificar si ya existe un cron job similar
EXISTING_CRON=$(crontab -l 2>/dev/null | grep "verify_all_payments_cron.py" || echo "")

if [ -n "$EXISTING_CRON" ]; then
    echo "⚠️  Ya existe un cron job para verificación de pagos:"
    echo "$EXISTING_CRON"
    echo ""
    read -p "¿Deseas reemplazarlo? (s/n): " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Ss]$ ]]; then
        echo "❌ Operación cancelada"
        exit 0
    fi
    # Eliminar entrada existente
    crontab -l 2>/dev/null | grep -v "verify_all_payments_cron.py" | crontab -
fi

# Agregar el nuevo cron job
(crontab -l 2>/dev/null; echo "$CRON_ENTRY") | crontab -

echo "✅ Cron job configurado exitosamente"
echo ""
echo "📊 Verificación:"
crontab -l | grep "verify_all_payments_cron.py"
echo ""
echo "📝 El cron job se ejecutará cada 10 minutos"
echo "📄 Los logs se guardarán en: $LOG_FILE"
echo ""
echo "Para ver los logs en tiempo real:"
echo "  tail -f $LOG_FILE"
echo ""
echo "Para verificar que el cron está funcionando:"
echo "  cd $BACKEND_DIR && $VENV_PYTHON verify_all_payments_cron.py"
echo ""
