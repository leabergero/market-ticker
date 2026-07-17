import sys
import re
import json
import subprocess
import webbrowser
import requests
from pathlib import Path
from PyQt6.QtWidgets import (
    QApplication, QWidget, QHBoxLayout, QVBoxLayout, QGridLayout, QLabel,
    QPushButton, QDialog, QListWidget, QListWidgetItem, QMessageBox, QMenu,
    QCheckBox, QComboBox
)
from datetime import datetime, timedelta
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QColor, QPainter, QAction, QFontMetrics

BACKEND_URL = "http://127.0.0.1:5003"

# Paleta HUD oscura
BG = QColor("#0a0e14")
FG = QColor("#c9d1d9")
GREEN = QColor("#00d97e")
RED = QColor("#ff5c5c")
DIM = QColor("#4a5568")

# Autoría mostrada en el diálogo "Acerca de"
AUTHOR = {
    "name": "Leandro R. Bergero",
    "title": "MSc Finance & Banking (BSM-UPF)",
    "github": "https://github.com/leabergero",
    "linkedin": "https://www.linkedin.com/in/leandro-raul-bergero/",
}

# Mercados disponibles y sus etiquetas para la interfaz
MARKETS = ["STOXX", "DAX", "CAC40", "IBEX35", "FTSE100", "FTSEMIB", "SMI",
           "NYSE", "NASDAQ", "SP500", "TSX", "NIKKEI", "HANGSENG", "SSE",
           "KOSPI", "SENSEX", "ASX", "BOVESPA", "MERVAL"]
# (nombre visible, código de país) — el país se traduce según el idioma activo
MARKET_INFO = {
    "STOXX": ("STOXX 50", "eu"), "DAX": ("DAX", "de"), "CAC40": ("CAC 40", "fr"),
    "IBEX35": ("IBEX 35", "es"), "FTSE100": ("FTSE 100", "uk"),
    "FTSEMIB": ("FTSE MIB", "it"), "SMI": ("SMI", "ch"), "NYSE": ("NYSE", "us"),
    "NASDAQ": ("NASDAQ", "us"), "SP500": ("S&P 500", "us"), "TSX": ("TSX", "ca"),
    "NIKKEI": ("Nikkei 225", "jp"), "HANGSENG": ("Hang Seng", "hk"),
    "SSE": ("SSE", "cn"), "KOSPI": ("KOSPI", "kr"), "SENSEX": ("Sensex", "in"),
    "ASX": ("ASX 200", "au"), "BOVESPA": ("Bovespa", "br"), "MERVAL": ("MERVAL", "ar"),
}

_COUNTRY = {
    "eu": {"es": "Europa", "en": "Europe", "de": "Europa"},
    "de": {"es": "Alemania", "en": "Germany", "de": "Deutschland"},
    "fr": {"es": "Francia", "en": "France", "de": "Frankreich"},
    "es": {"es": "España", "en": "Spain", "de": "Spanien"},
    "uk": {"es": "Reino Unido", "en": "United Kingdom", "de": "Vereinigtes Königreich"},
    "it": {"es": "Italia", "en": "Italy", "de": "Italien"},
    "ch": {"es": "Suiza", "en": "Switzerland", "de": "Schweiz"},
    "us": {"es": "EE.UU.", "en": "USA", "de": "USA"},
    "ca": {"es": "Canadá", "en": "Canada", "de": "Kanada"},
    "jp": {"es": "Japón", "en": "Japan", "de": "Japan"},
    "hk": {"es": "Hong Kong", "en": "Hong Kong", "de": "Hongkong"},
    "cn": {"es": "Shanghái", "en": "Shanghai", "de": "Schanghai"},
    "kr": {"es": "Corea del Sur", "en": "South Korea", "de": "Südkorea"},
    "in": {"es": "India", "en": "India", "de": "Indien"},
    "au": {"es": "Australia", "en": "Australia", "de": "Australien"},
    "br": {"es": "Brasil", "en": "Brazil", "de": "Brasilien"},
    "ar": {"es": "Argentina", "en": "Argentina", "de": "Argentinien"},
}

# Interfaz en tres idiomas; el activo vive en config["lang"]
LANGS = [("es", "🇪🇸 Español"), ("en", "🇬🇧 English"), ("de", "🇩🇪 Deutsch")]
_lang = "es"

