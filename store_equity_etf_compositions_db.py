import sqlite3
import pandas as pd
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from get_available_etfs import GetAvailableEtfs
from get_etf_composition import GetEtfComposition


class EquityEtfCompositionDb:
    """
    SQLite database manager for storing Equity ETF compositions with daily snapshots.

    Table Structure:
    ----------------
    1. equity_etf_info: Stores ETF metadata (relatively static, updates occasionally)
       - ticker (PK), name, domicile, gross_expense_ratio, nav, aum, last_updated

    2. equity_etf_compositions: Stores daily holdings (grows with each trading day)
       - Composite unique key: (etf_ticker, composition_date, component_identifier)
       - Stores: component details, weight, shares, sector, currency
    """

    def __init__(self, db_path = "data/etf_compositions.db"):
        self.db_path = db_path
        self.conn = None

    def connect_db(self):
        """Establish database connection with performance optimizations."""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA synchronous=NORMAL")
        return self.conn

    def close_db(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None

    def create_tables(self):
        """Create database tables if they don't exist."""
        cursor = self.conn.cursor()

        # Table 1: Equity ETF metadata (availble ETFs)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS equity_etf_info (
                ticker TEXT PRIMARY KEY,
                name TEXT,
                domicile TEXT,
                gross_expense_ratio TEXT,
                nav TEXT,
                aum TEXT,
                last_updated TEXT
            )
        """)

        # Table 2: Equity ETF compositions (daily snapshots)
        # Using composite unique constraint to prevent duplicate entries
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS equity_etf_compositions (
                id INTEGER PRIMARY KEY,
                etf_ticker TEXT NOT NULL,
                nav REAL,
                shares_outstanding REAL,
                total_net_assets REAL,
                composition_date TEXT NOT NULL,
                component_name TEXT,
                component_ticker TEXT,
                component_identifier TEXT,
                component_sedol TEXT,
                component_weight REAL,
                component_sector TEXT,
                component_shares REAL,
                component_currency TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                       
                UNIQUE(etf_ticker, composition_date, component_identifier),
                FOREIGN KEY (etf_ticker) REFERENCES equity_etf_info(ticker)
            )
        """)

        # Create indexes for common queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_compositions_etf_date
            ON equity_etf_compositions(etf_ticker, composition_date)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_compositions_date
            ON equity_etf_compositions(composition_date)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_compositions_component
            ON equity_etf_compositions(component_ticker)
        """)

        self.conn.commit()
        print("Database Equity ETF tables created successfully.")

    def update_etf_info(self, etf_df):
        """
        Insert or update ETF metadata from get_available_etfs result using batch upsert.

        :param etf_df: DataFrame from GetAvailableEtfs.parse_etf_table()
        """
        cursor = self.conn.cursor()
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        records = [
            (row['Ticker'], row['Name'], row['Domicile'],
             row['Gross Expense Ratio'], row['NAV'], row['AUM'], now)
            for _, row in etf_df.iterrows()
        ]

        cursor.executemany("""
            INSERT INTO equity_etf_info (ticker, name, domicile, gross_expense_ratio, nav, aum, last_updated)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(ticker) DO UPDATE SET
                name = excluded.name,
                domicile = excluded.domicile,
                gross_expense_ratio = excluded.gross_expense_ratio,
                nav = excluded.nav,
                aum = excluded.aum,
                last_updated = excluded.last_updated
        """, records)

        self.conn.commit()
        print(f"Upserted {len(etf_df)} ETF info records.")

    def insert_composition(self, composition_df):
        """
        Insert ETF composition data using batch insert. Skips duplicates via INSERT OR IGNORE.

        :param composition_df: DataFrame from GetEtfComposition.fetch_etf_composition_to_df()
        :return: Number of records inserted
        """
        if composition_df is None or composition_df.empty:
            return 0

        cursor = self.conn.cursor()
        records = [
            (row.get('etf_ticker'), row.get('nav'), row.get('shares_outstanding'),
             row.get('total_net_assets'), row.get('composition_date'), row.get('component_name'),
             row.get('ticker'), row.get('identifier'), row.get('sedol'),
             row.get('weight'), row.get('sector'), row.get('shares'), row.get('currency'))
            for _, row in composition_df.iterrows()
        ]

        cursor.executemany("""
            INSERT OR IGNORE INTO equity_etf_compositions (
                etf_ticker, nav, shares_outstanding, total_net_assets,
                composition_date, component_name, component_ticker,
                component_identifier, component_sedol, component_weight,
                component_sector, component_shares, component_currency
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, records)

        self.conn.commit()
        return cursor.rowcount

    def get_available_tickers(self):
        """Get list of all ETF tickers from equity_etf_info table 1."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT ticker FROM equity_etf_info ORDER BY ticker")
        return [row['ticker'] for row in cursor.fetchall()]

    def get_composition_dates(self, etf_ticker = None):
        """Get distinct composition dates, optionally filtered by ETF ticker."""
        cursor = self.conn.cursor()
        if etf_ticker:
            cursor.execute("""
                SELECT DISTINCT composition_date FROM equity_etf_compositions
                WHERE etf_ticker = ? ORDER BY composition_date DESC
            """, (etf_ticker,))
        else:
            cursor.execute("""
                SELECT DISTINCT composition_date FROM equity_etf_compositions
                ORDER BY composition_date DESC
            """)
        return [row['composition_date'] for row in cursor.fetchall()]

    def get_composition(self, etf_ticker, composition_date):
        """
        Get composition for a specific ETF on a specific date from table 2.

        :return: DataFrame with composition data
        """
        query = """
            SELECT * FROM equity_etf_compositions
            WHERE etf_ticker = ? AND composition_date = ?
            ORDER BY component_weight DESC
        """
        return pd.read_sql_query(query, self.conn, params=(etf_ticker, composition_date))

    def get_latest_composition(self, etf_ticker):
        """Get the most recent composition for an ETF."""
        dates = self.get_composition_dates(etf_ticker)
        if dates:
            return self.get_composition(etf_ticker, dates[0])
        return pd.DataFrame()

    def composition_exists(self, etf_ticker, composition_date):
        """Check if composition data already exists for a given ETF and date."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) as count FROM equity_etf_compositions
            WHERE etf_ticker = ? AND composition_date = ?
        """, (etf_ticker, composition_date))
        return cursor.fetchone()['count'] > 0

    def get_stats(self):
        """Get database statistics."""
        cursor = self.conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM equity_etf_info")
        etf_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM equity_etf_compositions")
        composition_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(DISTINCT composition_date) FROM equity_etf_compositions")
        date_count = cursor.fetchone()[0]

        return {
            'total_etfs': etf_count,
            'total_composition_records': composition_count,
            'total_unique_dates': date_count
        }

    def purge_old_compositions(self, days_to_keep = 1825):
        """
        Delete composition records older than the retention period and reclaim disk space.

        :param days_to_keep: Number of days of history to retain (default: 365)
        :return: Number of records deleted
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            DELETE FROM equity_etf_compositions
            WHERE composition_date < date('now', ? || ' days')
        """, (f'-{days_to_keep}',))
        deleted = cursor.rowcount
        self.conn.commit()
        if deleted > 0:
            self.conn.execute("VACUUM")
            print(f"Purged {deleted} records older than {days_to_keep} days and reclaimed disk space.")
        else:
            print(f"No records older than {days_to_keep} days found.")
        return deleted


def fetch_and_store_all_etfs(db, asset_classes = None, skip_existing = True):
    """
    Fetch all ETF compositions and store them in the database.

    :param db: EquityEtfCompositionDb instance (already connected)
    :param asset_classes: List of asset classes to fetch. Default: ["equity"]
    :param skip_existing: Skip ETFs that already have today's composition
    """
    if asset_classes is None:
        asset_classes = ["equity"]

    get_etfs = GetAvailableEtfs()

    all_etf_df = pd.DataFrame()

    # Fetch ETF list for each asset class
    for asset_class in asset_classes:
        print(f"\n{'='*60}")
        print(f"Fetching {asset_class} ETFs...")
        print(f"{'='*60}")

        url = get_etfs.asset_class_select(asset_class)
        content = get_etfs.fetch_url_content(url)
        etf_df = get_etfs.parse_etf_table(content)

        if not etf_df.empty:
            all_etf_df = pd.concat([all_etf_df, etf_df], ignore_index=True)
            print(f"Found {len(etf_df)} {asset_class} ETFs")

    if all_etf_df.empty:
        print("No ETFs found!")
        return

    # Remove duplicates based on ticker
    all_etf_df = all_etf_df.drop_duplicates(subset=['Ticker'])
    print(f"\nTotal unique ETFs: {len(all_etf_df)}")

    # Update ETF info table
    db.update_etf_info(all_etf_df)

    # Fetch compositions concurrently, then store to DB from main thread
    success_count = 0
    skip_count = 0
    fail_count = 0
    total = len(all_etf_df)
    tickers = all_etf_df['Ticker'].tolist()
    failed_tickers = []

    def fetch_composition(ticker):
        """Fetch a single ETF composition (thread-safe, no DB access)."""
        comp = GetEtfComposition()
        return ticker, comp.fetch_etf_composition_to_df(ticker)

    print(f"\nFetching compositions concurrently with up to 500 workers...")

    with ThreadPoolExecutor(max_workers = 500) as executor:
        future_to_ticker = {
            executor.submit(fetch_composition, ticker): ticker
            for ticker in tickers
        }

        for idx, future in enumerate(as_completed(future_to_ticker), 1):
            ticker = future_to_ticker[future]
            print(f"\n[{idx}/{total}] Processing {ticker}...")

            try:
                ticker, composition_df = future.result()

                if composition_df is not None and not composition_df.empty:
                    composition_date = composition_df['composition_date'].iloc[0]

                    # Check if we should skip
                    if skip_existing and db.composition_exists(ticker, composition_date):
                        print(f"  Skipping {ticker} - composition for {composition_date} already exists")
                        skip_count += 1
                        continue

                    # Insert composition (main thread - SQLite safe)
                    inserted = db.insert_composition(composition_df)
                    print(f"  Stored {inserted} holdings for {ticker} (date: {composition_date})")
                    success_count += 1
                else:
                    print(f"  No composition data available for {ticker} (returned None — likely NAV date mismatch or fetch error)")
                    failed_tickers.append(ticker)
                    fail_count += 1

            except Exception as e:
                print(f"  Error processing {ticker}: {e}")
                failed_tickers.append(ticker)
                fail_count += 1

    print(f"\n{'='*60}")
    print("Summary:")
    print(f"  Successfully stored: {success_count}")
    print(f"  Skipped (existing): {skip_count}")
    print(f"  Failed: {fail_count}")
    if failed_tickers:
        print(f"  Failed tickers: {', '.join(failed_tickers)}")
    print(f"{'='*60}")
