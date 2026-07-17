from flask import Flask, jsonify, request
from apscheduler.schedulers.background import BackgroundScheduler
from db import TickerDB
from scraper import TickerScraper
from datetime import datetime
import logging
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
db = TickerDB()
scheduler = BackgroundScheduler()

# Estado del último scraping: el frontend lo usa para el LED verde/rojo.
last_scrape = {"ok": False, "time": None, "count": 0}

def scheduled_scrape():
    """Ejecuta scraping cada 15 minutos y registra si obtuvo datos en vivo."""
    try:
        prices = TickerScraper.fetch_all_markets()
        for price_data in prices:
            db.insert_ticker(**price_data)
        last_scrape.update(ok=len(prices) > 0,
                           time=datetime.now().isoformat(),
                           count=len(prices))
        logger.info(f"Scraped {len(prices)} tickers at {datetime.now()}")
    except Exception as e:
        last_scrape.update(ok=False, time=datetime.now().isoformat(), count=0)
        logger.error(f"Scraping error: {e}")

def daily_rotation():
    """Rota la BD al cierre del día (ticker.db → backups/ticker-YYYY-MM-DD.db)."""
    try:
        db.rotate_backup()
        logger.info("Daily DB rotation done")
    except Exception as e:
        logger.error(f"Rotation error: {e}")

@app.route('/api/tickers', methods=['GET'])
def get_tickers():
    """Obtiene lista de tickers. `market` acepta varios separados por coma."""
    market = request.args.get('market')
    markets = [m.strip() for m in market.split(",") if m.strip()] if market else None
    price_min = request.args.get('price_min', type=float)
    price_max = request.args.get('price_max', type=float)
    limit = request.args.get('limit', 50, type=int)

    tickers = db.get_tickers(markets=markets, price_min=price_min, price_max=price_max, limit=limit)
    return jsonify({"tickers": tickers})

@app.route('/api/news', methods=['GET'])
def get_news():
    """Noticias de las últimas 72 h hábiles: intenta yfinance en vivo y
    cae a lo guardado en la BD si no hay conexión."""
    symbol = request.args.get('symbol')
    limit = request.args.get('limit', 20, type=int)

    if symbol:
        live = TickerScraper.fetch_news(symbol)
        if live:
            for n in live:
                db.insert_news(symbol, n["title"], n["url"], n["source"])
            return jsonify({"news": live[:limit], "live": True})

    news = db.get_news(symbol=symbol, limit=limit)
    return jsonify({"news": news, "live": False})

@app.route('/api/backups', methods=['GET'])
def get_backups():
    """Lista todos los archivos de backup."""
    backups = db.get_backups()
    return jsonify({"backups": backups})

@app.route('/api/backups/delete-old', methods=['POST'])
def delete_old_backups():
    """Borra backups más antiguos que N días (default: 7)."""
    days_keep = request.json.get('days_keep', 7) if request.json else 7
    deleted = db.delete_backups(days_keep=days_keep)
    return jsonify({"deleted": deleted, "count": len(deleted)})

@app.route('/api/backups/delete-all', methods=['POST'])
def delete_all_backups():
    """Borra TODOS los archivos de backup."""
    deleted = db.clear_all_backups()
    return jsonify({"deleted": deleted, "count": len(deleted)})

@app.route('/api/health', methods=['GET'])
def health():
    """Health check con estado del último scraping (para el LED del banner)."""
    return jsonify({
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "last_scrape": last_scrape,
    })

def start_scheduler():
    """Agenda scraping cada 15 min, uno inmediato al arrancar y rotación diaria a las 23:59."""
    if not scheduler.running:
        scheduler.add_job(scheduled_scrape, 'interval', minutes=15)
        scheduler.add_job(scheduled_scrape, 'date')  # primer scrape al arrancar
        scheduler.add_job(daily_rotation, 'cron', hour=23, minute=59)
        scheduler.start()
        logger.info("Scheduler started - scraping every 15 minutes, rotation at 23:59")

if __name__ == '__main__':
    start_scheduler()
    app.run(host='127.0.0.1', port=5003, debug=False)
