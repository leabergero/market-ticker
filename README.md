# Market Ticker

Banner de cotizaciones en tiempo real, estilo cinta de bolsa: fino (32 px), sin marco, ancho completo de pantalla, siempre a la vista. Multiplataforma (Linux, Windows, macOS).

![estado](https://img.shields.io/badge/estado-beta-orange) ![python](https://img.shields.io/badge/python-3.10+-blue)

## Características

- **Cinta desplazable** con cotizaciones de **19 mercados** (Europa, América, Asia-Pacífico — del S&P 500 al MERVAL argentino), actualizadas cada 15 minutos vía yfinance
- **Noticias por activo** de las últimas **72 horas hábiles** — click en una cotización, click en el titular y se abre en el navegador
- **LED de estado**: verde = datos en vivo; rojo = sin conexión
- **Siempre visible**: reserva espacio de pantalla como una barra de tareas — las ventanas maximizadas se acomodan sin tapar el banner (Linux vía `_NET_WM_STRUT`, Windows vía API AppBar; macOS no lo permite)
- **3 idiomas** (🇪🇸 🇬🇧 🇩🇪) con banderas en la configuración
- **Filtros**: por mercado (multi-selección) y por rango de precio
- Posición arriba o abajo, inicio automático con el sistema, base SQLite local con rotación diaria y gestión de backups
- Tickers numéricos asiáticos con nombre legible (7203.T → TOYOTA)

## Instalación rápida (testers)

Descargá el zip de tu sistema desde [Releases](../../releases), descomprimí y:

- **Windows**: doble click en `install.bat` — instala, crea "Market Ticker" en el menú inicio y arranca solo
- **macOS**: `bash install.sh` — instala y arranca solo
- **Linux**: `bash installers/build_linux.sh` → `dist/run.sh`

El inicio automático con el sistema queda **activado por defecto** (se desactiva en ⚙).

Único requisito: [Python 3.10+](https://www.python.org/downloads/) (en Windows, marcar "Add Python to PATH").

## Arquitectura

```
backend/    Flask (127.0.0.1:5003) + APScheduler: scraping yfinance cada 15 min,
            SQLite con rotación diaria (23:59), API REST (tickers, news, backups)
frontend/   PyQt6: banner sin marco, cinta animada con hit-testing por cotización,
            i18n, reserva de espacio por SO, autostart por SO
installers/ Scripts de build por plataforma
release/    Empaquetador de los zips de distribución
```

En Wayland el banner fuerza X11 (XWayland) porque Wayland no permite posicionar ventanas ni reservar espacio; requiere `libxcb-cursor0`.

## API local

```
GET  /api/tickers?market=DAX,MERVAL&price_min=10&price_max=50
GET  /api/news?symbol=SAP.DE          # 72 h hábiles, en vivo con fallback a BD
GET  /api/health                      # incluye estado del último scrape (LED)
GET  /api/backups
POST /api/backups/delete-old          # {"days_keep": 7}
POST /api/backups/delete-all
```

## Autor

**Leandro R. Bergero** — MSc Finance & Banking (BSM-UPF)
[GitHub](https://github.com/leabergero) · [LinkedIn](https://www.linkedin.com/in/leandro-raul-bergero/)

## Licencia

MIT
