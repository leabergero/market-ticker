import sys
import re
import json
import subprocess
import tempfile
import threading
import webbrowser
import requests
from pathlib import Path
from PyQt6.QtWidgets import (
    QApplication, QWidget, QHBoxLayout, QVBoxLayout, QGridLayout, QLabel,
    QPushButton, QDialog, QListWidget, QListWidgetItem, QMessageBox, QMenu,
    QCheckBox, QComboBox, QProgressDialog, QLineEdit
)
from datetime import datetime, timedelta
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QPoint, QPointF
from PyQt6.QtGui import (QFont, QColor, QPainter, QAction, QFontMetrics,
                         QPen, QPolygonF, QIcon)

BACKEND_URL = "http://127.0.0.1:5003"

# Versión de la app: fuente ÚNICA de verdad (los build scripts la leen de acá)
APP_VERSION = "0.3.2"
# Releases de GitHub contra los que se chequean actualizaciones
UPDATE_REPO = "leabergero/market-ticker"
UPDATE_API = f"https://api.github.com/repos/{UPDATE_REPO}/releases/latest"

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
        "update_title": "Actualización",
        "update_available": "Nueva versión {v} disponible — click para actualizar",
        "update_ask": "Hay una versión nueva de Market Ticker (v{v}).\n¿Actualizar ahora? La app se cerrará, se instalará la versión nueva y volverá a abrirse.",
        "update_now": "Actualizar ahora",
        "update_later": "Más tarde",
        "update_btn": "Actualizar a v{v}…",
        "update_check": "Buscar actualizaciones",
        "update_none": "Ya estás en la última versión (v{v}).",
        "update_no_asset": "El último release no incluye instalador para este sistema.",
        "update_err_check": "No se pudo consultar las actualizaciones. Probá más tarde.",
        "update_downloading": "Descargando la actualización…",
        "update_err_download": "Falló la descarga de la actualización.",
        "chart_label": "Evolución del precio — {d}",
        "chart_none": "Sin datos intradía para {s}.",
        "no_backend": "sin conexión con el backend — reiniciá la app o revisá ticker.log",
        "waiting_err": "sin datos del mercado — {e}",
        "change_range": "Variación diaria", "all_changes": "Todas las variaciones",
        "custom_tickers": "Tickers personalizados…",
        "custom_title": "Tickers personalizados",
        "custom_search_ph": "Buscar símbolo o compañía (p. ej. METR, Metrogas)…",
        "search": "Buscar",
        "custom_add": "Agregar seleccionado",
        "custom_remove": "Quitar seleccionado",
        "custom_mine": "Mis tickers (siempre en la cinta):",
        "custom_add_raw": "Agregar \"{s}\" tal cual (se valida contra Yahoo)",
        "custom_added": "{s} agregado a la cinta.",
        "my_tickers": "Mis tickers",
        "menu_tip": "Menú",
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
        "update_title": "Update",
        "update_available": "New version {v} available — click to update",
        "update_ask": "A new version of Market Ticker is available (v{v}).\nUpdate now? The app will close, install the new version and reopen.",
        "update_now": "Update now",
        "update_later": "Later",
        "update_btn": "Update to v{v}…",
        "update_check": "Check for updates",
        "update_none": "You are already on the latest version (v{v}).",
        "update_no_asset": "The latest release has no installer for this system.",
        "update_err_check": "Could not check for updates. Try again later.",
        "update_downloading": "Downloading update…",
        "update_err_download": "The update download failed.",
        "chart_label": "Price evolution — {d}",
        "chart_none": "No intraday data for {s}.",
        "no_backend": "no connection to the backend — restart the app or check ticker.log",
        "waiting_err": "no market data — {e}",
        "change_range": "Daily change", "all_changes": "All changes",
        "custom_tickers": "Custom tickers…",
        "custom_title": "Custom tickers",
        "custom_search_ph": "Search symbol or company (e.g. METR)…",
        "search": "Search",
        "custom_add": "Add selected",
        "custom_remove": "Remove selected",
        "custom_mine": "My tickers (always on the tape):",
        "custom_add_raw": "Add \"{s}\" as typed (validated against Yahoo)",
        "custom_added": "{s} added to the tape.",
        "my_tickers": "My tickers",
        "menu_tip": "Menu",
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
        "update_title": "Aktualisierung",
        "update_available": "Neue Version {v} verfügbar — zum Aktualisieren klicken",
        "update_ask": "Eine neue Version von Market Ticker ist verfügbar (v{v}).\nJetzt aktualisieren? Die App wird geschlossen, die neue Version installiert und wieder geöffnet.",
        "update_now": "Jetzt aktualisieren",
        "update_later": "Später",
        "update_btn": "Auf v{v} aktualisieren…",
        "update_check": "Nach Updates suchen",
        "update_none": "Sie verwenden bereits die neueste Version (v{v}).",
        "update_no_asset": "Das letzte Release enthält kein Installationspaket für dieses System.",
        "update_err_check": "Updates konnten nicht abgefragt werden. Versuchen Sie es später erneut.",
        "update_downloading": "Update wird heruntergeladen…",
        "update_err_download": "Der Download des Updates ist fehlgeschlagen.",
        "chart_label": "Kursverlauf — {d}",
        "chart_none": "Keine Intraday-Daten für {s}.",
        "no_backend": "keine Verbindung zum Backend — App neu starten oder ticker.log prüfen",
        "waiting_err": "keine Marktdaten — {e}",
        "change_range": "Tagesveränderung", "all_changes": "Alle Veränderungen",
        "custom_tickers": "Eigene Ticker…",
        "custom_title": "Eigene Ticker",
        "custom_search_ph": "Symbol oder Unternehmen suchen (z. B. METR)…",
        "search": "Suchen",
        "custom_add": "Auswahl hinzufügen",
        "custom_remove": "Auswahl entfernen",
        "custom_mine": "Meine Ticker (immer im Band):",
        "custom_add_raw": "\"{s}\" wie eingegeben hinzufügen (wird gegen Yahoo geprüft)",
        "custom_added": "{s} zum Band hinzugefügt.",
        "my_tickers": "Meine Ticker",
        "menu_tip": "Menü",
    },
}


