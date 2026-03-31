from InteractWithDB.insertintoDB_equity_etf_compositions import EquityEtfCompositionDb, fetch_and_store_all_etfs
from InteractWithDB.insertintoDB_etf_dividends import fetch_and_store_all_dividends
import datetime

def main():
    """Fetch and store all SSGA equity ETF compositions and dividend history into the local SQLite database."""
    db = EquityEtfCompositionDb(db_path="data/etf_compositions.db")

    try:
        exact_time = datetime.datetime.now()
        db.connect_db()
        db.create_tables()

        fetch_and_store_all_etfs(
            db,
            asset_classes=["equity"],  # Options: "alternative", "equity", "fixed-income", "Multi-Asset"
            skip_existing=True         # Set to False to re-fetch existing compositions
        )

        stats = db.get_stats()
        print(f"\nDatabase Statistics:")
        print(f"  Total ETFs tracked: {stats['total_etfs']}")
        print(f"  Total composition records: {stats['total_composition_records']}")
        print(f"  Unique composition dates: {stats['total_unique_dates']}")
        print(f"  Fetch time: {exact_time}")

        # Fetch dividend history for all tracked ETFs via yfinance
        print(f"\nFetching ETF dividend history...")
        tickers = db.get_available_tickers()
        div_stats = fetch_and_store_all_dividends(db.conn, tickers)
        print(f"  Tickers processed: {div_stats['processed']}")
        print(f"  Dividend rows inserted: {div_stats['inserted']}")
        print(f"  Tickers with no dividend data: {div_stats['skipped']}")
        if div_stats['failed']:
            print(f"  Tickers failed: {div_stats['failed']}")

    finally:
        db.close_db()


if __name__ == "__main__":
    main()
