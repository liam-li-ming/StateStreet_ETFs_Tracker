import sqlite3
from fair_nav_calculator import FairNavCalculator
from arb_monitor_db import ArbMonitorDb


def run_arb_monitor(etf_tickers, db_path="data/etf_compositions.db", store_results=True):
    """
    Orchestrate a full fair NAV / arbitrage monitor run for a list of ETF tickers.

    For each ticker:
        1. Calculate fair NAV using FairNavCalculator (reads T-1 holdings from DB,
           fetches live prices from yfinance).
        2. Optionally store the result in etf_nav_estimates.
        3. Print a formatted report to the terminal.

    :param etf_tickers: List of ETF ticker strings (e.g. ['SPY']).
    :param db_path: Path to the shared SQLite database file.
    :param store_results: If True, persist each result to etf_nav_estimates table.
    """
    print(f"\n{'='*64}")
    print(f"  ETF Fair NAV & Arbitrage Monitor")
    print(f"  ETFs: {', '.join(etf_tickers)}")
    print(f"{'='*64}")

    # Open DB connections
    arb_db = ArbMonitorDb(db_path=db_path)
    arb_db.connect_db()
    arb_db.create_table()

    # Separate sqlite3 connection for FairNavCalculator reads
    calc_conn = sqlite3.connect(db_path)
    calc_conn.row_factory = sqlite3.Row

    success_count = 0
    fail_count    = 0

    try:
        for ticker in etf_tickers:
            calc   = FairNavCalculator(calc_conn)
            result = calc.calculate_fair_nav(ticker)

            if result is None:
                print(f"\n  [{ticker}] Skipped — no composition data in DB.")
                fail_count += 1
                continue

            if store_results:
                inserted = arb_db.insert_estimate(result)
                if inserted:
                    print(f"  Saved to etf_nav_estimates.")

            print_arb_report(result)
            success_count += 1

    finally:
        calc_conn.close()
        arb_db.close_db()

    # Summary
    print(f"\n{'='*64}")
    print(f"  Run complete — Success: {success_count}   Failed/Skipped: {fail_count}")
    print(f"{'='*64}\n")


