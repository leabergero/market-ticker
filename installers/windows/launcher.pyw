"""Lanzador silencioso de Market Ticker para Windows.

Arranca el backend en segundo plano y luego el banner, sin abrir
ninguna ventana de consola (por eso extensión .pyw + pythonw.exe).
Es el destino del acceso directo del menú inicio y del inicio automático.
Ningún fallo puede ser silencioso: la salida del backend va a
backend\\ticker.log (capturada desde acá, así se ven hasta los imports
rotos que pythonw se tragaba), la del banner a frontend.log, y si algo
no levanta se muestra un MessageBox con la cola del log.
"""
import ctypes
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
PYTHONW = APP_DIR / "venv" / "Scripts" / "pythonw.exe"
BACKEND_LOG = APP_DIR / "backend" / "ticker.log"
MB_ICONERROR = 0x10
ERROR_ALREADY_EXISTS = 183

# use_last_error=True es obligatorio: leer GetLastError con una llamada
# ctypes aparte devuelve valores viejos → un falso "ya está corriendo"
# dejaba la app sin abrir y sin mensaje.
KERNEL32 = ctypes.WinDLL("kernel32", use_last_error=True)


def alert(msg):
    ctypes.windll.user32.MessageBoxW(None, msg, "Market Ticker", MB_ICONERROR)


def already_running():
    """True si otro launcher sigue vivo (el mutex se mantiene mientras el
    banner corre) Y el banner realmente está en pantalla. La verificación
    de ventana evita que un mutex colgado deje la app inutilizable."""
    KERNEL32.CreateMutexW(None, False, "MarketTickerLauncher")
    if ctypes.get_last_error() != ERROR_ALREADY_EXISTS:
        return False
    return bool(ctypes.windll.user32.FindWindowW(None, "Market Ticker"))


def backend_running():
    try:
        urllib.request.urlopen("http://127.0.0.1:5003/api/health", timeout=1)
        return True
    except OSError:
        return False


def start_backend():
    """Lanza el backend con su salida capturada en ticker.log y espera
    hasta 15 s a que responda el health check."""
    with open(BACKEND_LOG, "a", buffering=1, encoding="utf-8",
              errors="replace") as log:
        subprocess.Popen([str(PYTHONW), str(APP_DIR / "backend" / "app.py")],
                         cwd=str(APP_DIR / "backend"),
                         stdin=subprocess.DEVNULL, stdout=log, stderr=log)
    for _ in range(15):
        time.sleep(1)
        if backend_running():
            return True
    return False


def log_tail(path, lines=12):
    try:
        text = Path(path).read_text(encoding="utf-8", errors="replace")
        return "\n".join(text.splitlines()[-lines:]) or "(log vacío)"
    except OSError:
        return "(el log no existe)"


def main():
    """Arranca backend (si no está ya corriendo) y banner."""
    if already_running():
        return
    if not PYTHONW.exists():
        alert("Falta el entorno de Python de Market Ticker.\n"
              "Ejecutá setup.bat (o install.bat) en la carpeta de instalación "
              "para recrearlo.")
        return
    if not backend_running() and not start_backend():
        alert("El backend de datos no arrancó: el banner va a decir "
              "\"sin conexión\".\n\n"
              f"Últimas líneas de {BACKEND_LOG}:\n\n{log_tail(BACKEND_LOG)}")
    with open(APP_DIR / "frontend.log", "a", buffering=1, encoding="utf-8",
              errors="replace") as log:
        rc = subprocess.call([str(PYTHONW), str(APP_DIR / "main.py")],
                             cwd=str(APP_DIR), stdin=subprocess.DEVNULL,
                             stdout=log, stderr=log)
    if rc != 0:
        alert("El banner terminó con un error.\n"
              f"Revisá el detalle en:\n{APP_DIR / 'frontend.log'}")


if __name__ == "__main__":
    main()
