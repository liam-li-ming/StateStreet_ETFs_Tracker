from store_equity_etf_compositions_db import EquityEtfCompositionDb
from detect_etf_arbitrage import DetectEtfArbitrage


def main():
    db = EquityEtfCompositionDb(db_path="data/etf_compositions.db")

    try:
        db.connect_db()
        detector = DetectEtfArbitrage(db)

        # Analyze SPY
        print("Analyzing SPY for arbitrage opportunities...\n")
        result = detector.analyze_etf("SPY")

        if result is None:
            print("No data available for SPY. Make sure you have run main.py first.")
            return

        # Print detailed result
        print(detector.format_result(result))

        # Print key fields individually for inspection
        print("\n--- Key Metrics ---")
        print(f"  Signal:              {result['signal']}")
        print(f"  Arbitrage Action:    {result['arbitrage_action']}")
        print(f"  Market Price:        ${result['market_price']:.4f}")
        print(f"  Calculated NAV:      ${result['calculated_nav']:.4f}")
        print(f"  Premium/Discount:    {result['premium_discount_pct']:+.4f}%")
        print(f"  Est. Profit/Share:   ${result['estimated_profit_per_share']:.4f}")
        print(f"  Stock Value:         ${result['stock_value']:,.2f}")
        print(f"  Cash Value:          ${result['cash_value']:,.2f}")
        print(f"  Coverage:            {result['coverage_pct']}%")
        print(f"  Components Priced:   {result['priced_components']}/{result['total_components']}")
        print(f"    Stocks:            {result['stock_components']}")
        print(f"    Cash:              {result['cash_components']}")

        if result['skipped_components']:
            print(f"\n  Skipped ({len(result['skipped_components'])}):")
            for s in result['skipped_components']:
                print(f"    - {s['name'][:40]}  ({s['reason']})")

    finally:
        db.close_db()


if __name__ == "__main__":
    main()