def tr(key, **kw):
    """Traduce una clave al idioma activo (cae a español si falta)."""
    s = I18N.get(_lang, I18N["es"]).get(key) or I18N["es"].get(key, key)
    return s.format(**kw) if kw else s


def market_label(m):
    """Etiqueta de mercado con el país en el idioma activo. "CUSTOM" es el
    pseudo-mercado de los tickers personalizados del usuario."""
    if m == "CUSTOM":
        return tr("my_tickers")
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


# Nombre completo de cada símbolo de scraper.py (la lista es fija, así que
# un dict estático evita otra llamada a yfinance). Se usa en el diálogo de
# noticias/gráfico: por ticker solo no siempre se reconoce la compañía.
COMPANY_NAMES = {
    "^STOXX50E": "EURO STOXX 50", "ASML.AS": "ASML Holding", "MC.PA": "LVMH Moët Hennessy",
    "SAP.DE": "SAP", "NESN.SW": "Nestlé",
    "^GDAXI": "DAX 40", "SIE.DE": "Siemens", "ALV.DE": "Allianz",
    "MUV2.DE": "Münchener Rück",
    "^FCHI": "CAC 40", "OR.PA": "L'Oréal", "TTE.PA": "TotalEnergies", "AIR.PA": "Airbus",
    "^IBEX": "IBEX 35", "SAN.MC": "Banco Santander", "ITX.MC": "Inditex (Zara)",
    "IBE.MC": "Iberdrola", "TEF.MC": "Telefónica",
    "^FTSE": "FTSE 100", "SHEL.L": "Shell", "AZN.L": "AstraZeneca",
    "HSBA.L": "HSBC Holdings", "ULVR.L": "Unilever",
    "FTSEMIB.MI": "FTSE MIB", "ENI.MI": "Eni", "ISP.MI": "Intesa Sanpaolo",
    "UCG.MI": "UniCredit", "ENEL.MI": "Enel",
    "^SSMI": "Swiss Market Index", "NOVN.SW": "Novartis", "ROG.SW": "Roche",
    "UBSG.SW": "UBS Group",
    "^NYA": "NYSE Composite", "JPM": "JPMorgan Chase", "XOM": "Exxon Mobil",
    "JNJ": "Johnson & Johnson", "V": "Visa",
    "^IXIC": "NASDAQ Composite", "AAPL": "Apple", "MSFT": "Microsoft",
    "GOOGL": "Alphabet (Google)", "NVDA": "NVIDIA", "AMZN": "Amazon",
    "^GSPC": "S&P 500", "BRK-B": "Berkshire Hathaway", "LLY": "Eli Lilly",
    "AVGO": "Broadcom", "TSLA": "Tesla",
    "^GSPTSE": "S&P/TSX Composite", "RY.TO": "Royal Bank of Canada",
    "TD.TO": "Toronto-Dominion Bank", "SHOP.TO": "Shopify", "ENB.TO": "Enbridge",
    "^N225": "Nikkei 225", "7203.T": "Toyota Motor", "6758.T": "Sony Group",
    "9984.T": "SoftBank Group", "8306.T": "Mitsubishi UFJ Financial",
    "^HSI": "Hang Seng", "0700.HK": "Tencent Holdings", "9988.HK": "Alibaba Group",
    "0005.HK": "HSBC Holdings", "1299.HK": "AIA Group",
    "000001.SS": "SSE Composite", "600519.SS": "Kweichow Moutai",
    "601398.SS": "ICBC", "601857.SS": "PetroChina",
    "^KS11": "KOSPI", "005930.KS": "Samsung Electronics", "000660.KS": "SK Hynix",
    "005380.KS": "Hyundai Motor",
    "^BSESN": "BSE Sensex", "RELIANCE.NS": "Reliance Industries",
    "TCS.NS": "Tata Consultancy Services", "HDFCBANK.NS": "HDFC Bank",
    "^AXJO": "S&P/ASX 200", "BHP.AX": "BHP Group", "CBA.AX": "Commonwealth Bank",
    "CSL.AX": "CSL",
    "^BVSP": "Ibovespa", "VALE3.SA": "Vale", "PETR4.SA": "Petrobras",
    "ITUB4.SA": "Itaú Unibanco",
    "^MERV": "S&P MERVAL", "GGAL.BA": "Grupo Financiero Galicia", "YPFD.BA": "YPF",
    "PAMP.BA": "Pampa Energía", "CEPU.BA": "Central Puerto", "ALUA.BA": "Aluar",
}


# Nombres de los tickers personalizados del usuario (symbol → name), se
# cargan del backend (/api/custom) al arrancar y al modificar la lista.
CUSTOM_NAMES = {}


def company_label(symbol):
    """Nombre completo para diálogos: "Compañía (TICKER)"; si el símbolo no
    está en el dict (no debería pasar), cae a la etiqueta de la cinta."""
    name = COMPANY_NAMES.get(symbol) or CUSTOM_NAMES.get(symbol)
    short = display_label(symbol)
    return f"{name} ({short})" if name and name != short else short


