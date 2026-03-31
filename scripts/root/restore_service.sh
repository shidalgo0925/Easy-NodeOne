#!/bin/bash
# Restaurar servicio de membresía y recargar nginx

echo "Iniciando servicio membresia-relatic..."
sudo systemctl start membresia-relatic.service

echo "Verificando estado del servicio..."
sudo systemctl status membresia-relatic.service --no-pager -l

echo "Verificando configuración de nginx..."
sudo nginx -t

if [ $? -eq 0 ]; then
    echo "Recargando nginx..."
    sudo systemctl reload nginx
    echo "✅ Servicio restaurado y nginx recargado"
else
    echo "❌ Error en la configuración de nginx"
    exit 1
fi

