#!/bin/bash
# Ejecutar en el servidor Ubuntu por SSH para aumentar límite de inotify.
# Uso: bash fix-inotify.sh   (o chmod +x y ./fix-inotify.sh)

echo "Límite actual: $(cat /proc/sys/fs/inotify/max_user_watches 2>/dev/null || echo 'N/A')"

echo "fs.inotify.max_user_watches=524288" | sudo tee /etc/sysctl.d/99-inotify.conf
echo "fs.inotify.max_user_instances=512"   | sudo tee -a /etc/sysctl.d/99-inotify.conf
sudo sysctl --system

echo "Límite nuevo:  $(cat /proc/sys/fs/inotify/max_user_watches)"
echo "Debe mostrar 524288."
