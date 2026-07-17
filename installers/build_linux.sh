#!/bin/bash
# Compilador e instalador para Linux

set -e

echo "🐧 Building Ticker Widget for Linux..."

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD_DIR="$PROJECT_DIR/dist"
BACKEND_DIR="$PROJECT_DIR/backend"
FRONTEND_DIR="$PROJECT_DIR/frontend"

rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"

# Backend
echo "📦 Packaging backend..."
cp -r "$BACKEND_DIR" "$BUILD_DIR/backend"
cp -r "$PROJECT_DIR/config" "$BUILD_DIR/config"

# Frontend
echo "🎨 Packaging frontend..."
mkdir -p "$BUILD_DIR/venv"
python3 -m venv "$BUILD_DIR/venv"
source "$BUILD_DIR/venv/bin/activate"
pip install --upgrade pip
pip install -r "$FRONTEND_DIR/requirements.txt"
pip install -r "$BACKEND_DIR/requirements.txt"
cp "$FRONTEND_DIR/main.py" "$BUILD_DIR/main.py"

# Script de inicio
cat > "$BUILD_DIR/run.sh" << 'EOF'
#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/venv/bin/activate"
cd "$SCRIPT_DIR/backend"
python app.py &
cd "$SCRIPT_DIR"
sleep 2
python main.py
EOF

chmod +x "$BUILD_DIR/run.sh"

# Crear .desktop para Linux
cat > "$BUILD_DIR/ticker-widget.desktop" << 'EOF'
[Desktop Entry]
Version=1.0
Type=Application
Name=Market Ticker
Comment=Real-time market ticker widget
Exec=/path/to/ticker-widget/run.sh
Terminal=false
Categories=Finance;
Icon=ticker
EOF

echo "✅ Build complete!"
echo "📂 Output: $BUILD_DIR"
echo "🚀 To run: $BUILD_DIR/run.sh"
