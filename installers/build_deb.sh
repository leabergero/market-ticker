#!/bin/bash
# Genera el paquete .deb de Market Ticker para Ubuntu/Debian.
# La app se instala en /opt/market-ticker; el postinst crea el venv con
# las dependencias pip (requiere internet al instalar). Datos y config
# van al home de cada usuario (TICKER_DATA_DIR / ~/.config/market-ticker).
set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# La versión vive en frontend/main.py (APP_VERSION): única fuente de verdad
VERSION="$(sed -n 's/^APP_VERSION = "\([^"]*\)".*/\1/p' "$PROJECT_DIR/frontend/main.py")"
PKG="$PROJECT_DIR/release/deb-build"
OUT="$PROJECT_DIR/release/market-ticker_${VERSION}_all.deb"

rm -rf "$PKG"
mkdir -p "$PKG/DEBIAN" \
         "$PKG/opt/market-ticker" \
         "$PKG/usr/bin" \
         "$PKG/usr/share/applications" \
         "$PKG/usr/share/icons/hicolor/256x256/apps"

# ---- archivos de la app ----
cp -r "$PROJECT_DIR/backend" "$PKG/opt/market-ticker/backend"
rm -rf "$PKG/opt/market-ticker/backend/data" "$PKG/opt/market-ticker/backend/__pycache__" \
       "$PKG/opt/market-ticker/backend/ticker.log"
cp "$PROJECT_DIR/frontend/main.py" "$PKG/opt/market-ticker/main.py"
cp -r "$PROJECT_DIR/assets" "$PKG/opt/market-ticker/assets"
cp "$PROJECT_DIR/release/requirements.txt" "$PKG/opt/market-ticker/requirements.txt"

# run.sh junto a main.py: lo usa el registro de inicio automático de la app
cat > "$PKG/opt/market-ticker/run.sh" << 'EOF'
#!/bin/bash
exec /usr/bin/market-ticker
EOF
chmod 755 "$PKG/opt/market-ticker/run.sh"

# ---- lanzador ----
cat > "$PKG/usr/bin/market-ticker" << 'EOF'
#!/bin/bash
# Lanzador de Market Ticker: backend + banner con datos por-usuario
APP=/opt/market-ticker
export TICKER_DATA_DIR="$HOME/.local/share/market-ticker"
CFG="$HOME/.config/market-ticker"
mkdir -p "$TICKER_DATA_DIR" "$CFG/config"
cd "$CFG"
if ! curl -s --max-time 1 http://127.0.0.1:5003/api/health >/dev/null 2>&1; then
    "$APP/venv/bin/python" "$APP/backend/app.py" >>"$TICKER_DATA_DIR/ticker.log" 2>&1 &
    sleep 2
fi
exec "$APP/venv/bin/python" "$APP/main.py"
EOF
chmod 755 "$PKG/usr/bin/market-ticker"

# ---- entrada de menú + ícono ----
cat > "$PKG/usr/share/applications/market-ticker.desktop" << 'EOF'
[Desktop Entry]
Type=Application
Name=Market Ticker
Comment=Banner de cotizaciones en tiempo real
Comment[en]=Real-time stock ticker banner
Exec=market-ticker
Icon=market-ticker
Terminal=false
Categories=Office;Finance;
Keywords=bolsa;acciones;ticker;stocks;finance;
EOF
cp "$PROJECT_DIR/assets/ticker.png" "$PKG/usr/share/icons/hicolor/256x256/apps/market-ticker.png"

# ---- metadatos DEBIAN ----
cat > "$PKG/DEBIAN/control" << EOF
Package: market-ticker
Version: $VERSION
Section: misc
Priority: optional
Architecture: all
Depends: python3 (>= 3.10), python3-venv, python3-pip, libxcb-cursor0, x11-utils, curl
Maintainer: Leandro R. Bergero <estudiocontablebergero@gmail.com>
Homepage: https://github.com/leabergero/market-ticker
Description: Banner de cotizaciones en tiempo real
 Cinta de bolsa fina y siempre visible con 19 mercados mundiales,
 noticias de las ultimas 72 horas habiles, filtros por mercado y
 precio, 3 idiomas (ES/EN/DE) e inicio automatico opcional.
EOF

cat > "$PKG/DEBIAN/postinst" << 'EOF'
#!/bin/bash
# Crea el venv con las dependencias pip (requiere internet)
set -e
echo "Market Ticker: instalando dependencias Python (puede tardar un minuto)..."
python3 -m venv /opt/market-ticker/venv
/opt/market-ticker/venv/bin/pip install --quiet --upgrade pip
/opt/market-ticker/venv/bin/pip install --quiet -r /opt/market-ticker/requirements.txt
echo "Market Ticker instalado. Buscalo en el menú de aplicaciones."
EOF
chmod 755 "$PKG/DEBIAN/postinst"

cat > "$PKG/DEBIAN/prerm" << 'EOF'
#!/bin/bash
# Cierra la app y elimina el venv generado por postinst
fuser -k 5003/tcp 2>/dev/null || true
rm -rf /opt/market-ticker/venv
exit 0
EOF
chmod 755 "$PKG/DEBIAN/prerm"

# ---- construir ----
dpkg-deb --build --root-owner-group "$PKG" "$OUT"
rm -rf "$PKG"
echo
echo "✅ Paquete generado: $OUT"
dpkg-deb --info "$OUT" | head -15
