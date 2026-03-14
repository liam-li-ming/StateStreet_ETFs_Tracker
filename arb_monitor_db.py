import sqlite3
import pandas as pd
from datetime import datetime, timedelta


class ArbMonitorDb:
    """
    SQLite database manager for the etf_nav_estimates table.

    Stores the output of FairNavCalculator.calculate_fair_nav() — fair NAV
    estimates, coverage metrics, and arbitrage signals — for historical
    tracking and analysis.

    Follows the same connect / create / insert / query pattern as
    EquityEtfCompositionDb in store_equity_etf_compositions_db.py.

    Table structure:
        etf_nav_estimates: one row per ETF per calculator run.
        No UNIQUE constraint — multiple intraday runs are intentionally
        kept as separate rows so the full time-series is preserved.
    """

    def __init__(self, db_path="data/etf_compositions.db"):
        """
        :param db_path: Path to the shared SQLite database file.
                        Defaults to the same DB used by EquityEtfCompositionDb.
        """
        self.db_path = db_path
        self.conn    = None

    def connect_db(self):
        """Establish database connection with performance optimisations."""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA synchronous=NORMAL")
        return self.conn

    def close_db(self):
        """Close the database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None

    def create_table(self):
        """
        Create the etf_nav_estimates table and its indexes if they do not
        already exist.
        """
        cursor = self.conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS etf_nav_estimates (
                id                      INTEGER PRIMARY KEY,

                -- Identity
                etf_ticker              TEXT NOT NULL,
                composition_date        TEXT NOT NULL,
                calculation_timestamp   TEXT NOT NULL,

                -- Fund-level inputs from DB (T-1)
                official_nav            REAL,
                shares_outstanding      REAL,

                -- Calculated NAV
                fair_nav_primary        REAL,
                fair_nav_weight_based   REAL,

                -- ETF market price
                etf_market_price        REAL,
                premium_discount_pct    REAL,

                -- Coverage metrics (stored as 0-100 percentage values)
                covered_weight_pct      REAL,
                uncovered_weight_pct    REAL,
                total_components        INTEGER,
                priced_components       INTEGER,
                unpriced_components     INTEGER,
                skipped_components      INTEGER,
                quality_flag            TEXT,
                market_open             INTEGER,

                -- Arbitrage: Scenario A (creation — sell ETF, buy basket)
                arb_a_etf_bid_net       REAL,
                arb_a_basket_ask_net    REAL,
                arb_a_profit_pct        REAL,
                arb_a_signal            TEXT,

                -- Arbitrage: Scenario B (redemption — buy ETF, sell basket)
                arb_b_etf_ask_net       REAL,
                arb_b_basket_bid_net    REAL,
                arb_b_profit_pct        REAL,
                arb_b_signal            TEXT,

                -- Warnings
                unpriced_tickers_list   TEXT,
                currency_warning        TEXT,

                created_at              TEXT DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (etf_ticker) REFERENCES equity_etf_info(ticker)
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_nav_estimates_ticker_ts
            ON etf_nav_estimates(etf_ticker, calculation_timestamp)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_nav_estimates_ts
            ON etf_nav_estimates(calculation_timestamp)
        """)

        # Migration: add columns introduced after the table was first created.
        # ALTER TABLE ADD COLUMN is a no-op-safe pattern — we catch the
        # OperationalError SQLite raises when the column already exists.
        migrations = [
            "ALTER TABLE etf_nav_estimates ADD COLUMN unpriced_tickers_list TEXT",
        ]
        for sql in migrations:
            try:
                cursor.execute(sql)
            except Exception:
                pass  # column already exists

        self.conn.commit()
        print("etf_nav_estimates table ready.")

    def insert_estimate(self, result_dict):
        """
        Insert one fair NAV estimate from the result dict produced by
        FairNavCalculator.calculate_fair_nav().

        :param result_dict: Dict returned by FairNavCalculator._build_result_dict().
        :return: Number of rows inserted (1), or 0 if result_dict is None/empty.
        """
        if not result_dict:
            return 0

        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO etf_nav_estimates (
                etf_ticker, composition_date, calculation_timestamp,
                official_nav, shares_outstanding,
                fair_nav_primary, fair_nav_weight_based,
                etf_market_price, premium_discount_pct,
                covered_weight_pct, uncovered_weight_pct,
                total_components, priced_components,
                unpriced_components, skipped_components,
                quality_flag, market_open,
                arb_a_etf_bid_net, arb_a_basket_ask_net,
                arb_a_profit_pct, arb_a_signal,
                arb_b_etf_ask_net, arb_b_basket_bid_net,
                arb_b_profit_pct, arb_b_signal,
                unpriced_tickers_list, currency_warning
            ) VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
            )
        """, (
            result_dict.get('etf_ticker'),
            result_dict.get('composition_date'),
            result_dict.get('calculation_timestamp'),
            result_dict.get('official_nav'),
            result_dict.get('shares_outstanding'),
            result_dict.get('fair_nav_primary'),
            result_dict.get('fair_nav_weight_based'),
            result_dict.get('etf_market_price'),
            result_dict.get('premium_discount_pct'),
            result_dict.get('covered_weight_pct'),
            result_dict.get('uncovered_weight_pct'),
            result_dict.get('total_components'),
            result_dict.get('priced_components'),
            result_dict.get('unpriced_components'),
            result_dict.get('skipped_components'),
            result_dict.get('quality_flag'),
            result_dict.get('market_open'),
            result_dict.get('arb_a_etf_bid_net'),
            result_dict.get('arb_a_basket_ask_net'),
            result_dict.get('arb_a_profit_pct'),
            result_dict.get('arb_a_signal'),
            result_dict.get('arb_b_etf_ask_net'),
            result_dict.get('arb_b_basket_bid_net'),
            result_dict.get('arb_b_profit_pct'),
            result_dict.get('arb_b_signal'),
            ', '.join(result_dict.get('unpriced_tickers') or []),
            result_dict.get('currency_warning'),
        ))

        self.conn.commit()
        return cursor.rowcount

    def get_latest_estimates(self, etf_ticker=None, limit=10):
        """
        Retrieve the most recent fair NAV estimates, optionally filtered by ETF.

        :param etf_ticker: Optional ETF ticker to filter by.
        :param limit: Maximum number of rows to return.
        :return: DataFrame sorted by calculation_timestamp DESC.
        """
        if etf_ticker:
            query = """
                SELECT * FROM etf_nav_estimates
                WHERE etf_ticker = ?
                ORDER BY calculation_timestamp DESC
                LIMIT ?
            """
            return pd.read_sql_query(query, self.conn, params=(etf_ticker, limit))
        else:
            query = """
                SELECT * FROM etf_nav_estimates
                ORDER BY calculation_timestamp DESC
                LIMIT ?
            """
            return pd.read_sql_query(query, self.conn, params=(limit,))

    def get_estimate_history(self, etf_ticker, days=30):
        """
        Retrieve a rolling history of fair NAV estimates for a given ETF.

        :param etf_ticker: ETF ticker to query.
        :param days: Lookback window in calendar days.
        :return: DataFrame sorted by calculation_timestamp DESC.
        """
        cutoff = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        query = """
            SELECT * FROM etf_nav_estimates
            WHERE etf_ticker = ?
              AND calculation_timestamp >= ?
            ORDER BY calculation_timestamp DESC
        """
        return pd.read_sql_query(query, self.conn, params=(etf_ticker, cutoff))

    def get_stats(self):
        """
        Return summary statistics for the etf_nav_estimates table.

        :return: Dict with total_estimates, unique_etfs, opportunity_count.
        """
        cursor = self.conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM etf_nav_estimates")
        total = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(DISTINCT etf_ticker) FROM etf_nav_estimates")
        unique_etfs = cursor.fetchone()[0]

        cursor.execute("""
            SELECT COUNT(*) FROM etf_nav_estimates
            WHERE arb_a_signal = 'OPPORTUNITY' OR arb_b_signal = 'OPPORTUNITY'
        """)
        opportunities = cursor.fetchone()[0]

        return {
            'total_estimates':   total,
            'unique_etfs':       unique_etfs,
            'opportunity_count': opportunities,
        }
