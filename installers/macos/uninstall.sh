#!/bin/bash
# Desinstalador de Market Ticker para macOS.
# Uso: bash "/Applications/Market Ticker.app/Contents/Resources/uninstall.sh"
echo "Desinstalando Market Ticker..."
pkill -f "Market Ticker.app/Contents/Resources/main.py" 2>/dev/null
pkill -f "Market Ticker.app/Contents/Resources/backend/app.py" 2>/dev/null
launchctl unload "$HOME/Library/LaunchAgents/com.bergero.marketticker.plist" 2>/dev/null
rm -f "$HOME/Library/LaunchAgents/com.bergero.marketticker.plist"
rm -rf "$HOME/Library/Application Support/Market Ticker"
sudo rm -rf "/Applications/Market Ticker.app"
sudo pkgutil --forget com.bergero.marketticker 2>/dev/null
echo "Listo. Market Ticker fue eliminado."
