# CLAUDE.md — Market Ticker

Banner de cotizaciones tipo cinta de bolsa. **Autor:** Leandro R. Bergero · MSc Finance & Banking (BSM-UPF) · github.com/leabergero · linkedin.com/in/leandro-raul-bergero (el "Acerca de" con estos datos es obligatorio en toda la suite de proyectos).

## Qué es (diseño aprobado 2026-07-17)

- **NO es una ventana con lista**: es un banner de 32 px, sin marco, ancho completo, con la cinta desplazándose (TapeWidget con paintEvent propio + hit-testing por cotización para el click → noticias).
- Fila: LED estado · cinta · ⚙ config · ✕ cerrar. Todo lo demás vive en el click derecho y en ⚙.
- Estética HUD oscura (#0a0e14, monoespaciada chica, verde #00d97e / rojo #ff5c5c).

## Arquitectura

- `backend/` Flask :5003 + APScheduler (scrape cada 15 min + inicial al arrancar + rotación BD 23:59). SQLite en ruta ABSOLUTA junto a db.py (nunca relativa: generaba BDs duplicadas). `get_tickers` devuelve última cotización por símbolo (GROUP BY + MAX(timestamp)); `market` acepta lista por comas.
- `frontend/main.py` PyQt6, todo en un archivo: i18n (dict I18N es/en/de + tr() + market_label con país traducido), TICKER_LABELS para tickers numéricos (patrón JP_LABELS/HK_LABELS de market-neuronal-map), reserva de espacio por SO, autostart por SO.
- `release/` empaquetador → zips windows/macos con install.bat/install.sh (venv; PyInstaller NO cross-compila).

## Gotchas duros (no re-aprender)

- **Reiniciar backend: `fuser -k 5003/tcp`** — pkill -f con "app.py"/"main.py" se auto-mata (el patrón matchea el propio shell). Para el frontend: patrón `"main[.]py"` en comando aislado sin otras menciones, o kill por PID.
- **Wayland**: forzar `QT_QPA_PLATFORM=xcb` (requiere `libxcb-cursor0`). Sin `Qt.Tool` (oculta la ventana al perder foco). `move()` y always-on-top no funcionan en Wayland nativo.
- **Reserva de espacio (strut)**: Qt bajo XWayland reporta availableGeometry SIN la barra de GNOME → leer márgenes reales con `xprop -root _NET_WORKAREA` + `xwininfo -root`, cachearlos SOLO con la reserva propia inactiva, y posicionar siempre desde geometría completa + márgenes cacheados. El strut es absoluto desde el borde (barra GNOME 32 + banner 32 = reservar 64). Tipo de ventana `_NET_WM_WINDOW_TYPE_DOCK` + remap (hide/show) para que Mutter lo relea.
- **yfinance**: nunca pinear versiones viejas (0.2.32 murió cuando Yahoo cambió la API; síntoma "Expecting value: line 1"). `.news` moderno anida en `content` (pubDate ISO, clickThroughUrl, provider.displayName) — fetch_news soporta ambos formatos. El % de cambio necesita `period="5d"` (con 1d compara la vela contra sí misma → 0%).
- **PyQt6**: `>=6.7` (pinear 6.6.1 mezclaba Qt6 6.11 incompatible). `setWindowIcon(None)` crashea.
- Noticias: corte de **72 horas hábiles** (`news_cutoff` descuenta solo lun-vie).
- macOS: NO existe API pública para reservar espacio — documentado al usuario, no intentarlo.

## Verificación mínima

```bash
python -m py_compile frontend/main.py backend/*.py
curl -s http://127.0.0.1:5003/api/health   # last_scrape.ok = LED
# strut visible: xprop -id $(xwininfo -root -children | grep -i "market ticker" | awk '{print $1}') _NET_WM_STRUT_PARTIAL
```

## Estado 2026-07-17

Funcionando en Linux con 91 tickers en vivo. Zips enviados a testers (Daniel/Windows, contacto/macOS) — AppBar de Windows aún sin prueba real. Pendientes: GitHub Actions para binarios nativos, filtro de precio consciente de moneda (MERVAL en ARS vs rangos en €), pulsar noticias en la cinta.
