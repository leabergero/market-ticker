#!/bin/bash
# Desinstalador de Market Ticker para Linux
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP_DIR="$PROJECT_DIR/dist"

echo
echo "  Esto eliminará la instalación de Market Ticker:"
echo "    - cierra la app si está corriendo"
echo "    - quita el inicio automático"
echo "    - borra $APP_DIR (incluidos datos y backups)"
echo "    (el código fuente del proyecto NO se toca)"
echo
read -r -p "  Escribí SI y presioná Enter para continuar (otra cosa cancela): " CONFIRM
if [ "$CONFIRM" != "SI" ]; then
    echo "  Cancelado."
    exit 0
fi

echo "Cerrando Market Ticker..."
fuser -k 5003/tcp 2>/dev/null || true
pkill -f "$APP_DIR" 2>/dev/null || true
sleep 1

echo "Quitando inicio automático..."
rm -f "$HOME/.config/autostart/market-ticker.desktop"

echo "Eliminando archivos..."
rm -rf "$APP_DIR"

echo
echo "  [OK] Market Ticker fue desinstalado."
