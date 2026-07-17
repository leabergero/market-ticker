#!/bin/bash
# Compilador e instalador para macOS

set -e

echo "🍎 Building Ticker Widget for macOS..."

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD_DIR="$PROJECT_DIR/dist"
BACKEND_DIR="$PROJECT_DIR/backend"
FRONTEND_DIR="$PROJECT_DIR/frontend"
APP_DIR="$BUILD_DIR/Market Ticker.app"

rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"

# Backend
echo "📦 Packaging backend..."
cp -r "$BACKEND_DIR" "$BUILD_DIR/backend"
cp -r "$PROJECT_DIR/config" "$BUILD_DIR/config"

# Frontend
echo "🎨 Packaging frontend..."
python3 -m venv "$BUILD_DIR/venv"
source "$BUILD_DIR/venv/bin/activate"
pip install --upgrade pip
pip install -r "$FRONTEND_DIR/requirements.txt"
pip install -r "$BACKEND_DIR/requirements.txt"
pip install pyinstaller

# Copiar main.py
cp "$FRONTEND_DIR/main.py" "$BUILD_DIR/main.py"

# Crear ejecutable con PyInstaller
echo "⚙️  Building executable..."
pyinstaller --onefile --windowed \
  --name "Market Ticker" \
  --add-data "$BUILD_DIR/backend:backend" \
  --add-data "$BUILD_DIR/config:config" \
  "$BUILD_DIR/main.py"

# Script de inicio para macOS
cat > "$BUILD_DIR/run.sh" << 'EOF'
#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/venv/bin/activate"
cd "$SCRIPT_DIR/backend"
python app.py &
BACKEND_PID=$!
cd "$SCRIPT_DIR"
sleep 2

# Lanzar app
if [ -d "dist/Market Ticker.app" ]; then
  open "dist/Market Ticker.app"
else
  python main.py
fi

# Cleanup
trap "kill $BACKEND_PID" EXIT
EOF

chmod +x "$BUILD_DIR/run.sh"

# Info.plist para integración con Dock/Menu
mkdir -p "$APP_DIR/Contents"
cat > "$APP_DIR/Contents/Info.plist" << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleName</key>
  <string>Market Ticker</string>
  <key>CFBundleIdentifier</key>
  <string>com.ticker.widget</string>
  <key>CFBundleVersion</key>
  <string>1.0</string>
  <key>LSUIElement</key>
  <true/>
</dict>
</plist>
EOF

echo "✅ Build complete!"
echo "📂 Output: $BUILD_DIR"
echo "🚀 To run: $BUILD_DIR/run.sh"