def ver_tuple(s):
    """Convierte "v0.2.1" en (0, 2, 1) para comparar versiones."""
    return tuple(int(n) for n in re.findall(r"\d+", s or "")[:3]) or (0,)


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

# Escalas de variación diaria en % (etiqueta, change_min, change_max).
# La primera etiqueta se traduce con tr("all_changes"); el resto es neutro.
PCT_RANGES = [
    ("all_changes", None, None),
    ("▲ > 0 %", 0, None),
    ("▲ > +2 %", 2, None),
    ("▲ > +5 %", 5, None),
    ("▼ < 0 %", None, 0),
    ("▼ < −2 %", None, -2),
    ("▼ < −5 %", None, -5),
]


class TapeWidget(QWidget):
    """Cinta desplazable que dibuja las cotizaciones y detecta clicks."""

    SPEED_PX = 1          # píxeles por tick de animación
    TICK_MS = 30          # intervalo de animación
    GAP = 48              # separación entre cotizaciones

    def __init__(self, parent=None):
        super().__init__(parent)
        self.tickers = []          # datos actuales
        self.status_msg = None     # texto a mostrar mientras no hay datos
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

    def set_status(self, msg):
        """Mensaje mostrado mientras la cinta está vacía (diagnóstico:
        distingue backend caído de scrape sin datos)."""
        self.status_msg = msg
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
            p.drawText(10, y, self.status_msg or tr("waiting"))
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


class HistoryChart(QWidget):
    """Gráfico de línea de la última sesión (intradía 15 min), estética HUD.

    Mismo patrón que TapeWidget: paintEvent propio con QPainter, sin
    dependencias de gráficos (los instaladores no cambian).
    """

    MARGIN = 10       # margen interior del trazado
    LABEL_H = 16      # franja superior/inferior para las etiquetas

    def __init__(self, points, parent=None):
        # points: [(iso_timestamp, precio)] en orden cronológico
        super().__init__(parent)
        self.points = points
        self.setMinimumHeight(150)
        self.font_small = QFont("DejaVu Sans Mono", 8)

    def paintEvent(self, event):
        p = QPainter(self)
        p.fillRect(self.rect(), BG)
        prices = [pt[1] for pt in self.points]
        if len(prices) < 2:
            return
        lo, hi = min(prices), max(prices)
        span = (hi - lo) or 1.0
        up = prices[-1] >= prices[0]
        color = GREEN if up else RED

        m = self.MARGIN
        x0, y0 = m, m + self.LABEL_H
        w = self.width() - 2 * m
        h = self.height() - 2 * (m + self.LABEL_H)
        if w <= 0 or h <= 0:
            return

        # línea punteada de referencia en el precio de apertura
        base_y = y0 + h - (prices[0] - lo) * h / span
        pen = QPen(DIM)
        pen.setStyle(Qt.PenStyle.DotLine)
        p.setPen(pen)
        p.drawLine(x0, int(base_y), x0 + w, int(base_y))

        # curva del día
        step = w / (len(prices) - 1)
        poly = QPolygonF([QPointF(x0 + i * step, y0 + h - (v - lo) * h / span)
                          for i, v in enumerate(prices)])
        pen = QPen(color)
        pen.setWidthF(1.6)
        p.setPen(pen)
        p.drawPolyline(poly)

        # etiquetas: máx/mín (izq), variación de la sesión y último (der),
        # horas de inicio/fin (abajo)
        p.setFont(self.font_small)
        fm = QFontMetrics(self.font_small)
        p.setPen(DIM)
        p.drawText(x0, m + fm.ascent(), f"max {hi:,.2f}")
        p.drawText(x0, self.height() - m - fm.descent(), f"min {lo:,.2f}")
        t0, t1 = self.points[0][0][11:16], self.points[-1][0][11:16]
        hours = f"{t0} – {t1}"
        p.drawText(x0 + w - fm.horizontalAdvance(hours),
                   self.height() - m - fm.descent(), hours)
        pct = (prices[-1] - prices[0]) / prices[0] * 100 if prices[0] else 0
        last = f"{prices[-1]:,.2f} {'▲' if up else '▼'}{abs(pct):.2f}%"
        p.setPen(color)
        p.drawText(x0 + w - fm.horizontalAdvance(last), m + fm.ascent(), last)
        p.end()


