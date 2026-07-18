# Changelog — Market Ticker

Todas las novedades relevantes de cada versión. Formato basado en
[Keep a Changelog](https://keepachangelog.com/es-ES/); versionado SemVer.

## Sin publicar

### Agregado
- **Grosor del banner configurable** (⚙ → "Grosor del banner", 20–64 px,
  default 32): en Windows el banner se sentía más invasivo que en Linux;
  ahora cada quien elige el alto de la franja. La reserva de espacio
  (strut/AppBar) y el posicionado siguen el valor elegido.

## v0.3.2 — 2026-07-18

### Agregado
- **Tickers personalizados**: nuevo diálogo (☰ o click derecho → "Tickers
  personalizados…") con buscador contra Yahoo Finance; los símbolos se
  agregan con "+" (validados y con cotización inmediata en la cinta,
  p. ej. METR.BA aunque no esté en los 19 mercados) y se quitan de a uno
  con "−". La lista persiste, entra al scraping cada 15 minutos y aparece
  como mercado propio ("Mis tickers") en la selección de mercados: se
  puede ver sola o combinada, y mientras existan tickers personalizados
  queda siempre seleccionada.
- **Botón ☰ de menú** al lado del engranaje: despliega el mismo menú que
  el click derecho (útil en trackpads y macOS).
- **Filtro por variación diaria** (click derecho → "Variación diaria"):
  escalas de subas y bajas (▲ > 0/+2/+5 %, ▼ < 0/−2/−5 %), combinable con
  los filtros de mercado y de precio.
- El diálogo de noticias/gráfico muestra el **nombre completo de la
  compañía** ("Grupo Financiero Galicia (GGAL)") en vez del ticker pelado.
- **Diagnóstico visible**: si la cinta no tiene datos, ahora distingue
  "sin conexión con el backend" de "sin datos del mercado — <causa>", y el
  tooltip del LED muestra el error concreto del último scraping.

### Corregido
- **Windows**: el primer arranque (instalación de dependencias en consola)
  ahora se lanza solo al terminar la instalación del .msi — antes había
  que ir a buscar la app al menú inicio.
- **macOS**: ídem — el .pkg abre la app al terminar de instalar
  (postinstall), y el primer arranque crea el entorno.
- **Windows**: el banner ya no aparece en la barra de tareas, y las
  ventanas de la app (noticias, configuración) muestran el icono propio en
  vez del de Python (AppUserModelID + icono de aplicación).
- **macOS**: la app no ocupa lugar en el Dock (LSUIElement + política
  Accessory).
- Un doble lanzamiento simultáneo (instalador + inicio automático) ya no
  abre dos banners (mutex en el lanzador de Windows), y un mutex huérfano
  ya no puede dejar la app "no abre" en silencio: se verifica que el
  banner exista de verdad antes de ceder el arranque.
- **Windows**: el lanzador ahora captura la salida del backend en
  `backend\ticker.log` desde el arranque (antes un import roto bajo
  pythonw no dejaba rastro), espera hasta 15 s a que el backend responda
  y, si no levanta, muestra las últimas líneas del log en pantalla.

## v0.3.0 — 2026-07-18

### Agregado
- **Gráfico intradía por cotización**: al hacer click en un símbolo de la
  cinta, el diálogo muestra la evolución del precio de la última sesión
  (velas de 15 minutos) arriba de las noticias — máximo/mínimo, variación
  de la sesión, horario y línea de referencia de apertura. Con el mercado
  cerrado muestra la sesión completa del último día hábil.
- Endpoint `/api/history?symbol=X` en el backend (yfinance on-demand,
  sin dependencias nuevas ni impacto en los instaladores).

## v0.2.0 — 2026-07-18

### Agregado
- **Actualización automática multiplataforma**: la app chequea una vez por
  día (y al arrancar) el último release de GitHub. Si hay versión nueva
  aparece un botón ⬆ en el banner; si el usuario pospone, la actualización
  queda siempre disponible desde ⚙ Configuración ("Actualizar a vX.Y.Z…" /
  "Buscar actualizaciones"). Al aceptar se descarga el instalador del SO
  (.msi/.pkg/.deb) con barra de progreso, se instala reemplazando la
  versión actual (msiexec /passive, installer con permiso de administrador,
  pkexec dpkg -i) y la app se relanza sola.
- Versión visible en el diálogo "Acerca de".
- `APP_VERSION` en `frontend/main.py` como única fuente de versión: los
  tres scripts de empaquetado la leen de ahí.

### Corregido
- **Mercados cerrados**: fuera de horario Yahoo devuelve una vela del día
  en curso con precio NaN que abortaba el scraping completo — la cinta
  quedaba en "esperando datos…" de madrugada (y el banner de Windows en
  negro). Ahora se descartan las velas vacías y se muestran los movimientos
  del último día hábil hasta que los mercados abren.
- La rotación diaria de la base (23:59) dejaba la cinta vacía hasta el
  primer scraping exitoso: la base nueva ahora se siembra con la última
  cotización de cada símbolo.
- Un error al guardar una cotización ya no aborta el resto del lote.
- **Windows**: la reserva de espacio (AppBar) calculaba en píxeles lógicos
  de Qt pero la API del sistema trabaja en físicos — con escalado 125/150 %
  la franja quedaba corta o corrida.
- **Windows**: el lanzador ahora detecta si el backend ya corre (evita
  doble arranque con el inicio automático), registra los errores del
  banner en `frontend.log` y los muestra en pantalla — antes un fallo era
  totalmente silencioso ("abre y no hace nada"). El instalador de
  dependencias verifica que la instalación quede completa.
- **Linux (.deb)**: el backend registra su log en
  `~/.local/share/market-ticker/ticker.log` (antes se descartaba).

## v0.1.0 — 2026-07-17

- Versión inicial: banner de 32 px siempre visible con cinta desplazable,
  91 tickers de 19 mercados, noticias de las últimas 72 h hábiles por
  símbolo, filtros por mercado y rango de precio, 3 idiomas (ES/EN/DE),
  reserva de espacio (strut X11 / AppBar Windows), inicio automático
  opcional e instaladores nativos .msi / .pkg / .deb generados desde Linux.