I18N = {
    "es": {
        "waiting": "esperando datos…",
        "data_status": "Estado de datos",
        "live": "Datos en vivo",
        "not_live": "Sin datos en vivo (backend caído o mercado sin respuesta)",
        "gear_tip": "Configuración",
        "close": "Cerrar",
        "news_title": "Noticias",
        "news_click": "Click en una noticia para abrirla en el navegador:",
        "news_none": "Sin noticias de las últimas 72 h hábiles para {s}.",
        "position": "Posición", "top": "Arriba", "bottom": "Abajo",
        "always_visible": "Siempre visible (reservar espacio)",
        "markets": "Mercados", "all": "Todos",
        "price_range": "Rango de precio", "all_prices": "Todos los precios",
        "refresh": "Actualizar ahora",
        "backups": "Backups", "del_old": "Borrar antiguos (> 7 días)",
        "del_all": "Borrar todos…",
        "about": "Acerca de…", "about_title": "Acerca de", "quit": "Salir",
        "settings": "Configuración",
        "markets_label": "Mercados a mostrar (ninguno marcado = todos):",
        "pos_label": "Posición del banner:",
        "reserve_label": "Siempre visible: las ventanas maximizadas\nse acomodan sin tapar el banner",
        "language": "Idioma:", "save": "Guardar", "cancel": "Cancelar",
        "deleted_old": "Se borraron {n} backups antiguos.",
        "deleted_all": "Se borraron {n} backups.",
        "confirm_del": "¿Borrar TODOS los backups? No se puede deshacer.",
        "error": "Error",
        "autostart": "Iniciar automáticamente con el sistema",
    },
    "en": {
        "waiting": "waiting for data…",
        "data_status": "Data status",
        "live": "Live data",
        "not_live": "No live data (backend down or market not responding)",
        "gear_tip": "Settings",
        "close": "Close",
        "news_title": "News",
        "news_click": "Click a headline to open it in your browser:",
        "news_none": "No news from the last 72 business hours for {s}.",
        "position": "Position", "top": "Top", "bottom": "Bottom",
        "always_visible": "Always visible (reserve space)",
        "markets": "Markets", "all": "All",
        "price_range": "Price range", "all_prices": "All prices",
        "refresh": "Refresh now",
        "backups": "Backups", "del_old": "Delete old (> 7 days)",
        "del_all": "Delete all…",
        "about": "About…", "about_title": "About", "quit": "Quit",
        "settings": "Settings",
        "markets_label": "Markets to show (none checked = all):",
        "pos_label": "Banner position:",
        "reserve_label": "Always visible: maximized windows\narrange without covering the banner",
        "language": "Language:", "save": "Save", "cancel": "Cancel",
        "deleted_old": "{n} old backups deleted.",
        "deleted_all": "{n} backups deleted.",
        "confirm_del": "Delete ALL backups? This cannot be undone.",
        "error": "Error",
        "autostart": "Start automatically at login",
    },
    "de": {
        "waiting": "warte auf Daten…",
        "data_status": "Datenstatus",
        "live": "Live-Daten",
        "not_live": "Keine Live-Daten (Backend aus oder Markt antwortet nicht)",
        "gear_tip": "Einstellungen",
        "close": "Schließen",
        "news_title": "Nachrichten",
        "news_click": "Klicken Sie auf eine Nachricht, um sie im Browser zu öffnen:",
        "news_none": "Keine Nachrichten der letzten 72 Handelsstunden für {s}.",
        "position": "Position", "top": "Oben", "bottom": "Unten",
        "always_visible": "Immer sichtbar (Platz reservieren)",
        "markets": "Märkte", "all": "Alle",
        "price_range": "Preisbereich", "all_prices": "Alle Preise",
        "refresh": "Jetzt aktualisieren",
        "backups": "Backups", "del_old": "Alte löschen (> 7 Tage)",
        "del_all": "Alle löschen…",
        "about": "Über…", "about_title": "Über", "quit": "Beenden",
        "settings": "Einstellungen",
        "markets_label": "Anzuzeigende Märkte (keine Auswahl = alle):",
        "pos_label": "Position des Banners:",
        "reserve_label": "Immer sichtbar: maximierte Fenster\nverdecken das Banner nicht",
        "language": "Sprache:", "save": "Speichern", "cancel": "Abbrechen",
        "deleted_old": "{n} alte Backups gelöscht.",
        "deleted_all": "{n} Backups gelöscht.",
        "confirm_del": "ALLE Backups löschen? Das kann nicht rückgängig gemacht werden.",
        "error": "Fehler",
        "autostart": "Automatisch beim Anmelden starten",
    },
}


def tr(key, **kw):
    """Traduce una clave al idioma activo (cae a español si falta)."""
    s = I18N.get(_lang, I18N["es"]).get(key) or I18N["es"].get(key, key)
    return s.format(**kw) if kw else s


def market_label(m):
    """Etiqueta de mercado con el país en el idioma activo."""
    name, country = MARKET_INFO.get(m, (m, None))
    return f"{name} ({_COUNTRY[country][_lang]})" if country else name

# Tickers numéricos (Tokio/HK/Shanghái/Corea) e índices → etiqueta legible.
# Patrón heredado de market-neuronal-map (JP_LABELS/HK_LABELS).
TICKER_LABELS = {
    "7203.T": "TOYOTA", "6758.T": "SONY", "9984.T": "SOFTBANK", "8306.T": "MUFG",
    "0700.HK": "TENCENT", "9988.HK": "ALIBABA", "0005.HK": "HSBC", "1299.HK": "AIA",
    "000001.SS": "SSE COMP", "600519.SS": "MOUTAI", "601398.SS": "ICBC",
    "601857.SS": "PETROCHINA", "005930.KS": "SAMSUNG", "000660.KS": "SK HYNIX",
    "005380.KS": "HYUNDAI",
    "^STOXX50E": "STOXX50", "^GDAXI": "DAX", "^FCHI": "CAC40", "^IBEX": "IBEX35",
    "^FTSE": "FTSE100", "FTSEMIB.MI": "FTSE MIB", "^SSMI": "SMI", "^NYA": "NYSE",
    "^IXIC": "NASDAQ", "^GSPC": "S&P500", "^GSPTSE": "TSX", "^N225": "NIKKEI",
    "^HSI": "HANGSENG", "^KS11": "KOSPI", "^BSESN": "SENSEX", "^AXJO": "ASX200",
    "^BVSP": "BOVESPA", "^MERV": "MERVAL",
}


