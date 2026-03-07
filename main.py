from get_available_etfs import GetAvailableEtfs
from get_etf_composition import GetEtfComposition
from store_equity_etf_compositions_db import EquityEtfCompositionDb, fetch_and_store_all_etfs

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


if __name__ == "__main__":
    main()