def print_arb_report(result):
    """
    Print a clean, sectioned terminal report for one ETF's fair NAV result.

    Sections:
        Header     — ticker, composition date, market status, timestamp
        NAV        — official, fair (primary), fair (weight-based), market price,
                     premium/discount
        Coverage   — component counts, weight coverage %, quality flag
        Arb        — Scenario A and B profit/loss and signals
        Warnings   — currency warning (if any), AP disclaimer (always)

    :param result: Dict returned by FairNavCalculator.calculate_fair_nav().
    """
    if result is None:
        print("  No result to display.")
        return

    market_status = (
        "OPEN  (prices 15-min delayed)"
        if result.get('market_open')
        else "CLOSED (prior close used)"
    )

    quality_icon = {
        'HIGH':            '✓',
        'LOW_CONFIDENCE':  '⚠',
        'INSUFFICIENT':    '✗',
    }.get(result.get('quality_flag'), '?')

    sep = '─' * 64

    print(f"\n{'═'*64}")
    print(f"  {result['etf_ticker']}  │  Holdings: {result['composition_date']} (T-1)  │  Market: {market_status}")
    print(f"  Calculated: {result['calculation_timestamp']}")
    print(f"{'═'*64}")

    # ── NAV section ───────────────────────────────────────────────────────
    print(f"\n  NAV")
    print(sep)
    print(f"    Official NAV (T-1):      ${result['official_nav']:.4f}")

    if result['fair_nav_primary'] is not None:
        print(f"    Fair NAV (primary):      ${result['fair_nav_primary']:.4f}   ← shares-based")
    else:
        print(f"    Fair NAV (primary):      N/A  (insufficient coverage)")

    if result['fair_nav_weight_based'] is not None and result['fair_nav_primary'] is not None:
        delta = result['fair_nav_weight_based'] - result['fair_nav_primary']
        print(f"    Fair NAV (weight check): ${result['fair_nav_weight_based']:.4f}   [Δ {delta:+.4f}]")
    elif result['fair_nav_weight_based'] is not None:
        print(f"    Fair NAV (weight check): ${result['fair_nav_weight_based']:.4f}")
    else:
        print(f"    Fair NAV (weight check): N/A  (prev_close unavailable)")

    if result['etf_market_price'] is not None:
        print(f"    ETF market price:        ${result['etf_market_price']:.4f}")
    else:
        print(f"    ETF market price:        N/A  (yfinance fetch failed)")

    if result['premium_discount_pct'] is not None:
        direction = "PREMIUM  ▲" if result['premium_discount_pct'] > 0 else "DISCOUNT ▼"
        print(f"    Premium / Discount:      {result['premium_discount_pct']:+.4f}%  [{direction}]")

    # ── Coverage section ──────────────────────────────────────────────────
    print(f"\n  Coverage                                    [{quality_icon} {result['quality_flag']}]")
    print(sep)
    print(f"    Components priced:   {result['priced_components']} / {result['total_components']}")
    print(f"    Weight covered:      {result['covered_weight_pct']:.2f}%")
    print(f"    Weight uncovered:    {result['uncovered_weight_pct']:.2f}%")
    print(f"    Unpriced tickers:    {result['unpriced_components']}  (priceable, no yfinance data)")
    for t in result.get('unpriced_tickers') or []:
        print(f"      · {t}")
    print(f"    Skipped components:  {result['skipped_components']}  (cash, futures, derivatives)")

    if result['quality_flag'] == 'LOW_CONFIDENCE':
        print(f"    ⚠  Coverage is below 95% — treat fair NAV as indicative only.")
    elif result['quality_flag'] == 'INSUFFICIENT':
        print(f"    ✗  Coverage < 80% — fair NAV not computed. Arb signals unavailable.")

    # ── Arbitrage section ─────────────────────────────────────────────────
    print(f"\n  Arbitrage Signals  (spread=0.05%, commission=0.03%/leg, breakeven≈0.055%/direction)")
    print(sep)

    # Scenario A
    print(f"    Scenario A — Sell ETF, buy basket  (ETF at PREMIUM → creation arb):")
    if result['arb_a_profit_pct'] is not None:
        signal_icon = '★' if result['arb_a_signal'] == 'OPPORTUNITY' else '·'
        print(f"      ETF bid net:     ${result['arb_a_etf_bid_net']:.4f}")
        print(f"      Basket ask net:  ${result['arb_a_basket_ask_net']:.4f}")
        print(f"      Profit:          {result['arb_a_profit_pct']:+.6f}%   {signal_icon} {result['arb_a_signal']}")
    else:
        print(f"      {result['arb_a_signal']}")

    print()

    # Scenario B
    print(f"    Scenario B — Buy ETF, sell basket  (ETF at DISCOUNT → redemption arb):")
    if result['arb_b_profit_pct'] is not None:
        signal_icon = '★' if result['arb_b_signal'] == 'OPPORTUNITY' else '·'
        print(f"      ETF ask net:     ${result['arb_b_etf_ask_net']:.4f}")
        print(f"      Basket bid net:  ${result['arb_b_basket_bid_net']:.4f}")
        print(f"      Profit:          {result['arb_b_profit_pct']:+.6f}%   {signal_icon} {result['arb_b_signal']}")
    else:
        print(f"      {result['arb_b_signal']}")

    # ── Warnings section ──────────────────────────────────────────────────
    print(f"\n  Notes")
    print(sep)
    if result.get('currency_warning'):
        print(f"    ⚠  {result['currency_warning']}")
    print(f"    ℹ  Creation/redemption arb requires Authorized Participant status.")
    print(f"       Minimum creation unit for SPY ≈ 50,000 shares (~$28M).")
    print(f"       This output is for monitoring and analysis only.")
    print(f"{'═'*64}\n")


if __name__ == "__main__":
    # Default: run against SPY.
    # Edit etf_tickers to monitor multiple ETFs at once.
    run_arb_monitor(
        etf_tickers   = ["SPY"],
        db_path       = "data/etf_compositions.db",
        store_results = True
    )
