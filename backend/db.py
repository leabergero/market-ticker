import sqlite3
import os
from datetime import datetime
from pathlib import Path

class TickerDB:
    """Gestiona SQLite local con rotación diaria de backups."""

    def __init__(self, db_dir=None):
        # TICKER_DATA_DIR permite datos por-usuario cuando la app está
        # instalada en una ruta de solo-lectura (/opt en el .deb).
        # Sin la variable: ruta absoluta junto a este archivo (evita crear
        # BDs distintas según desde dónde se lance el proceso).
        if db_dir is None:
            db_dir = os.environ.get("TICKER_DATA_DIR") or Path(__file__).resolve().parent / "data"
        self.db_dir = Path(db_dir)
        self.db_dir.mkdir(exist_ok=True)
        self.db_path = self.db_dir / "ticker.db"
        self.backup_dir = self.db_dir / "backups"
        self.backup_dir.mkdir(exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Inicializa tabla si no existe."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tickers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                price REAL NOT NULL,
                change REAL,
                change_percent REAL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                market TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS news (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                title TEXT,
                url TEXT,
                source TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS custom_tickers (
                symbol TEXT PRIMARY KEY,
                name TEXT
            )
        """)
        conn.commit()
        conn.close()

    def insert_ticker(self, symbol, price, change, change_percent, market):
        """Inserta datos de cotización en la BD."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO tickers (symbol, price, change, change_percent, market)
            VALUES (?, ?, ?, ?, ?)
        """, (symbol, price, change, change_percent, market))
        conn.commit()
        conn.close()

    def insert_news(self, symbol, title, url, source):
        """Inserta noticia en la BD."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO news (symbol, title, url, source)
            VALUES (?, ?, ?, ?)
        """, (symbol, title, url, source))
        conn.commit()
        conn.close()

    def get_tickers(self, markets=None, price_min=None, price_max=None,
                    change_min=None, change_max=None, limit=50):
        """Obtiene la última cotización de cada símbolo.

        markets: lista de mercados a incluir (None o vacía = todos).
        change_min/change_max: filtro por variación diaria en % (cualquiera
        puede ser None para dejar ese extremo abierto).
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Subconsulta: fila más reciente por símbolo (evita duplicados
        # históricos acumulados por el scraping cada 15 min).
        query = """
            SELECT symbol, price, change, change_percent, market, MAX(timestamp) AS timestamp
            FROM tickers
            GROUP BY symbol
        """
        conditions = []
        params = []

        if markets:
            placeholders = ",".join("?" * len(markets))
            conditions.append(f"market IN ({placeholders})")
            params.extend(markets)

        if price_min is not None or price_max is not None:
            conditions.append("price BETWEEN ? AND ?")
            params.extend([price_min or 0, price_max or 1000000])

        if change_min is not None:
            conditions.append("change_percent >= ?")
            params.append(change_min)
        if change_max is not None:
            conditions.append("change_percent <= ?")
            params.append(change_max)

        if conditions:
            query = f"SELECT * FROM ({query}) WHERE {' AND '.join(conditions)}"
        else:
            query = f"SELECT * FROM ({query})"

        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_custom_tickers(self):
        """Lista de tickers personalizados del usuario: [{symbol, name}]."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT symbol, name FROM custom_tickers ORDER BY symbol").fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def add_custom_ticker(self, symbol, name=""):
        """Agrega (o actualiza el nombre de) un ticker personalizado."""
        conn = sqlite3.connect(self.db_path)
        conn.execute("INSERT OR REPLACE INTO custom_tickers (symbol, name) VALUES (?, ?)",
                     (symbol, name))
        conn.commit()
        conn.close()

    def remove_custom_ticker(self, symbol):
        """Quita un ticker personalizado y sus cotizaciones (si no las
        borrara, seguiría en la cinta hasta la rotación diaria)."""
        conn = sqlite3.connect(self.db_path)
        conn.execute("DELETE FROM custom_tickers WHERE symbol = ?", (symbol,))
        conn.execute("DELETE FROM tickers WHERE symbol = ? AND market = 'CUSTOM'",
                     (symbol,))
        conn.commit()
        conn.close()

    def get_news(self, symbol=None, limit=20):
        """Obtiene noticias, opcionalmente filtradas por símbolo."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        if symbol:
            cursor.execute("""
                SELECT title, url, source, timestamp FROM news
                WHERE symbol = ?
                ORDER BY timestamp DESC LIMIT ?
            """, (symbol, limit))
        else:
            cursor.execute("""
                SELECT symbol, title, url, source, timestamp FROM news
                ORDER BY timestamp DESC LIMIT ?
            """, (limit,))

        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def rotate_backup(self):
        """Rota BD actual al cierre del día con timestamp.

        La BD nueva se siembra con la última cotización de cada símbolo:
        sin esto la cinta quedaba vacía ("esperando datos…") desde las
        23:59 hasta el primer scrape exitoso (horas, con mercados cerrados).
        """
        today = datetime.now().strftime("%Y-%m-%d")
        backup_path = self.backup_dir / f"ticker-{today}.db"

        if self.db_path.exists() and not backup_path.exists():
            self.db_path.rename(backup_path)
            self._init_db()
            try:
                src = sqlite3.connect(backup_path)
                rows = src.execute("""
                    SELECT symbol, price, change, change_percent, market, MAX(timestamp)
                    FROM tickers GROUP BY symbol
                """).fetchall()
                try:
                    custom = src.execute(
                        "SELECT symbol, name FROM custom_tickers").fetchall()
                except sqlite3.Error:
                    custom = []  # backup de una versión sin la tabla
                src.close()
                conn = sqlite3.connect(self.db_path)
                if rows:
                    conn.executemany("""
                        INSERT INTO tickers (symbol, price, change, change_percent, market, timestamp)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, rows)
                if custom:
                    # la lista personalizada debe sobrevivir la rotación
                    conn.executemany("""
                        INSERT OR REPLACE INTO custom_tickers (symbol, name)
                        VALUES (?, ?)
                    """, custom)
                conn.commit()
                conn.close()
            except sqlite3.Error:
                pass  # sin semilla la cinta espera al próximo scrape

    def get_backups(self):
        """Retorna lista de archivos de backup."""
        if not self.backup_dir.exists():
            return []
        return sorted([f.name for f in self.backup_dir.glob("ticker-*.db")])

    def delete_backups(self, days_keep=7):
        """Borra backups más antiguos que N días."""
        from datetime import timedelta
        cutoff = datetime.now() - timedelta(days=days_keep)
        deleted = []

        for backup_file in self.backup_dir.glob("ticker-*.db"):
            file_date_str = backup_file.stem.replace("ticker-", "")
            try:
                file_date = datetime.strptime(file_date_str, "%Y-%m-%d")
                if file_date < cutoff:
                    backup_file.unlink()
                    deleted.append(backup_file.name)
            except ValueError:
                pass

        return deleted

    def clear_all_backups(self):
        """Borra TODOS los archivos de backup (manualmente)."""
        deleted = []
        for backup_file in self.backup_dir.glob("ticker-*.db"):
            backup_file.unlink()
            deleted.append(backup_file.name)
        return deleted
