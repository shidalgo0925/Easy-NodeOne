#!/bin/bash
#
# Script para configurar cron job de notificaciones automáticas
# Ejecuta notification_scheduler.py diariamente
#

set -e

# Colores para output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Directorios
PROJECT_DIR="/var/www/nodeone"
BACKEND_DIR="$PROJECT_DIR/backend"
VENV_PYTHON="$PROJECT_DIR/venv/bin/python"
SCHEDULER_SCRIPT="$BACKEND_DIR/notification_scheduler.py"
LOG_DIR="$PROJECT_DIR/logs"
LOG_FILE="$LOG_DIR/notifications.log"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Configuración de Cron Job para Notificaciones${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Verificar que el script existe
if [ ! -f "$SCHEDULER_SCRIPT" ]; then
    echo -e "${RED}❌ Error: No se encuentra $SCHEDULER_SCRIPT${NC}"
    exit 1
fi

# Verificar que el venv existe
if [ ! -f "$VENV_PYTHON" ]; then
    echo -e "${RED}❌ Error: No se encuentra el entorno virtual en $PROJECT_DIR/venv${NC}"
    exit 1
fi

# Crear directorio de logs si no existe
if [ ! -d "$LOG_DIR" ]; then
    echo -e "${YELLOW}📁 Creando directorio de logs: $LOG_DIR${NC}"
    mkdir -p "$LOG_DIR"
    chmod 755 "$LOG_DIR"
fi

# Hacer el script ejecutable
chmod +x "$SCHEDULER_SCRIPT"

# Obtener crontab actual
CRON_TEMP=$(mktemp)
crontab -l 2>/dev/null > "$CRON_TEMP" || true

# Verificar si ya existe el cron job
if grep -q "notification_scheduler.py" "$CRON_TEMP"; then
    echo -e "${YELLOW}⚠️  Ya existe un cron job para notification_scheduler.py${NC}"
    echo ""
    echo "Cron job actual:"
    grep "notification_scheduler.py" "$CRON_TEMP"
    echo ""
    read -p "¿Deseas reemplazarlo? (s/n): " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Ss]$ ]]; then
        echo -e "${YELLOW}Operación cancelada${NC}"
        rm "$CRON_TEMP"
        exit 0
    fi
    # Eliminar línea existente
    sed -i '/notification_scheduler.py/d' "$CRON_TEMP"
fi

# Agregar nuevo cron job
# Ejecutar diariamente a las 9:00 AM
CRON_LINE="0 9 * * * cd $PROJECT_DIR && source venv/bin/activate && $VENV_PYTHON $SCHEDULER_SCRIPT >> $LOG_FILE 2>&1"

echo "$CRON_LINE" >> "$CRON_TEMP"

# Instalar nuevo crontab
/usr/bin/crontab "$CRON_TEMP"
rm "$CRON_TEMP"

echo -e "${GREEN}✅ Cron job configurado exitosamente${NC}"
echo ""
echo "Configuración:"
echo "  - Frecuencia: Diariamente a las 9:00 AM"
echo "  - Script: $SCHEDULER_SCRIPT"
echo "  - Logs: $LOG_FILE"
echo ""
echo "Para verificar:"
echo "  crontab -l | grep notification"
echo ""
echo "Para ver logs en tiempo real:"
echo "  tail -f $LOG_FILE"
echo ""
echo "Para ejecutar manualmente:"
echo "  cd $PROJECT_DIR && source venv/bin/activate && python $SCHEDULER_SCRIPT"
echo ""

# Opcional: Preguntar si quiere ejecutar ahora
read -p "¿Deseas ejecutar el scheduler ahora para probar? (s/n): " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Ss]$ ]]; then
    echo -e "${YELLOW}Ejecutando scheduler...${NC}"
    cd "$PROJECT_DIR"
    source venv/bin/activate
    python "$SCHEDULER_SCRIPT"
    echo -e "${GREEN}✅ Ejecución completada${NC}"
fi

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Configuración Completada${NC}"
echo -e "${GREEN}========================================${NC}"
