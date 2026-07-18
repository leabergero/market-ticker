import yfinance as yf
import requests
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class TickerScraper:
    """Scraping de precios con yfinance y noticias financieras."""

    # Tickers principales STOXX600 + DAX + NYSE/NASDAQ
    # Índice principal + papeles representativos de cada mercado.
    # Sufijos yfinance: .DE Xetra, .PA París, .MC Madrid, .L Londres, .MI Milán,
    # .SW Zúrich, .TO Toronto, .T Tokio, .HK Hong Kong, .SS Shanghái, .KS Seúl,
    # .NS India, .AX Australia, .SA São Paulo, .BA Buenos Aires.
    TICKERS = {
        "STOXX": ["^STOXX50E", "ASML.AS", "MC.PA", "SAP.DE", "NESN.SW"],
        "DAX": ["^GDAXI", "SAP.DE", "SIE.DE", "ALV.DE", "MUV2.DE"],
        "CAC40": ["^FCHI", "MC.PA", "OR.PA", "TTE.PA", "AIR.PA"],
        "IBEX35": ["^IBEX", "SAN.MC", "ITX.MC", "IBE.MC", "TEF.MC"],
        "FTSE100": ["^FTSE", "SHEL.L", "AZN.L", "HSBA.L", "ULVR.L"],
        "FTSEMIB": ["FTSEMIB.MI", "ENI.MI", "ISP.MI", "UCG.MI", "ENEL.MI"],
        "SMI": ["^SSMI", "NESN.SW", "NOVN.SW", "ROG.SW", "UBSG.SW"],
        "NYSE": ["^NYA", "JPM", "XOM", "JNJ", "V"],
        "NASDAQ": ["^IXIC", "AAPL", "MSFT", "GOOGL", "NVDA", "AMZN"],
        "SP500": ["^GSPC", "BRK-B", "LLY", "AVGO", "TSLA"],
        "TSX": ["^GSPTSE", "RY.TO", "TD.TO", "SHOP.TO", "ENB.TO"],
        "NIKKEI": ["^N225", "7203.T", "6758.T", "9984.T", "8306.T"],
        "HANGSENG": ["^HSI", "0700.HK", "9988.HK", "0005.HK", "1299.HK"],
        "SSE": ["000001.SS", "600519.SS", "601398.SS", "601857.SS"],
        "KOSPI": ["^KS11", "005930.KS", "000660.KS", "005380.KS"],
        "SENSEX": ["^BSESN", "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS"],
        "ASX": ["^AXJO", "BHP.AX", "CBA.AX", "CSL.AX"],
        "BOVESPA": ["^BVSP", "VALE3.SA", "PETR4.SA", "ITUB4.SA"],
        "MERVAL": ["^MERV", "GGAL.BA", "YPFD.BA", "PAMP.BA", "CEPU.BA", "ALUA.BA"],
    }

    @staticmethod
    def fetch_prices(symbols, market):
        """Obtiene precios actuales de yfinance para símbolos dados."""
        results = []
        for symbol in symbols:
            try:
                ticker = yf.Ticker(symbol)
                # 5 días para tener el cierre anterior (con 1d el cambio da 0)
                data = ticker.history(period="5d")

                # Con el mercado cerrado Yahoo incluye una vela del día en
                # curso con Close NaN: descartarla y usar los últimos cierres
                # reales, así fuera de horario se muestra el movimiento del
                # día anterior. (NaN además se vuelve NULL en SQLite y viola
                # el NOT NULL de price.)
                closes = data['Close'].dropna() if not data.empty else []
                if len(closes) > 0:
                    latest_close = float(closes.iloc[-1])
                    prev_close = float(closes.iloc[-2]) if len(closes) >= 2 else latest_close
                    change = latest_close - prev_close
                    change_pct = (change / prev_close * 100) if prev_close != 0 else 0

                    results.append({
                        "symbol": symbol,
                        "price": round(latest_close, 2),
                        "change": round(change, 2),
                        "change_percent": round(change_pct, 2),
                        "market": market
                    })
            except Exception as e:
                logger.warning(f"Error fetching {symbol}: {e}")

        return results

    @staticmethod
    def fetch_all_markets():
        """Obtiene precios de todos los mercados configurados."""
        all_prices = []
        for market, symbols in TickerScraper.TICKERS.items():
            prices = TickerScraper.fetch_prices(symbols, market)
            all_prices.extend(prices)
        return all_prices

    @staticmethod
    def search(query, limit=10):
        """Busca símbolos en Yahoo Finance (para los tickers personalizados
        del usuario): [{symbol, name, exchange}]."""
        try:
            quotes = yf.Search(query, max_results=limit).quotes or []
        except Exception as e:
            logger.warning(f"Search error '{query}': {e}")
            return []
        results = []
        for q in quotes:
            sym = q.get("symbol")
            if sym:
                results.append({
                    "symbol": sym,
                    "name": q.get("shortname") or q.get("longname") or sym,
                    "exchange": q.get("exchDisp") or q.get("exchange") or "",
                })
        return results

    @staticmethod
    def fetch_history(symbol, interval="15m"):
        """Curva intradía de la última sesión (velas de 15 min).

        Con el mercado cerrado, yfinance con period=1d ya devuelve la sesión
        del último día hábil completa — el fallback viene gratis. dropna por
        el mismo gotcha de velas NaN fuera de horario que fetch_prices.
        """
        try:
            data = yf.Ticker(symbol).history(period="1d", interval=interval)
            closes = data["Close"].dropna() if not data.empty else []
            if len(closes) == 0:
                return []
            return [{"t": ts.isoformat(), "p": round(float(v), 2)}
                    for ts, v in closes.items()]
        except Exception as e:
            logger.warning(f"Error fetching history for {symbol}: {e}")
            return []

    @staticmethod
    def news_cutoff(business_hours=72):
        """Momento límite para noticias: N horas hábiles hacia atrás.

        Los sábados y domingos no descuentan horas, así el lunes se ven
        las noticias desde el miércoles anterior.
        """
        remaining = timedelta(hours=business_hours)
        t = datetime.now()
        while remaining > timedelta(0):
            step = min(remaining, timedelta(hours=1))
            t -= step
            if t.weekday() < 5:  # lunes a viernes descuentan
                remaining -= step
        return t

    @staticmethod
    def fetch_news(symbol, business_hours=72):
        """Noticias del símbolo vía yfinance, últimas N horas hábiles."""
        cutoff_ts = TickerScraper.news_cutoff(business_hours).timestamp()
        news = []
        try:
            items = yf.Ticker(symbol).news or []
            for item in items:
                # yfinance moderno anida en "content"; el viejo era plano
                content = item.get("content", item)
                published = item.get("providerPublishTime")
                if published is None:
                    pub = content.get("pubDate") or content.get("displayTime")
                    try:
                        published = datetime.fromisoformat(
                            pub.replace("Z", "+00:00")).timestamp() if pub else 0
                    except ValueError:
                        published = 0
                if published < cutoff_ts:
                    continue
                url = ((content.get("clickThroughUrl") or {}).get("url")
                       or (content.get("canonicalUrl") or {}).get("url")
                       or item.get("link", ""))
                source = ((content.get("provider") or {}).get("displayName")
                          or item.get("publisher", ""))
                title = content.get("title", "")
                if title:
                    news.append({"title": title, "url": url, "source": source})
        except Exception as e:
            logger.warning(f"Error fetching news for {symbol}: {e}")
        return news