def display_label(symbol):
    """Etiqueta legible para la cinta: mapea códigos numéricos/índices y
    quita sufijo de bolsa y clase de acción (VALE3.SA → VALE)."""
    if symbol in TICKER_LABELS:
        return TICKER_LABELS[symbol]
    base = symbol.split(".")[0]
    return re.sub(r"\d+$", "", base) or base


# Rangos de precio predefinidos (etiqueta, min, max)
PRICE_RANGES = [
    ("Todos los precios", None, None),
    ("0 – 10 €", 0, 10),
    ("10 – 20 €", 10, 20),
    ("21 – 50 €", 21, 50),
    ("51 – 100 €", 51, 100),
    ("100 – 500 €", 100, 500),
    ("+500 €", 500, 100000),
]


class TapeWidget(QWidget):
    """Cinta desplazable que dibuja las cotizaciones y detecta clicks."""

    SPEED_PX = 1          # píxeles por tick de animación
    TICK_MS = 30          # intervalo de animación
    GAP = 48              # separación entre cotizaciones

    def __init__(self, parent=None):
        super().__init__(parent)
        self.tickers = []          # datos actuales
        self.offset = 0.0          # desplazamiento horizontal
        self._hit_zones = []       # [(x_ini, x_fin, symbol)] para clicks
        self._tape_width = 1       # ancho total de una pasada de la cinta
        self.font_mono = QFont("DejaVu Sans Mono", 10)
        self.setMouseTracking(True)

        self.anim = QTimer(self)
        self.anim.timeout.connect(self._advance)
        self.anim.start(self.TICK_MS)

    def set_tickers(self, tickers):
        """Actualiza los datos que muestra la cinta."""
        self.tickers = tickers
        self.update()

    def _advance(self):
        """Avanza la cinta un paso y repinta."""
        self.offset += self.SPEED_PX
        if self._tape_width > 0:
            self.offset %= self._tape_width
        self.update()

    def _segments(self):
        """Genera los segmentos de texto de una pasada completa de la cinta."""
        segs = []
        for t in self.tickers:
            up = (t.get("change") or 0) >= 0
            arrow = "▲" if up else "▼"
            label = display_label(t["symbol"])
            text = f"{label}  {t['price']:,.2f} {arrow}{abs(t.get('change_percent') or 0):.2f}%"
            segs.append((text, GREEN if up else RED, t["symbol"]))
        return segs

    def paintEvent(self, event):
        """Dibuja la cinta con desplazamiento continuo."""
        p = QPainter(self)
        p.fillRect(self.rect(), BG)
        p.setFont(self.font_mono)
        fm = QFontMetrics(self.font_mono)
        y = int(self.height() / 2 + fm.ascent() / 2 - 2)

        segs = self._segments()
        if not segs:
            p.setPen(DIM)
            p.drawText(10, y, tr("waiting"))
            return

        widths = [fm.horizontalAdvance(s[0]) + self.GAP for s in segs]
        self._tape_width = max(sum(widths), 1)
        self._hit_zones = []

        # Dibuja dos pasadas para que el bucle sea continuo
        x = -self.offset
        while x < self.width():
            for (text, color, symbol), w in zip(segs, widths):
                if x + w > 0 and x < self.width():
                    p.setPen(color)
                    p.drawText(int(x), y, text)
                    self._hit_zones.append((x, x + w - self.GAP, symbol))
                x += w
        p.end()

    def mouseReleaseEvent(self, event):
        """Click sobre una cotización abre sus noticias."""
        x = event.position().x()
        for x0, x1, symbol in self._hit_zones:
            if x0 <= x <= x1:
                self.window().show_news(symbol)
                return


