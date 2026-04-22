#!/bin/bash

echo "=========================================="
echo "DIAGNÓSTICO DEL SISTEMA DE MEMBRESÍA"
echo "=========================================="
echo ""

echo "1. Verificando servicio nodeone..."
sudo systemctl status nodeone.service --no-pager -l | head -20
echo ""

echo "2. Verificando si el puerto 9000 está en uso..."
sudo ss -tlnp | grep :9000 || echo "❌ Puerto 9000 NO está en uso"
echo ""

echo "3. Verificando procesos Python relacionados..."
ps aux | grep -E "python.*app.py|membresia" | grep -v grep || echo "❌ No hay procesos Python corriendo"
echo ""

echo "4. Verificando logs del servicio (últimas 20 líneas)..."
sudo journalctl -u nodeone.service -n 20 --no-pager
echo ""

echo "5. Verificando configuración de nginx..."
sudo nginx -t
echo ""

echo "6. Verificando si nginx está corriendo..."
sudo systemctl status nginx --no-pager | head -10
echo ""

echo "7. Verificando configuración de dev.app.example.com..."
grep -A 2 "proxy_pass" /etc/nginx/sites-enabled/01-dev.app.example.com | head -5
echo ""

echo "8. Verificando archivo app.py..."
if [ -f "/var/www/nodeone/backend/app.py" ]; then
    echo "✅ app.py existe"
    echo "Últimas líneas del archivo:"
    tail -5 /var/www/nodeone/backend/app.py
else
    echo "❌ app.py NO existe"
fi
echo ""

echo "9. Verificando entorno virtual..."
if [ -d "/var/www/nodeone/venv" ]; then
    echo "✅ venv existe"
    if [ -f "/var/www/nodeone/venv/bin/python3" ]; then
        echo "✅ Python en venv existe"
    else
        echo "❌ Python en venv NO existe"
    fi
else
    echo "❌ venv NO existe"
fi
echo ""

echo "10. Intentando iniciar el servicio..."
sudo systemctl start nodeone.service
sleep 2
sudo systemctl status nodeone.service --no-pager -l | head -15
echo ""

echo "=========================================="
echo "FIN DEL DIAGNÓSTICO"
echo "=========================================="

