from InteractWithDB.insertintoDB_equity_etf_compositions import EquityEtfCompositionDb, fetch_and_store_all_etfs
from run_arb_monitor import run_arb_monitor


def main():
    """Main function to run the ETF composition storage."""
    db = EquityEtfCompositionDb(db_path = "data/etf_compositions.db")

    try:
        db.connect_db()
        db.create_tables()

        # Fetch and store all equity ETFs (you can add more asset classes)
        fetch_and_store_all_etfs(
            db,
            asset_classes = ["equity"],  # Options: "alternative", "equity", "fixed-income", "Multi-Asset"
            skip_existing = True  # Set to False to re-fetch existing compositions
        )

        # Print database stats
        stats = db.get_stats()
        print(f"\nDatabase Statistics:")
        print(f"  Total ETFs tracked: {stats['total_etfs']}")
        print(f"  Total composition records: {stats['total_composition_records']}")
        print(f"  Unique composition dates: {stats['total_unique_dates']}")

    finally:
        db.close_db()

    # ── Fair NAV & Arbitrage Monitor ──────────────────────────────────────
    # Runs after the composition fetch. Opens its own DB connection.
    # Add more tickers to monitor multiple ETFs in one run.

    nav_cal = input("Start calculating the ETF NAV? (y/n): ")

    if nav_cal == "y":

        etf_cal = input("Input the ETF ticker: ")
        run_arb_monitor(
            etf_tickers   = [etf_cal],
            db_path       = "data/etf_compositions.db",
            store_results = True
        )
    else:
        pass

if __name__ == "__main__":
    main()