class TickerBanner(QWidget):
    """Banner de cotizaciones: fino, sin marco, ancho completo de pantalla."""

    HEIGHT = 32

    def __init__(self):
        super().__init__()
        self.config_path = Path("./config/config.json")
        self.config = self._load_config()
        self.live = False  # estado del último fetch (LED)

        self.setWindowTitle("Market Ticker")
        # Nota: sin Qt.Tool — ese flag oculta la ventana cuando la app
        # pierde el foco, y un banner debe quedar siempre visible.
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self._init_ui()
        self._place()
        # Si el área de trabajo cambia (el sistema informa sus barras tarde,
        # o aplica nuestra reserva), reposicionarse automáticamente.
        QApplication.primaryScreen().availableGeometryChanged.connect(
            lambda _: self._place())

        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.fetch_tickers)
        self.refresh_timer.start(60 * 1000)  # consulta al backend cada 1 min
        self.fetch_tickers()

    # ---------- configuración ----------

    def _load_config(self):
        """Carga config.json normalizando valores de versiones anteriores."""
        default = {"position": "top", "markets": [], "price_range": 0,
                   "reserve_space": True, "lang": "es", "autostart": False}
        try:
            with open(self.config_path) as f:
                cfg = {**default, **json.load(f)}
        except (OSError, json.JSONDecodeError):
            return default

        # Migra el campo legado "market" (string único) a "markets" (lista)
        legacy = cfg.pop("market", None)
        if legacy in MARKETS and not cfg["markets"]:
            cfg["markets"] = [legacy]

        # Normaliza valores legados o corruptos
        if not isinstance(cfg.get("markets"), list):
            cfg["markets"] = []
        cfg["markets"] = [m for m in cfg["markets"] if m in MARKETS]
        if cfg.get("position") not in ("top", "bottom"):
            cfg["position"] = "top"
        if not isinstance(cfg.get("price_range"), int) or not (0 <= cfg["price_range"] < len(PRICE_RANGES)):
            cfg["price_range"] = 0
        cfg["reserve_space"] = bool(cfg.get("reserve_space", True))
        if cfg.get("lang") not in I18N:
            cfg["lang"] = "es"
        cfg["autostart"] = bool(cfg.get("autostart", False))
        global _lang
        _lang = cfg["lang"]
        return {k: cfg[k] for k in default}

    def _save_config(self):
        """Persiste la configuración actual."""
        self.config_path.parent.mkdir(exist_ok=True)
        with open(self.config_path, "w") as f:
            json.dump(self.config, f, indent=2)

    # ---------- interfaz ----------

    def _init_ui(self):
        """Construye la fila: LED | cinta | cerrar."""
        self.setStyleSheet(f"background-color: {BG.name()};")
        row = QHBoxLayout(self)
        row.setContentsMargins(8, 0, 4, 0)
        row.setSpacing(6)

        self.led = QLabel("●")
        self.led.setStyleSheet(f"color: {RED.name()}; font-size: 10px;")
        self.led.setToolTip(f"{tr('data_status')}: {tr('not_live')}")
        row.addWidget(self.led)

        self.tape = TapeWidget(self)
        row.addWidget(self.tape, stretch=1)

        self.gear_btn = QPushButton("⚙")
        self.gear_btn.setFixedSize(18, 18)
        self.gear_btn.setToolTip(tr("gear_tip"))
        self.gear_btn.setStyleSheet(
            "QPushButton {color:#4a5568; background:transparent; border:none; font-size:12px;}"
            "QPushButton:hover {color:#c9d1d9;}"
        )
        self.gear_btn.clicked.connect(self._show_settings)
        row.addWidget(self.gear_btn)

        self.close_btn = QPushButton("✕")
        self.close_btn.setFixedSize(18, 18)
        self.close_btn.setToolTip(tr("close"))
        self.close_btn.setStyleSheet(
            "QPushButton {color:#4a5568; background:transparent; border:none; font-size:11px;}"
            "QPushButton:hover {color:#ff5c5c;}"
        )
        self.close_btn.clicked.connect(self.close)
        row.addWidget(self.close_btn)

    def _read_margins_x11(self):
        """Lee los márgenes reales del sistema desde _NET_WORKAREA del root
        (xprop). Qt bajo XWayland reporta el área disponible sin descontar
        la barra del sistema — el servidor X sí la informa bien."""
        try:
            wa = subprocess.run(["xprop", "-root", "_NET_WORKAREA"],
                                capture_output=True, text=True).stdout
            nums = [int(n) for n in re.findall(r"\d+", wa)]
            _, y, _, h = nums[:4]
            root = subprocess.run(["xwininfo", "-root"],
                                  capture_output=True, text=True).stdout
            rheight = int(re.search(r"Height:\s*(\d+)", root).group(1))
            return (y, max(rheight - y - h, 0))
        except Exception:
            return (0, 0)

    def _base_margins(self):
        """Márgenes reservados por OTROS paneles (barra del sistema, dock…).

        En Linux se leen del servidor X y se cachean mientras nuestra propia
        reserva está inactiva (leerlos con ella puesta los contaminaría).
        En Windows/macOS Qt sí es confiable y se descuenta la reserva propia."""
        if sys.platform.startswith("linux"):
            if not getattr(self, "_strut_active", False):
                self._margins_cache = self._read_margins_x11()
            return getattr(self, "_margins_cache", (0, 0))

        screen = QApplication.primaryScreen()
        full = screen.geometry()
        avail = screen.availableGeometry()
        top_m = avail.y() - full.y()
        bottom_m = (full.y() + full.height()) - (avail.y() + avail.height())
        if getattr(self, "_strut_active", False):
            if self.config.get("position") == "bottom":
                bottom_m = max(bottom_m - self.HEIGHT, 0)
            else:
                top_m = max(top_m - self.HEIGHT, 0)
        return top_m, bottom_m

    def _place(self):
        """Posiciona el banner arriba o abajo (geometría completa + márgenes
        base): inmune a que el área disponible incluya nuestra propia reserva."""
        full = QApplication.primaryScreen().geometry()
        top_m, bottom_m = self._base_margins()
        self.setFixedSize(full.width(), self.HEIGHT)
        if self.config.get("position") == "bottom":
            self.move(full.x(), full.y() + full.height() - bottom_m - self.HEIGHT)
        else:
            self.move(full.x(), full.y() + top_m)

    # ---------- reserva de espacio ("siempre visible") ----------

    def _apply_strut(self):
        """Reserva el borde de pantalla para que las ventanas maximizadas
        se acomoden y nunca tapen el banner (como una barra de tareas)."""
        if not self.config.get("reserve_space", True):
            self._remove_strut()
            return
        if sys.platform.startswith("linux"):
            self._strut_linux(remove=False)
        elif sys.platform == "win32":
            self._strut_windows(remove=False)
        # macOS: no existe API pública para reservar espacio de pantalla.
        # El banner queda siempre-encima, pero una ventana maximizada
        # puede extenderse por debajo de él.

    def _remove_strut(self):
        """Libera el espacio reservado (las ventanas vuelven a maximizar completo)."""
        if sys.platform.startswith("linux"):
            self._strut_linux(remove=True)
        elif sys.platform == "win32":
            self._strut_windows(remove=True)

    def _strut_linux(self, remove):
        """Publica _NET_WM_STRUT(_PARTIAL) + tipo DOCK vía xprop (X11/XWayland).

        La reserva se calcula sobre el área base SIN nuestra propia reserva
        previa, para que re-aplicar no acumule espacio.
        """
        wid = str(int(self.winId()))
        if remove:
            for prop in ("_NET_WM_STRUT_PARTIAL", "_NET_WM_STRUT"):
                subprocess.run(["xprop", "-id", wid, "-remove", prop],
                               capture_output=True)
            wtype = "_NET_WM_WINDOW_TYPE_NORMAL"
            self._strut_active = False
        else:
            full = self.screen().geometry()
            top_m, bottom_m = self._base_margins()
            x0, x1 = full.x(), full.x() + full.width() - 1
            if self.config.get("position") == "bottom":
                reserved = bottom_m + self.HEIGHT
                vals = [0, 0, 0, reserved, 0, 0, 0, 0, 0, 0, x0, x1]
            else:
                reserved = top_m + self.HEIGHT
                vals = [0, 0, reserved, 0, 0, 0, 0, 0, x0, x1, 0, 0]
            subprocess.run(["xprop", "-id", wid, "-f", "_NET_WM_STRUT_PARTIAL", "32c",
                            "-set", "_NET_WM_STRUT_PARTIAL", ",".join(map(str, vals))],
                           capture_output=True)
            subprocess.run(["xprop", "-id", wid, "-f", "_NET_WM_STRUT", "32c",
                            "-set", "_NET_WM_STRUT",
                            f"{vals[0]},{vals[1]},{vals[2]},{vals[3]}"],
                           capture_output=True)
            wtype = "_NET_WM_WINDOW_TYPE_DOCK"
            self._strut_active = True
        subprocess.run(["xprop", "-id", wid, "-f", "_NET_WM_WINDOW_TYPE", "32a",
                        "-set", "_NET_WM_WINDOW_TYPE", wtype], capture_output=True)
        # remapear para que el gestor relea tipo y strut, y reubicarse después
        self.hide()
        self.show()
        QTimer.singleShot(200, self._place)

    def _strut_windows(self, remove):
        """Registra/quita el banner como AppBar de Windows (SHAppBarMessage)."""
        import ctypes
        from ctypes import wintypes

        class APPBARDATA(ctypes.Structure):
            _fields_ = [("cbSize", wintypes.DWORD), ("hWnd", wintypes.HWND),
                        ("uCallbackMessage", wintypes.UINT), ("uEdge", wintypes.UINT),
                        ("rc", wintypes.RECT), ("lParam", wintypes.LPARAM)]

        ABM_NEW, ABM_REMOVE, ABM_QUERYPOS, ABM_SETPOS = 0, 1, 2, 3
        ABE_TOP, ABE_BOTTOM = 1, 3
        shell = ctypes.windll.shell32
        abd = APPBARDATA()
        abd.cbSize = ctypes.sizeof(APPBARDATA)
        abd.hWnd = int(self.winId())

        if remove:
            if getattr(self, "_appbar_registered", False):
                shell.SHAppBarMessage(ABM_REMOVE, ctypes.byref(abd))
                self._appbar_registered = False
            self._strut_active = False
            return

        if not getattr(self, "_appbar_registered", False):
            shell.SHAppBarMessage(ABM_NEW, ctypes.byref(abd))
            self._appbar_registered = True
        geo = self.screen().geometry()
        abd.uEdge = ABE_BOTTOM if self.config.get("position") == "bottom" else ABE_TOP
        abd.rc.left, abd.rc.right = geo.x(), geo.x() + geo.width()
        if abd.uEdge == ABE_TOP:
            abd.rc.top = geo.y()
            abd.rc.bottom = geo.y() + self.HEIGHT
        else:
            abd.rc.bottom = geo.y() + geo.height()
            abd.rc.top = abd.rc.bottom - self.HEIGHT
        shell.SHAppBarMessage(ABM_QUERYPOS, ctypes.byref(abd))
        shell.SHAppBarMessage(ABM_SETPOS, ctypes.byref(abd))
        self._strut_active = True
        # ocupar exactamente el rectángulo concedido por el sistema
        self.move(abd.rc.left, abd.rc.top)

    def _set_led(self, live):
        """Actualiza el LED: verde = datos en vivo, rojo = sin conexión."""
        self.live = live
        color = GREEN.name() if live else RED.name()
        tip = tr("live") if live else tr("not_live")
        self.led.setStyleSheet(f"color: {color}; font-size: 10px;")
        self.led.setToolTip(f"{tr('data_status')}: {tip}")

    # ---------- datos ----------

    def fetch_tickers(self):
        """Trae cotizaciones del backend aplicando los filtros activos."""
        try:
            params = {"limit": 100}
            if self.config.get("markets"):
                params["market"] = ",".join(self.config["markets"])
            _, pmin, pmax = PRICE_RANGES[self.config.get("price_range", 0)]
            if pmin is not None:
                params["price_min"] = pmin
                params["price_max"] = pmax
            r = requests.get(f"{BACKEND_URL}/api/tickers", params=params, timeout=5)
            r.raise_for_status()
            self.tape.set_tickers(r.json().get("tickers", []))
            self._set_led(self._data_is_live())
        except requests.RequestException:
            self._set_led(False)

    def _data_is_live(self):
        """True solo si el backend scrapeó datos reales hace menos de 20 min."""
        try:
            r = requests.get(f"{BACKEND_URL}/api/health", timeout=5)
            info = r.json().get("last_scrape", {})
            if info.get("ok") and info.get("time"):
                age = datetime.now() - datetime.fromisoformat(info["time"])
                return age < timedelta(minutes=20)
        except (requests.RequestException, ValueError):
            pass
        return False

    def show_news(self, symbol):
        """Muestra las noticias del símbolo clickeado."""
        try:
            r = requests.get(f"{BACKEND_URL}/api/news", params={"symbol": symbol}, timeout=5)
            news = r.json().get("news", [])
        except requests.RequestException:
            news = []

        dlg = QDialog(self)
        dlg.setWindowTitle(f"{tr('news_title')} — {display_label(symbol)}")
        dlg.resize(560, 360)
        lay = QVBoxLayout(dlg)
        if news:
            lay.addWidget(QLabel(tr("news_click")))
            lst = QListWidget()
            for n in news[:20]:
                item = QListWidgetItem(f"[{n.get('source', '')}] {n.get('title', '')}")
                item.setData(Qt.ItemDataRole.UserRole, n.get("url", ""))
                lst.addItem(item)
            lst.itemClicked.connect(
                lambda it: webbrowser.open(it.data(Qt.ItemDataRole.UserRole))
                if it.data(Qt.ItemDataRole.UserRole) else None)
            lay.addWidget(lst)
        else:
            lay.addWidget(QLabel(tr("news_none", s=display_label(symbol))))
        btn = QPushButton(tr("close"))
        btn.clicked.connect(dlg.close)
        lay.addWidget(btn)
        dlg.exec()

    # ---------- menú contextual ----------

    def contextMenuEvent(self, event):
        """Click derecho: posición, filtros y gestión de backups."""
        menu = QMenu(self)

        pos_menu = menu.addMenu(tr("position"))
        for label, value in [(tr("top"), "top"), (tr("bottom"), "bottom")]:
            act = QAction(label, self, checkable=True)
            act.setChecked(self.config.get("position") == value)
            act.triggered.connect(lambda _, v=value: self._change_position(v))
            pos_menu.addAction(act)

        vis_act = QAction(tr("always_visible"), self, checkable=True)
        vis_act.setChecked(self.config.get("reserve_space", True))
        vis_act.triggered.connect(self._toggle_reserve)
        menu.addAction(vis_act)

        mkt_menu = menu.addMenu(tr("markets"))
        all_act = QAction(tr("all"), self, checkable=True)
        all_act.setChecked(not self.config.get("markets"))
        all_act.triggered.connect(lambda: self._set_markets([]))
        mkt_menu.addAction(all_act)
        mkt_menu.addSeparator()
        for m in MARKETS:
            act = QAction(market_label(m), self, checkable=True)
            act.setChecked(m in self.config.get("markets", []))
            act.triggered.connect(lambda _, v=m: self._toggle_market(v))
            mkt_menu.addAction(act)

        price_menu = menu.addMenu(tr("price_range"))
        for i, (label, _, _) in enumerate(PRICE_RANGES):
            act = QAction(label if i else tr("all_prices"), self, checkable=True)
            act.setChecked(self.config.get("price_range", 0) == i)
            act.triggered.connect(lambda _, v=i: self._change_price_range(v))
            price_menu.addAction(act)

        menu.addSeparator()
        menu.addAction(tr("refresh"), self.fetch_tickers)

        bk_menu = menu.addMenu(tr("backups"))
        bk_menu.addAction(tr("del_old"), self._delete_old_backups)
        bk_menu.addAction(tr("del_all"), self._delete_all_backups)

        menu.addSeparator()
        menu.addAction(tr("about"), self._show_about)
        menu.addAction(tr("quit"), self.close)
        menu.exec(event.globalPos())

    def _change_position(self, value):
        """Cambia el banner de borde de pantalla y reubica la reserva."""
        self.config["position"] = value
        self._save_config()
        self._remove_strut()
        self._place()
        QTimer.singleShot(250, self._apply_strut)

    def _toggle_reserve(self, checked):
        """Activa/desactiva la reserva de espacio en el borde."""
        self.config["reserve_space"] = bool(checked)
        self._save_config()
        self._apply_strut()

    def _set_markets(self, markets):
        """Fija la lista de mercados visibles (vacía = todos)."""
        self.config["markets"] = markets
        self._save_config()
        self.fetch_tickers()

    def _toggle_market(self, market):
        """Agrega o quita un mercado de la selección."""
        current = set(self.config.get("markets", []))
        current.symmetric_difference_update({market})
        self._set_markets(sorted(current))

    def _show_settings(self):
        """Diálogo de configuración: mercados, posición, reserva de espacio,
        idioma e inicio automático."""
        dlg = QDialog(self)
        dlg.setWindowTitle(tr("settings"))
        dlg.setStyleSheet(f"background-color: {BG.name()}; color: {FG.name()};")
        lay = QVBoxLayout(dlg)

        lang_row = QHBoxLayout()
        lang_row.addWidget(QLabel(tr("language")))
        for code, label in LANGS:
            btn = QPushButton(label)
            if code == _lang:
                # idioma activo: destacado en verde, sin acción
                btn.setStyleSheet(
                    f"QPushButton {{border: 1px solid {GREEN.name()};"
                    f" color: {GREEN.name()}; padding: 4px 10px;"
                    f" border-radius: 4px; background: transparent; font-weight: bold;}}")
            else:
                btn.setStyleSheet(
                    "QPushButton {border: 1px solid #4a5568; color: #c9d1d9;"
                    " padding: 4px 10px; border-radius: 4px; background: transparent;}"
                    "QPushButton:hover {border-color: #c9d1d9;}")
                btn.clicked.connect(lambda _, c=code, d=dlg: self._set_lang(c, d))
            lang_row.addWidget(btn)
        lang_row.addStretch()
        lay.addLayout(lang_row)

        lay.addWidget(QLabel(tr("markets_label")))
        grid = QGridLayout()
        boxes = {}
        for i, m in enumerate(MARKETS):
            cb = QCheckBox(market_label(m))
            cb.setChecked(m in self.config.get("markets", []))
            boxes[m] = cb
            grid.addWidget(cb, i // 2, i % 2)
        lay.addLayout(grid)

        pos_row = QHBoxLayout()
        pos_row.addWidget(QLabel(tr("pos_label")))
        pos_combo = QComboBox()
        pos_combo.addItems([tr("top"), tr("bottom")])
        pos_combo.setCurrentIndex(1 if self.config.get("position") == "bottom" else 0)
        pos_row.addWidget(pos_combo)
        pos_row.addStretch()
        lay.addLayout(pos_row)

        reserve_cb = QCheckBox(tr("reserve_label"))
        reserve_cb.setChecked(self.config.get("reserve_space", True))
        lay.addWidget(reserve_cb)

        autostart_cb = QCheckBox(tr("autostart"))
        autostart_cb.setChecked(self._autostart_enabled())
        lay.addWidget(autostart_cb)

        btn_row = QHBoxLayout()
        about_btn = QPushButton(tr("about"))
        about_btn.clicked.connect(self._show_about)
        save_btn = QPushButton(tr("save"))
        cancel_btn = QPushButton(tr("cancel"))
        btn_row.addWidget(about_btn)
        btn_row.addStretch()
        btn_row.addWidget(save_btn)
        btn_row.addWidget(cancel_btn)
        lay.addLayout(btn_row)

        save_btn.clicked.connect(dlg.accept)
        cancel_btn.clicked.connect(dlg.reject)

        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.config["markets"] = [m for m, cb in boxes.items() if cb.isChecked()]
            self.config["position"] = "bottom" if pos_combo.currentIndex() == 1 else "top"
            self.config["reserve_space"] = reserve_cb.isChecked()
            self.config["autostart"] = autostart_cb.isChecked()
            self._set_autostart(autostart_cb.isChecked())
            self._save_config()
            self._remove_strut()
            self._place()
            QTimer.singleShot(250, self._apply_strut)
            self.fetch_tickers()

    def _set_lang(self, code, dlg=None):
        """Cambia el idioma de la interfaz y refresca los textos persistentes."""
        global _lang
        _lang = code
        self.config["lang"] = code
        self._save_config()
        self.gear_btn.setToolTip(tr("gear_tip"))
        self.close_btn.setToolTip(tr("close"))
        self._set_led(self.live)
        if dlg is not None:
            dlg.reject()
            QTimer.singleShot(0, self._show_settings)

    def _show_about(self):
        """Diálogo 'Acerca de' con autoría y enlaces de contacto."""
        dlg = QDialog(self)
        dlg.setWindowTitle(tr("about_title"))
        dlg.setStyleSheet(f"background-color: {BG.name()}; color: {FG.name()};")
        lay = QVBoxLayout(dlg)
        lay.setSpacing(8)

        info = QLabel(
            f"<b>Market Ticker</b><br>"
            f"<br>{AUTHOR['name']}<br>"
            f"<span style='color:{DIM.name()}'>{AUTHOR['title']}</span><br><br>"
            f"<a style='color:{GREEN.name()}' href='{AUTHOR['github']}'>GitHub</a> · "
            f"<a style='color:{GREEN.name()}' href='{AUTHOR['linkedin']}'>LinkedIn</a>"
        )
        info.setOpenExternalLinks(True)
        info.setTextFormat(Qt.TextFormat.RichText)
        lay.addWidget(info)

        close_btn = QPushButton(tr("close"))
        close_btn.clicked.connect(dlg.close)
        lay.addWidget(close_btn)
        dlg.exec()

    def _change_price_range(self, index):
        """Cambia el filtro de rango de precio."""
        self.config["price_range"] = index
        self._save_config()
        self.fetch_tickers()

    # ---------- backups ----------

    def _delete_old_backups(self):
        """Borra backups con más de 7 días."""
        try:
            r = requests.post(f"{BACKEND_URL}/api/backups/delete-old",
                              json={"days_keep": 7}, timeout=5)
            n = r.json().get("count", 0)
            QMessageBox.information(self, tr("backups"), tr("deleted_old", n=n))
        except requests.RequestException as e:
            QMessageBox.warning(self, tr("backups"), f"{tr('error')}: {e}")

    def _delete_all_backups(self):
        """Borra todos los backups previa confirmación."""
        ok = QMessageBox.question(self, tr("backups"), tr("confirm_del"))
        if ok == QMessageBox.StandardButton.Yes:
            try:
                r = requests.post(f"{BACKEND_URL}/api/backups/delete-all", timeout=5)
                n = r.json().get("count", 0)
                QMessageBox.information(self, tr("backups"), tr("deleted_all", n=n))
            except requests.RequestException as e:
                QMessageBox.warning(self, tr("backups"), f"{tr('error')}: {e}")


    # ---------- inicio automático con el sistema ----------

    def _launch_command(self):
        """Comando que arranca la app completa (backend + banner).

        Usa el script de arranque de la instalación si existe; si no,
        el intérprete actual con este main.py.
        """
        app_dir = Path(sys.argv[0]).resolve().parent
        script = app_dir / ("run.bat" if sys.platform == "win32" else "run.sh")
        if script.exists():
            return str(script)
        return f'"{sys.executable}" "{Path(sys.argv[0]).resolve()}"'

    def _autostart_file(self):
        """Ruta del artefacto de autostart según el SO."""
        home = Path.home()
        if sys.platform == "win32":
            return None  # Windows usa el registro, no un archivo
        if sys.platform == "darwin":
            return home / "Library" / "LaunchAgents" / "com.bergero.marketticker.plist"
        return home / ".config" / "autostart" / "market-ticker.desktop"

    def _autostart_enabled(self):
        """Consulta si el inicio automático está activo en este SO."""
        if sys.platform == "win32":
            try:
                import winreg
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                    r"Software\Microsoft\Windows\CurrentVersion\Run") as k:
                    winreg.QueryValueEx(k, "MarketTicker")
                return True
            except OSError:
                return False
        f = self._autostart_file()
        return f is not None and f.exists()

    def _set_autostart(self, enable):
        """Activa/desactiva el arranque automático al iniciar sesión."""
        cmd = self._launch_command()
        if sys.platform == "win32":
            import winreg
            key = r"Software\Microsoft\Windows\CurrentVersion\Run"
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key, 0,
                                winreg.KEY_SET_VALUE) as k:
                if enable:
                    winreg.SetValueEx(k, "MarketTicker", 0, winreg.REG_SZ, cmd)
                else:
                    try:
                        winreg.DeleteValue(k, "MarketTicker")
                    except OSError:
                        pass
            return

        f = self._autostart_file()
        if not enable:
            f.unlink(missing_ok=True)
            return
        f.parent.mkdir(parents=True, exist_ok=True)
        if sys.platform == "darwin":
            f.write_text(f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>com.bergero.marketticker</string>
  <key>ProgramArguments</key>
  <array><string>/bin/bash</string><string>-c</string><string>{cmd}</string></array>
  <key>RunAtLoad</key><true/>
</dict>
</plist>
""")
        else:
            f.write_text(f"""[Desktop Entry]
Type=Application
Name=Market Ticker
Comment=Ticker de cotizaciones
Exec={cmd}
Terminal=false
X-GNOME-Autostart-enabled=true
""")

    def closeEvent(self, event):
        """Al cerrar: Windows exige desregistrar el AppBar (X11 lo libera solo)."""
        if sys.platform == "win32":
            self._strut_windows(remove=True)
        event.accept()


def main():
    """Punto de entrada del banner."""
    import os
    # En Wayland, Qt no permite posicionar ventanas ni mantenerlas siempre
    # visibles; forzamos X11 (XWayland) donde ambas cosas funcionan.
    if sys.platform.startswith("linux") and os.environ.get("WAYLAND_DISPLAY"):
        os.environ.setdefault("QT_QPA_PLATFORM", "xcb")
    app = QApplication(sys.argv)
    banner = TickerBanner()
    banner.show()
    # La reserva de espacio necesita la ventana ya mapeada por el gestor
    QTimer.singleShot(400, banner._apply_strut)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