class TickerBanner(QWidget):
    """Banner de cotizaciones: fino, sin marco, ancho completo de pantalla."""

    HEIGHT = 32

    # Señales para volver del hilo de red al hilo de la interfaz (Qt las
    # encola automáticamente cuando se emiten desde otro hilo)
    update_checked = pyqtSignal(dict)
    update_progress = pyqtSignal(int)
    update_finished = pyqtSignal(bool, str)

    def __init__(self):
        super().__init__()
        self.config_path = Path("./config/config.json")
        self.config = self._load_config()
        self.live = False  # estado del último fetch (LED)

        self.setWindowTitle("Market Ticker")
        # Nota: sin Qt.Tool en Linux/macOS — bajo Wayland/XWayland ese flag
        # oculta la ventana cuando la app pierde el foco, y un banner debe
        # quedar siempre visible. En Windows sí lo usamos: ahí un Tool window
        # no se oculta al perder foco y es lo que saca al banner de la barra
        # de tareas (WS_EX_TOOLWINDOW).
        flags = (Qt.WindowType.FramelessWindowHint
                 | Qt.WindowType.WindowStaysOnTopHint)
        if sys.platform == "win32":
            flags |= Qt.WindowType.Tool
        self.setWindowFlags(flags)
        self._init_ui()
        self._place()
        # Si el área de trabajo cambia (el sistema informa sus barras tarde,
        # o aplica nuestra reserva), reposicionarse automáticamente.
        QApplication.primaryScreen().availableGeometryChanged.connect(
            lambda _: self._place())

        # Autostart viene activado por defecto: registrarlo en el SO en el
        # primer arranque (el usuario lo desactiva desde ⚙ si no lo quiere).
        if self.config.get("autostart") and not self._autostart_enabled():
            try:
                self._set_autostart(True)
            except Exception:
                pass

        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.fetch_tickers)
        self.refresh_timer.start(60 * 1000)  # consulta al backend cada 1 min
        self._load_custom_names()
        self.fetch_tickers()

        # Actualizaciones: chequeo contra GitHub al arrancar (diferido para
        # no demorar el banner) y después una vez por día mientras corre.
        self.update_info = None      # {"version": ..., "url": ...} si hay nueva
        self._manual_check = False   # el chequeo manual (⚙) siempre responde
        self._dl_dialog = None
        self.update_checked.connect(self._on_update_checked)
        self.update_progress.connect(self._on_update_progress)
        self.update_finished.connect(self._on_update_finished)
        QTimer.singleShot(15 * 1000, self._check_updates_async)
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self._check_updates_async)
        self.update_timer.start(24 * 3600 * 1000)

    # ---------- configuración ----------

    def _load_config(self):
        """Carga config.json normalizando valores de versiones anteriores."""
        default = {"position": "top", "markets": [], "price_range": 0,
                   "pct_range": 0, "reserve_space": True, "lang": "es",
                   "autostart": True, "declined_update": ""}
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
        cfg["markets"] = [m for m in cfg["markets"] if m in MARKETS + ["CUSTOM"]]
        if cfg.get("position") not in ("top", "bottom"):
            cfg["position"] = "top"
        if not isinstance(cfg.get("price_range"), int) or not (0 <= cfg["price_range"] < len(PRICE_RANGES)):
            cfg["price_range"] = 0
        if not isinstance(cfg.get("pct_range"), int) or not (0 <= cfg["pct_range"] < len(PCT_RANGES)):
            cfg["pct_range"] = 0
        cfg["reserve_space"] = bool(cfg.get("reserve_space", True))
        if cfg.get("lang") not in I18N:
            cfg["lang"] = "es"
        cfg["autostart"] = bool(cfg.get("autostart", True))
        cfg["declined_update"] = str(cfg.get("declined_update") or "")
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

        # ⬆ aparece solo cuando hay una versión nueva en GitHub
        self.update_btn = QPushButton("⬆")
        self.update_btn.setFixedSize(18, 18)
        self.update_btn.setStyleSheet(
            f"QPushButton {{color:{GREEN.name()}; background:transparent;"
            " border:none; font-size:12px; font-weight:bold;}"
            "QPushButton:hover {color:#c9d1d9;}"
        )
        self.update_btn.clicked.connect(self._prompt_update)
        self.update_btn.hide()
        row.addWidget(self.update_btn)

        # ☰ despliega el mismo menú que el click derecho (más descubrible,
        # y en macOS/trackpads el click derecho no siempre está a mano)
        self.menu_btn = QPushButton("☰")
        self.menu_btn.setFixedSize(18, 18)
        self.menu_btn.setToolTip(tr("menu_tip"))
        self.menu_btn.setStyleSheet(
            "QPushButton {color:#4a5568; background:transparent; border:none; font-size:12px;}"
            "QPushButton:hover {color:#c9d1d9;}"
        )
        self.menu_btn.clicked.connect(self._show_menu)
        row.addWidget(self.menu_btn)

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
        # SHAppBarMessage trabaja en píxeles físicos; Qt en lógicos (con
        # escalado 125/150% difieren y la reserva quedaba corta/corrida).
        geo = self.screen().geometry()
        dpr = self.screen().devicePixelRatio()
        abd.uEdge = ABE_BOTTOM if self.config.get("position") == "bottom" else ABE_TOP
        abd.rc.left = round(geo.x() * dpr)
        abd.rc.right = round((geo.x() + geo.width()) * dpr)
        if abd.uEdge == ABE_TOP:
            abd.rc.top = round(geo.y() * dpr)
            abd.rc.bottom = round((geo.y() + self.HEIGHT) * dpr)
        else:
            abd.rc.bottom = round((geo.y() + geo.height()) * dpr)
            abd.rc.top = abd.rc.bottom - round(self.HEIGHT * dpr)
        shell.SHAppBarMessage(ABM_QUERYPOS, ctypes.byref(abd))
        shell.SHAppBarMessage(ABM_SETPOS, ctypes.byref(abd))
        self._strut_active = True
        # ocupar exactamente el rectángulo concedido por el sistema
        self.move(round(abd.rc.left / dpr), round(abd.rc.top / dpr))

    def _set_led(self, live, detail=None):
        """Actualiza el LED: verde = datos en vivo, rojo = sin conexión.
        detail agrega la causa concreta al tooltip (diagnóstico)."""
        self.live = live
        self._led_detail = detail
        color = GREEN.name() if live else RED.name()
        tip = tr("live") if live else tr("not_live")
        if detail:
            tip = f"{tip}\n{detail}"
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
            _, cmin, cmax = PCT_RANGES[self.config.get("pct_range", 0)]
            if cmin is not None:
                params["change_min"] = cmin
            if cmax is not None:
                params["change_max"] = cmax
            r = requests.get(f"{BACKEND_URL}/api/tickers", params=params, timeout=5)
            r.raise_for_status()
            tickers = r.json().get("tickers", [])
            self.tape.set_tickers(tickers)
            live, error = self._backend_status()
            self._set_led(live, error)
            if not tickers:
                # cinta vacía: mostrar la causa real en vez del genérico
                self.tape.set_status(tr("waiting_err", e=error) if error else None)
        except requests.RequestException as e:
            # el backend no contesta: eso NO es "esperando datos"
            self._set_led(False, str(e))
            self.tape.set_status(tr("no_backend"))

    def _load_custom_names(self):
        """Refresca el mapa symbol→nombre de los tickers personalizados."""
        try:
            r = requests.get(f"{BACKEND_URL}/api/custom", timeout=5)
            CUSTOM_NAMES.clear()
            CUSTOM_NAMES.update({t["symbol"]: t.get("name") or ""
                                 for t in r.json().get("tickers", [])})
        except (requests.RequestException, ValueError):
            pass  # backend viejo sin /api/custom o backend caído
        self._ensure_custom_market()

    def _ensure_custom_market(self):
        """Invariante pedido por el usuario: mientras haya tickers
        personalizados, el mercado "Mis tickers" queda seleccionado (así
        nunca desaparecen de la cinta por un filtro de mercados)."""
        markets = self.config.get("markets") or []
        if CUSTOM_NAMES and markets and "CUSTOM" not in markets:
            self.config["markets"].append("CUSTOM")
            self._save_config()
        elif not CUSTOM_NAMES and "CUSTOM" in markets:
            # sin tickers personalizados el pseudo-mercado no tiene sentido
            self.config["markets"].remove("CUSTOM")
            self._save_config()

    def _backend_status(self):
        """(vivo, error): vivo si el backend scrapeó datos reales hace menos
        de 20 min; error es la causa del último scrape fallido (o None)."""
        try:
            r = requests.get(f"{BACKEND_URL}/api/health", timeout=5)
            info = r.json().get("last_scrape", {})
            error = info.get("error")
            if info.get("ok") and info.get("time"):
                age = datetime.now() - datetime.fromisoformat(info["time"])
                return age < timedelta(minutes=20), error
            return False, error
        except (requests.RequestException, ValueError):
            return False, None

    def show_news(self, symbol):
        """Muestra el gráfico intradía y las noticias del símbolo clickeado."""
        try:
            r = requests.get(f"{BACKEND_URL}/api/news", params={"symbol": symbol}, timeout=5)
            news = r.json().get("news", [])
        except requests.RequestException:
            news = []
        # curva de la última sesión (backend viejo sin /api/history → sin gráfico)
        try:
            r = requests.get(f"{BACKEND_URL}/api/history",
                             params={"symbol": symbol}, timeout=15)
            points = [(pt["t"], pt["p"]) for pt in r.json().get("points", [])]
        except (requests.RequestException, ValueError, KeyError, TypeError):
            points = []

        dlg = QDialog(self)
        dlg.setWindowTitle(f"{tr('news_title')} — {company_label(symbol)}")
        dlg.setStyleSheet(f"background-color: {BG.name()}; color: {FG.name()};")
        dlg.resize(560, 500 if points else 360)
        lay = QVBoxLayout(dlg)
        if points:
            lay.addWidget(QLabel(tr("chart_label", d=points[0][0][:10])))
            lay.addWidget(HistoryChart(points))
        else:
            lay.addWidget(QLabel(tr("chart_none", s=company_label(symbol))))
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
            lay.addWidget(QLabel(tr("news_none", s=company_label(symbol))))
        btn = QPushButton(tr("close"))
        btn.clicked.connect(dlg.close)
        lay.addWidget(btn)
        dlg.exec()

    # ---------- menú contextual ----------

    def contextMenuEvent(self, event):
        """Click derecho: el menú principal."""
        self._build_menu().exec(event.globalPos())

    def _show_menu(self):
        """Botón ☰: el mismo menú del click derecho, desplegado desde ahí."""
        self._build_menu().exec(
            self.menu_btn.mapToGlobal(QPoint(0, self.menu_btn.height())))

    def _build_menu(self):
        """Menú principal: posición, filtros y gestión de backups (lo usan
        el click derecho y el botón ☰)."""
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
        if CUSTOM_NAMES:
            # los tickers personalizados como pseudo-mercado: permite
            # verlos solos o combinados (con filtro activo quedan siempre
            # seleccionados vía _ensure_custom_market)
            mkt_menu.addSeparator()
            act = QAction(market_label("CUSTOM"), self, checkable=True)
            act.setChecked("CUSTOM" in self.config.get("markets", []))
            act.triggered.connect(lambda _: self._toggle_market("CUSTOM"))
            mkt_menu.addAction(act)

        price_menu = menu.addMenu(tr("price_range"))
        for i, (label, _, _) in enumerate(PRICE_RANGES):
            act = QAction(label if i else tr("all_prices"), self, checkable=True)
            act.setChecked(self.config.get("price_range", 0) == i)
            act.triggered.connect(lambda _, v=i: self._change_price_range(v))
            price_menu.addAction(act)

        pct_menu = menu.addMenu(tr("change_range"))
        for i, (label, _, _) in enumerate(PCT_RANGES):
            act = QAction(label if i else tr("all_changes"), self, checkable=True)
            act.setChecked(self.config.get("pct_range", 0) == i)
            act.triggered.connect(lambda _, v=i: self._change_pct_range(v))
            pct_menu.addAction(act)

        menu.addAction(tr("custom_tickers"), self._show_custom_tickers)

        menu.addSeparator()
        menu.addAction(tr("refresh"), self.fetch_tickers)

        bk_menu = menu.addMenu(tr("backups"))
        bk_menu.addAction(tr("del_old"), self._delete_old_backups)
        bk_menu.addAction(tr("del_all"), self._delete_all_backups)

        menu.addSeparator()
        menu.addAction(tr("about"), self._show_about)
        menu.addAction(tr("quit"), self.close)
        return menu

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
        self._ensure_custom_market()
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
        listed = MARKETS + (["CUSTOM"] if CUSTOM_NAMES else [])
        for i, m in enumerate(listed):
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
        # actualización siempre a mano desde acá (aunque se haya pospuesto)
        upd_btn = QPushButton(
            tr("update_btn", v=self.update_info["version"]) if self.update_info
            else tr("update_check"))
        upd_btn.clicked.connect(self._settings_update_clicked)
        save_btn = QPushButton(tr("save"))
        cancel_btn = QPushButton(tr("cancel"))
        btn_row.addWidget(about_btn)
        btn_row.addWidget(upd_btn)
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
            self._ensure_custom_market()
            self._remove_strut()
            self._place()
            QTimer.singleShot(250, self._apply_strut)
            self.fetch_tickers()

    def _settings_update_clicked(self):
        """Botón de ⚙: actualiza si ya hay versión conocida, si no chequea."""
        if self.update_info:
            self._prompt_update()
        else:
            self._manual_check = True
            self._check_updates_async()

    def _set_lang(self, code, dlg=None):
        """Cambia el idioma de la interfaz y refresca los textos persistentes."""
        global _lang
        _lang = code
        self.config["lang"] = code
        self._save_config()
        self.gear_btn.setToolTip(tr("gear_tip"))
        self.close_btn.setToolTip(tr("close"))
        self.menu_btn.setToolTip(tr("menu_tip"))
        self._set_led(self.live, getattr(self, "_led_detail", None))
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
            f"<b>Market Ticker</b> v{APP_VERSION}<br>"
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

    def _change_pct_range(self, index):
        """Cambia el filtro de variación diaria en %."""
        self.config["pct_range"] = index
        self._save_config()
        self.fetch_tickers()

    def _show_custom_tickers(self):
        """Diálogo de tickers personalizados: buscador contra Yahoo, agregar
        con + y quitar con − (la lista persiste en el backend y sus símbolos
        entran al scrape cada 15 min como mercado CUSTOM)."""
        dlg = QDialog(self)
        dlg.setWindowTitle(tr("custom_title"))
        dlg.setStyleSheet(f"background-color: {BG.name()}; color: {FG.name()};")
        dlg.resize(500, 460)
        lay = QVBoxLayout(dlg)

        srow = QHBoxLayout()
        edit = QLineEdit()
        edit.setPlaceholderText(tr("custom_search_ph"))
        sbtn = QPushButton(tr("search"))
        srow.addWidget(edit, stretch=1)
        srow.addWidget(sbtn)
        lay.addLayout(srow)

        results = QListWidget()
        lay.addWidget(results, stretch=2)
        add_btn = QPushButton("+ " + tr("custom_add"))
        lay.addWidget(add_btn)

        lay.addWidget(QLabel(tr("custom_mine")))
        mine = QListWidget()
        lay.addWidget(mine, stretch=1)
        del_btn = QPushButton("− " + tr("custom_remove"))
        lay.addWidget(del_btn)

        msg = QLabel("")
        msg.setStyleSheet(f"color: {DIM.name()};")
        lay.addWidget(msg)
        close_btn = QPushButton(tr("close"))
        close_btn.clicked.connect(dlg.close)
        lay.addWidget(close_btn)

        role = Qt.ItemDataRole.UserRole

        def refresh_mine():
            self._load_custom_names()
            mine.clear()
            for sym, name in sorted(CUSTOM_NAMES.items()):
                item = QListWidgetItem(f"{sym} — {name}" if name else sym)
                item.setData(role, sym)
                mine.addItem(item)

        def do_search():
            q = edit.text().strip()
            if not q:
                return
            results.clear()
            msg.setText("…")
            QApplication.processEvents()
            try:
                r = requests.get(f"{BACKEND_URL}/api/search",
                                 params={"q": q}, timeout=15)
                found = r.json().get("results", [])
            except (requests.RequestException, ValueError):
                found = []
            for f in found:
                extra = f"   [{f['exchange']}]" if f.get("exchange") else ""
                item = QListWidgetItem(f"{f['symbol']} — {f['name']}{extra}")
                item.setData(role, (f["symbol"], f["name"]))
                results.addItem(item)
            if not found:
                # sin resultados: ofrecer el texto tal cual (el backend lo
                # valida contra Yahoo al agregar)
                item = QListWidgetItem(tr("custom_add_raw", s=q.upper()))
                item.setData(role, (q.upper(), ""))
                results.addItem(item)
            msg.setText("")

        def do_add():
            item = results.currentItem()
            if item is None:
                return
            sym, name = item.data(role)
            msg.setText("…")
            QApplication.processEvents()
            try:
                r = requests.post(f"{BACKEND_URL}/api/custom",
                                  json={"symbol": sym, "name": name}, timeout=30)
                if r.ok:
                    msg.setText(tr("custom_added", s=sym))
                    refresh_mine()
                    self.fetch_tickers()
                else:
                    msg.setText(r.json().get("error") or tr("error"))
            except (requests.RequestException, ValueError):
                msg.setText(tr("no_backend"))

        def do_del():
            item = mine.currentItem()
            if item is None:
                return
            try:
                requests.delete(f"{BACKEND_URL}/api/custom/{item.data(role)}",
                                timeout=10)
            except requests.RequestException:
                pass
            refresh_mine()
            self.fetch_tickers()

        sbtn.clicked.connect(do_search)
        edit.returnPressed.connect(do_search)
        add_btn.clicked.connect(do_add)
        results.itemDoubleClicked.connect(lambda _: do_add())
        del_btn.clicked.connect(do_del)
        refresh_mine()
        dlg.exec()

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


    # ---------- actualizaciones (releases de GitHub) ----------

    def _check_updates_async(self):
        """Consulta GitHub en un hilo aparte (no bloquea la cinta)."""
        threading.Thread(target=self._check_updates_worker, daemon=True).start()

    def _check_updates_worker(self):
        """Compara APP_VERSION con el último release y busca el instalador
        del SO actual entre sus assets. Corre en un hilo: solo emite señales."""
        try:
            r = requests.get(UPDATE_API, timeout=10,
                             headers={"Accept": "application/vnd.github+json"})
            r.raise_for_status()
            data = r.json()
            tag = data.get("tag_name") or data.get("name") or ""
            if ver_tuple(tag) <= ver_tuple(APP_VERSION):
                self.update_checked.emit({"status": "none"})
                return
            ext = {"win32": ".msi", "darwin": ".pkg"}.get(sys.platform, ".deb")
            url = next((a.get("browser_download_url")
                        for a in data.get("assets", [])
                        if a.get("name", "").endswith(ext)), None)
            version = tag.lstrip("vV")
            if url:
                self.update_checked.emit(
                    {"status": "update", "version": version, "url": url})
            else:
                self.update_checked.emit({"status": "no_asset"})
        except (requests.RequestException, ValueError):
            self.update_checked.emit({"status": "error"})

    def _on_update_checked(self, info):
        """Reacciona al resultado del chequeo (ya en el hilo de la UI)."""
        manual, self._manual_check = self._manual_check, False
        status = info.get("status")
        if status == "update":
            self.update_info = info
            self.update_btn.setToolTip(tr("update_available", v=info["version"]))
            if manual:
                self._prompt_update()
            elif self.config.get("declined_update") != info["version"]:
                self.update_btn.show()
        elif manual:
            if status == "none":
                QMessageBox.information(self, tr("update_title"),
                                        tr("update_none", v=APP_VERSION))
            elif status == "no_asset":
                QMessageBox.warning(self, tr("update_title"), tr("update_no_asset"))
            else:
                QMessageBox.warning(self, tr("update_title"), tr("update_err_check"))

    def _prompt_update(self):
        """Ofrece actualizar; si el usuario desiste, el ⬆ se oculta y la
        actualización queda disponible desde ⚙ Configuración."""
        if not self.update_info:
            return
        v = self.update_info["version"]
        box = QMessageBox(self)
        box.setWindowTitle(tr("update_title"))
        box.setText(tr("update_ask", v=v))
        yes = box.addButton(tr("update_now"), QMessageBox.ButtonRole.AcceptRole)
        box.addButton(tr("update_later"), QMessageBox.ButtonRole.RejectRole)
        box.exec()
        if box.clickedButton() is yes:
            self._start_update()
        else:
            self.config["declined_update"] = v
            self._save_config()
            self.update_btn.hide()

    def _start_update(self):
        """Descarga el instalador en un hilo mostrando el progreso."""
        self._dl_dialog = QProgressDialog(tr("update_downloading"), None, 0, 100, self)
        self._dl_dialog.setWindowTitle(tr("update_title"))
        self._dl_dialog.setWindowModality(Qt.WindowModality.ApplicationModal)
        self._dl_dialog.setMinimumDuration(0)
        self._dl_dialog.setValue(0)
        threading.Thread(target=self._download_worker,
                         args=(self.update_info["url"],), daemon=True).start()

    def _download_worker(self, url):
        """Baja el asset a un archivo temporal. Corre en un hilo."""
        try:
            dest = Path(tempfile.gettempdir()) / url.rsplit("/", 1)[-1]
            with requests.get(url, stream=True, timeout=30) as r:
                r.raise_for_status()
                total = int(r.headers.get("content-length") or 0)
                done = 0
                with open(dest, "wb") as f:
                    for chunk in r.iter_content(chunk_size=65536):
                        f.write(chunk)
                        done += len(chunk)
                        if total:
                            self.update_progress.emit(int(done * 100 / total))
            self.update_finished.emit(True, str(dest))
        except (requests.RequestException, OSError) as e:
            self.update_finished.emit(False, str(e))

    def _on_update_progress(self, pct):
        if self._dl_dialog is not None:
            self._dl_dialog.setValue(pct)

    def _on_update_finished(self, ok, payload):
        if self._dl_dialog is not None:
            self._dl_dialog.close()
            self._dl_dialog = None
        if not ok:
            QMessageBox.warning(self, tr("update_title"),
                                f"{tr('update_err_download')}\n{payload}")
            return
        self._install_update(payload)

    def _install_update(self, installer_path):
        """Deja un script actualizador corriendo aparte y cierra la app.

        El script instala el paquete con el mecanismo nativo del SO (que
        reemplaza/elimina la versión actual: MajorUpgrade en el MSI,
        dpkg -i, installer sobre /Applications) y relanza Market Ticker.
        Si el usuario cancela la autorización, relanza la versión actual.
        """
        tmp = Path(tempfile.gettempdir())
        if sys.platform == "win32":
            # launcher.vbs de la instalación MSI (ruta fija per-user)
            script = tmp / "market-ticker-update.bat"
            script.write_text(
                '@echo off\r\n'
                'timeout /t 2 /nobreak >nul\r\n'
                'for /f "tokens=5" %%p in (\'netstat -ano ^| findstr ":5003" '
                '^| findstr "LISTENING"\') do taskkill /f /pid %%p >nul 2>nul\r\n'
                f'msiexec /i "{installer_path}" /passive\r\n'
                'start "" wscript "%LocalAppData%\\Programs\\Market Ticker\\launcher.vbs"\r\n',
                encoding="ascii")
            subprocess.Popen(["cmd.exe", "/c", str(script)],
                             creationflags=0x08000000)  # CREATE_NO_WINDOW
        elif sys.platform == "darwin":
            script = tmp / "market-ticker-update.sh"
            script.write_text(
                '#!/bin/bash\n'
                'sleep 1\n'
                f'PKG="{installer_path}"\n'
                'osascript -e "do shell script \\"installer -pkg \'$PKG\' -target /\\"'
                ' with administrator privileges"\n'
                'kill $(lsof -ti :5003) 2>/dev/null\n'
                'sleep 1\n'
                'open -a "Market Ticker"\n')
            script.chmod(0o755)
            subprocess.Popen(["/bin/bash", str(script)], start_new_session=True)
        else:
            # el prerm del paquete viejo ya mata el backend (fuser -k 5003)
            script = tmp / "market-ticker-update.sh"
            script.write_text(
                '#!/bin/bash\n'
                'sleep 1\n'
                f'pkexec /usr/bin/dpkg -i "{installer_path}"\n'
                'setsid /usr/bin/market-ticker >/dev/null 2>&1 &\n')
            script.chmod(0o755)
            subprocess.Popen(["/bin/bash", str(script)], start_new_session=True)
        self.close()

    # ---------- inicio automático con el sistema ----------

    def _launch_command(self):
        """Comando que arranca la app completa (backend + banner).

        Usa el script de arranque de la instalación si existe; si no,
        el intérprete actual con este main.py.
        """
        app_dir = Path(sys.argv[0]).resolve().parent
        if sys.platform == "win32":
            # launcher.pyw + pythonw = sin ventanas de consola al iniciar sesión
            pyw = app_dir / "venv" / "Scripts" / "pythonw.exe"
            launcher = app_dir / "launcher.pyw"
            if pyw.exists() and launcher.exists():
                return f'"{pyw}" "{launcher}"'
            script = app_dir / "run.bat"
        else:
            script = app_dir / "run.sh"
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


