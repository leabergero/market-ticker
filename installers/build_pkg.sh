#!/bin/bash
# Genera el instalador .pkg de macOS (product archive plano) desde Linux.
# Instala "Market Ticker.app" en /Applications con icono en Launchpad; el
# venv/config/BD van a ~/Library/Application Support/Market Ticker y se
# crean en el primer arranque (PyInstaller no cross-compila).
#
# Un .pkg plano es un xar con Distribution + <id>.pkg/{Payload,Bom,PackageInfo}:
#  - Payload: cpio odc gzip con la raíz a instalar
#  - Bom: lo genera mkbom (bomutils, https://github.com/hogliux/bomutils)
#  - xar: no hay paquete para Linux moderno → installers/lib/mkxar.py
# Exportar MKBOM si mkbom no está en el PATH.
set -e

IDENT="com.bergero.marketticker"
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# La versión vive en frontend/main.py (APP_VERSION): única fuente de verdad
VERSION="$(sed -n 's/^APP_VERSION = "\([^"]*\)".*/\1/p' "$PROJECT_DIR/frontend/main.py")"
STAGE="$PROJECT_DIR/release/pkg-build"
OUT="$PROJECT_DIR/release/market-ticker-${VERSION}.pkg"
MKBOM="${MKBOM:-mkbom}"

rm -rf "$STAGE"
ROOT="$STAGE/root"
APP="$ROOT/Applications/Market Ticker.app"
RES="$APP/Contents/Resources"
mkdir -p "$APP/Contents/MacOS" "$RES"

# ---- bundle de la app ----
cp "$PROJECT_DIR/installers/macos/MarketTicker.sh" "$APP/Contents/MacOS/MarketTicker"
chmod 755 "$APP/Contents/MacOS/MarketTicker"

cat > "$APP/Contents/Info.plist" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleName</key><string>Market Ticker</string>
  <key>CFBundleDisplayName</key><string>Market Ticker</string>
  <key>CFBundleIdentifier</key><string>$IDENT</string>
  <key>CFBundleVersion</key><string>$VERSION</string>
  <key>CFBundleShortVersionString</key><string>$VERSION</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>CFBundleExecutable</key><string>MarketTicker</string>
  <key>CFBundleIconFile</key><string>icon.icns</string>
  <key>NSHighResolutionCapable</key><true/>
  <key>LSMinimumSystemVersion</key><string>11.0</string>
  <!-- banner sin icono en el Dock ni en Cmd-Tab (app "agente") -->
  <key>LSUIElement</key><true/>
</dict>
</plist>
EOF

mkdir -p "$RES/backend" "$RES/config" "$RES/assets"
cp "$PROJECT_DIR"/backend/{app.py,db.py,scraper.py} "$RES/backend/"
cp "$PROJECT_DIR/frontend/main.py" "$RES/main.py"
cp "$PROJECT_DIR/config/config.json" "$RES/config/"
cp "$PROJECT_DIR/assets/ticker.png" "$RES/assets/"
cp "$PROJECT_DIR/assets/icon.icns" "$RES/icon.icns"
cp "$PROJECT_DIR/release/requirements.txt" "$RES/requirements.txt"
cp "$PROJECT_DIR/installers/macos/uninstall.sh" "$RES/uninstall.sh"
cp "$PROJECT_DIR/installers/macos/INSTRUCCIONES.txt" "$RES/INSTRUCCIONES.txt"
chmod 755 "$RES/uninstall.sh"

# run.sh junto a main.py: lo usa el registro de inicio automático de la app
cat > "$RES/run.sh" << 'EOF'
#!/bin/bash
exec "$(cd "$(dirname "$0")/../MacOS" && pwd)/MarketTicker"
EOF
chmod 755 "$RES/run.sh"

# ---- componentes del pkg plano ----
PKGDIR="$STAGE/flat/market-ticker.pkg"
mkdir -p "$PKGDIR"

(cd "$ROOT" && find . | cpio -o --format odc --owner 0:0 2>/dev/null | gzip -9) > "$PKGDIR/Payload"
"$MKBOM" -u 0 -g 0 "$ROOT" "$PKGDIR/Bom"

# postinstall: primer arranque automático al terminar la instalación. El
# instalador corre como root → abrir la app como el usuario logueado; el
# primer arranque de la app crea el venv (MarketTicker.sh), así que acá no
# se duplica esa lógica. Nunca abortar la instalación por esto (exit 0).
SCRIPTS="$STAGE/scripts"
mkdir -p "$SCRIPTS"
cat > "$SCRIPTS/postinstall" << 'EOF'
#!/bin/bash
APP="/Applications/Market Ticker.app"
CUSER="$(stat -f%Su /dev/console 2>/dev/null)"
if [ -n "$CUSER" ] && [ "$CUSER" != "root" ]; then
    CUID="$(id -u "$CUSER" 2>/dev/null)"
    launchctl asuser "$CUID" sudo -u "$CUSER" -H open "$APP" >/dev/null 2>&1 \
        || sudo -u "$CUSER" -H open "$APP" >/dev/null 2>&1 || true
fi
exit 0
EOF
chmod 755 "$SCRIPTS/postinstall"
(cd "$SCRIPTS" && find . | cpio -o --format odc --owner 0:0 2>/dev/null | gzip -9) > "$PKGDIR/Scripts"

NFILES=$(find "$ROOT" | wc -l)
KBYTES=$(du -sk "$ROOT" | cut -f1)

cat > "$PKGDIR/PackageInfo" << EOF
<?xml version="1.0" encoding="utf-8"?>
<pkg-info format-version="2" identifier="$IDENT" version="$VERSION" install-location="/" auth="root">
  <payload installKBytes="$KBYTES" numberOfFiles="$NFILES"/>
  <scripts>
    <postinstall file="./postinstall"/>
  </scripts>
  <bundle-version>
    <bundle CFBundleShortVersionString="$VERSION" CFBundleVersion="$VERSION" id="$IDENT" path="./Applications/Market Ticker.app"/>
  </bundle-version>
</pkg-info>
EOF

cat > "$STAGE/flat/Distribution" << EOF
<?xml version="1.0" encoding="utf-8"?>
<installer-gui-script minSpecVersion="1">
  <title>Market Ticker</title>
  <options customize="never" require-scripts="false" rootVolumeOnly="true"/>
  <domains enable_localSystem="true"/>
  <choices-outline>
    <line choice="default">
      <line choice="$IDENT"/>
    </line>
  </choices-outline>
  <choice id="default"/>
  <choice id="$IDENT" visible="false">
    <pkg-ref id="$IDENT"/>
  </choice>
  <pkg-ref id="$IDENT" version="$VERSION" onConclusion="none">#market-ticker.pkg</pkg-ref>
  <pkg-ref id="$IDENT">
    <payload installKBytes="$KBYTES" numberOfFiles="$NFILES"/>
  </pkg-ref>
</installer-gui-script>
EOF

# ---- empaquetar en xar ----
python3 "$PROJECT_DIR/installers/lib/mkxar.py" "$STAGE/flat" "$OUT"
rm -rf "$STAGE"
echo
echo "✅ PKG generado: $OUT"
