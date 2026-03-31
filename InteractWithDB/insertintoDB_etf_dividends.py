import sqlite3
from concurrent.futures import ThreadPoolExecutor, as_completed
from .retrievefromWEB_etf_dividends import GetEtfDividends


def create_dividends_table(conn: sqlite3.Connection):
    """Create etf_dividends table and indexes if they don't exist."""
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS etf_dividends (
            id INTEGER PRIMARY KEY,
            etf_ticker TEXT NOT NULL,
            ex_date TEXT NOT NULL,
            dividend_amount REAL NOT NULL,
            currency TEXT DEFAULT 'USD',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(etf_ticker, ex_date),
            FOREIGN KEY (etf_ticker) REFERENCES equity_etf_info(ticker)
        )
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_dividends_etf
        ON etf_dividends(etf_ticker)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_dividends_date
        ON etf_dividends(ex_date)
    """)

    conn.commit()


def insert_dividends(conn: sqlite3.Connection, df) -> int:
    """
    Batch-insert dividend rows, skipping duplicates via INSERT OR IGNORE.

    :param conn: Active SQLite connection
    :param df: DataFrame with columns: etf_ticker, ex_date, dividend_amount
    :return: Number of rows inserted
    """
    if df is None or df.empty:
        return 0

    cursor = conn.cursor()
    records = list(zip(df["etf_ticker"], df["ex_date"], df["dividend_amount"]))

    cursor.executemany("""
        INSERT OR IGNORE INTO etf_dividends (etf_ticker, ex_date, dividend_amount)
        VALUES (?, ?, ?)
    """, records)

    conn.commit()
    return cursor.rowcount


def get_dividends(conn: sqlite3.Connection, etf_ticker: str):
    """Return all dividend rows for a given ETF ticker, newest first."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT etf_ticker, ex_date, dividend_amount, currency
        FROM etf_dividends
        WHERE etf_ticker = ?
        ORDER BY ex_date DESC
    """, (etf_ticker,))
    return cursor.fetchall()


def fetch_and_store_all_dividends(conn: sqlite3.Connection, tickers: list[str], max_workers: int = 10) -> dict:
    """
    Fetch dividend history for all tickers concurrently and insert into DB.

    :param conn: Active SQLite connection (with etf_dividends table created)
    :param tickers: List of ETF ticker strings
    :param max_workers: Thread pool size (yfinance is I/O-bound; 20 is safe)
    :return: Stats dict with counts of processed, inserted, skipped, failed tickers
    """
    fetcher = GetEtfDividends()
    stats = {"processed": 0, "inserted": 0, "skipped": 0, "failed": 0}

    def _fetch(ticker):
        return ticker, fetcher.fetch_dividends(ticker)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_fetch, t): t for t in tickers}
        for future in as_completed(futures):
            ticker, df = future.result()
            stats["processed"] += 1
            if df is None:
                stats["skipped"] += 1
                continue
            try:
                n = insert_dividends(conn, df)
                stats["inserted"] += n
            except Exception as e:
                print(f"[dividends] DB insert error for {ticker}: {e}")
                stats["failed"] += 1

    return stats