def _app_icon():
    """Icono propio de la app, buscándolo en los layouts instalado (assets/
    junto a main.py) y de desarrollo (../assets). None si no aparece
    (recordar: setWindowIcon(None) crashea)."""
    here = Path(__file__).resolve().parent
    for cand in (here / "assets" / "ticker.png",
                 here.parent / "assets" / "ticker.png",
                 here / "assets" / "ticker.ico"):
        if cand.exists():
            return QIcon(str(cand))
    return None


def _hide_dock_icon_macos():
    """Saca el proceso del Dock de macOS (política Accessory), llamando a
    AppKit por ctypes para no sumar pyobjc como dependencia. El Info.plist
    no sirve acá: el proceso visible es el python del venv, no el bundle.
    Si algo falla la app sigue, solo que con icono en el Dock."""
    try:
        import ctypes
        objc = ctypes.cdll.LoadLibrary("/usr/lib/libobjc.dylib")
        ctypes.cdll.LoadLibrary(
            "/System/Library/Frameworks/AppKit.framework/AppKit")
        objc.objc_getClass.restype = ctypes.c_void_p
        objc.objc_getClass.argtypes = [ctypes.c_char_p]
        objc.sel_registerName.restype = ctypes.c_void_p
        objc.sel_registerName.argtypes = [ctypes.c_char_p]
        send = ctypes.CFUNCTYPE(ctypes.c_void_p, ctypes.c_void_p,
                                ctypes.c_void_p)(("objc_msgSend", objc))
        send_i = ctypes.CFUNCTYPE(ctypes.c_bool, ctypes.c_void_p,
                                  ctypes.c_void_p, ctypes.c_long)(
                                      ("objc_msgSend", objc))
        nsapp = send(objc.objc_getClass(b"NSApplication"),
                     objc.sel_registerName(b"sharedApplication"))
        # 1 = NSApplicationActivationPolicyAccessory (sin Dock ni menú)
        send_i(nsapp, objc.sel_registerName(b"setActivationPolicy:"), 1)
    except Exception:
        pass


def main():
    """Punto de entrada del banner."""
    import os
    # En Wayland, Qt no permite posicionar ventanas ni mantenerlas siempre
    # visibles; forzamos X11 (XWayland) donde ambas cosas funcionan.
    if sys.platform.startswith("linux") and os.environ.get("WAYLAND_DISPLAY"):
        os.environ.setdefault("QT_QPA_PLATFORM", "xcb")
    if sys.platform == "win32":
        # Sin AppUserModelID propio, la barra de tareas agrupa la ventana
        # bajo pythonw.exe y muestra el icono de Python en vez del nuestro.
        import ctypes
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                "LeandroBergero.MarketTicker")
        except Exception:
            pass
    app = QApplication(sys.argv)
    icon = _app_icon()
    if icon is not None:
        app.setWindowIcon(icon)
    if sys.platform == "darwin":
        _hide_dock_icon_macos()
    banner = TickerBanner()
    banner.show()
    # La reserva de espacio necesita la ventana ya mapeada por el gestor
    QTimer.singleShot(400, banner._apply_strut)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
