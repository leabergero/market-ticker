#!/bin/bash
# Lanzador de Market Ticker.app (CFBundleExecutable).
# La app vive en /Applications (solo lectura): el venv, la config, la BD y
# los logs van a ~/Library/Application Support/Market Ticker. En el primer
# arranque crea el venv con las dependencias pip (necesita internet).
RES="$(cd "$(dirname "$0")/../Resources" && pwd)"
SUP="$HOME/Library/Application Support/Market Ticker"
VENV="$SUP/venv"
mkdir -p "$SUP/config"
export TICKER_DATA_DIR="$SUP"
[ -f "$SUP/config/config.json" ] || cp "$RES/config/config.json" "$SUP/config/" 2>/dev/null

# Python 3.10+: PATH primero, luego rutas típicas de Homebrew/python.org
PY=""
for c in python3.13 python3.12 python3.11 python3.10 python3 \
         /opt/homebrew/bin/python3 /usr/local/bin/python3; do
    p="$(command -v "$c" 2>/dev/null)" || continue
    if "$p" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' 2>/dev/null; then
        PY="$p"
        break
    fi
done
if [ -z "$PY" ]; then
    osascript -e 'display alert "Market Ticker" message "Se necesita Python 3.10 o superior. Se abrirá la página de descarga; instalalo y volvé a abrir Market Ticker." as critical' >/dev/null 2>&1
    open "https://www.python.org/downloads/macos/"
    exit 1
fi

# Qt tiene mínimo de macOS por versión (6.7→11, 6.8→12, 6.9→13): pinear
# PyQt6 según el SO o el último wheel exige un macOS más nuevo y la app
# muere con "Qt requires macOS N or later" (visto en Monterey con 6.9).
OSMAJ="$(sw_vers -productVersion 2>/dev/null | cut -d. -f1)"
QT_PIN=()
case "$OSMAJ" in
    11) QT_PIN=("PyQt6>=6.7,<6.8" "PyQt6-Qt6>=6.7,<6.8");;
    12) QT_PIN=("PyQt6>=6.7,<6.9" "PyQt6-Qt6>=6.8,<6.9");;
esac
if [ -n "$OSMAJ" ] && [ "$OSMAJ" -lt 11 ] 2>/dev/null; then
    osascript -e 'display alert "Market Ticker" message "Se necesita macOS 11 (Big Sur) o superior." as critical' >/dev/null 2>&1
    exit 1
fi

if [ ! -x "$VENV/bin/python" ]; then
    osascript -e 'display notification "Instalando dependencias (solo la primera vez, puede tardar unos minutos)…" with title "Market Ticker"' >/dev/null 2>&1
    if ! { "$PY" -m venv "$VENV" \
           && "$VENV/bin/pip" install --quiet --upgrade pip \
           && "$VENV/bin/pip" install --quiet -r "$RES/requirements.txt" "${QT_PIN[@]}"; } >>"$SUP/ticker.log" 2>&1; then
        rm -rf "$VENV"
        osascript -e 'display alert "Market Ticker" message "Falló la instalación de dependencias. Revisá tu conexión a internet y volvé a abrir la app." as critical' >/dev/null 2>&1
        exit 1
    fi
fi

cd "$SUP"
if ! curl -s --max-time 1 http://127.0.0.1:5003/api/health >/dev/null 2>&1; then
    "$VENV/bin/python" "$RES/backend/app.py" >>"$SUP/ticker.log" 2>&1 &
    sleep 2
fi
exec "$VENV/bin/python" "$RES/main.py"
