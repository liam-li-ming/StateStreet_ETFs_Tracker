import yfinance as yf
import pandas as pd
from datetime import datetime
from store_equity_etf_compositions_db import EquityEtfCompositionDb


class DetectEtfArbitrage:
    """
    Detects ETF arbitrage opportunities by comparing the ETF market price
    to a calculated fair NAV derived from component holdings, cash positions,
    and live prices.

    Fair NAV = (Stock Value + Cash Value) / Shares Outstanding
      where Stock Value = SUM(stock_shares_i * stock_price_i)
            Cash Value  = SUM(cash_amount_j * fx_rate_j)

    Arbitrage Strategy (creation/redemption mechanism):
      PREMIUM  -> Sell ETF / Buy basket (APs create new ETF shares)
      DISCOUNT -> Buy ETF / Sell basket (APs redeem ETF shares)

    Usage:
        db = EquityEtfCompositionDb()
        db.connect_db()
        detector = DetectEtfArbitrage(db)
        result = detector.analyze_etf("SPY")
        db.close_db()
    """

    # Map component_name keywords to yfinance FX ticker (currency -> USD)
    CURRENCY_TO_FX = {
        "US DOLLAR": None,                        # $1.00 per unit
        "U.S. DOLLAR": None,
        "SSI US GOV MONEY MARKET CLASS": None,    # $1.00 per share
        "EURO CURRENCY": "EURUSD=X",
        "POUND STERLING": "GBPUSD=X",
        "JAPANESE YEN": "JPYUSD=X",
        "CANADIAN DOLLAR": "CADUSD=X",
        "AUSTRALIAN DOLLAR": "AUDUSD=X",
        "HONG KONG DOLLAR": "HKDUSD=X",
        "SWISS FRANC": "CHFUSD=X",
        "SWEDISH KRONA": "SEKUSD=X",
        "NORWEGIAN KRONE": "NOKUSD=X",
        "DANISH KRONE": "DKKUSD=X",
        "NEW ZEALAND DOLLAR": "NZDUSD=X",
        "SINGAPORE DOLLAR": "SGDUSD=X",
        "SOUTH KOREAN WON": "KRWUSD=X",
        "NEW TAIWAN DOLLAR": "TWDUSD=X",
        "BRAZILIAN REAL": "BRLUSD=X",
        "MEXICAN PESO (NEW)": "MXNUSD=X",
        "INDIAN RUPEE": "INRUSD=X",
        "SOUTH AFRICAN RAND": "ZARUSD=X",
        "INDONESIAN RUPIAH": "IDRUSD=X",
        "MALAYSIAN RINGGIT": "MYRUSD=X",
        "PHILIPPINE PESO": "PHPUSD=X",
        "THAI BAHT": "THBUSD=X",
        "POLISH ZLOTY": "PLNUSD=X",
        "TURKISH LIRA": "TRYUSD=X",
        "CHILEAN PESO": "CLPUSD=X",
        "COLOMBIAN PESO": "COPUSD=X",
        "NEW ISRAELI SHEQEL": "ILSUSD=X",
        "KUWAITI DINAR": "KWDUSD=X",
        "QATARI RIAL": "QARUSD=X",
        "SAUDI RIYAL": "SARUSD=X",
        "CHINESE YUAN": "CNYUSD=X",
    }

    # Additional keywords for partial matching of cash-like components
    CASH_PARTIAL_KEYWORDS = [
        "CASH COLLATERAL",
        "MARGIN CASH",
        "MONEY MARKET",
        "TREASURY BILL",
        "T-BILL",
    ]

    def __init__(self, db):
        self.db = db
        self.price_cache = {}
        self.fx_cache = {}

    def _is_cash_component(self, component_name):
        """Check if a component is a cash/currency/money market position."""
        name_upper = str(component_name).strip().upper()
        # Exact match against known currency names
        if name_upper in self.CURRENCY_TO_FX:
            return True
        # Partial match against cash-like keywords
        for keyword in self.CASH_PARTIAL_KEYWORDS:
            if keyword in name_upper:
                return True
        return False

    def _get_cash_usd_value(self, component_name):
        """
        Get the USD value per unit of a cash component.
        Returns the USD exchange rate, or None if not a recognized cash component.

        For exact-match currency names, uses the corresponding FX ticker.
        For partial-match cash keywords (e.g. CASH COLLATERAL, MONEY MARKET),
        assumes USD-denominated ($1 per unit).
        """
        name_upper = str(component_name).strip().upper()

        # Check exact match first
        if name_upper in self.CURRENCY_TO_FX:
            fx_ticker = self.CURRENCY_TO_FX[name_upper]
            if fx_ticker is None:
                return 1.0
            return self._fetch_fx_rate(fx_ticker)

        # Check partial-match cash keywords (assume USD-denominated)
        for keyword in self.CASH_PARTIAL_KEYWORDS:
            if keyword in name_upper:
                return 1.0

        return None

    def _fetch_fx_rate(self, fx_ticker):
        """Fetch an FX rate from cache or yfinance."""
        if fx_ticker in self.fx_cache:
            return self.fx_cache[fx_ticker]
        try:
            data = yf.download(fx_ticker, period="1d", progress=False, auto_adjust=True)
            if not data.empty:
                rate = float(data['Close'].iloc[-1].iloc[0])
                self.fx_cache[fx_ticker] = rate
                return rate
        except Exception:
            pass
        self.fx_cache[fx_ticker] = None
        return None

    def fetch_prices(self, tickers):
        """
        Fetch current market prices for a list of tickers via yfinance.
        Uses a shared cache to avoid redundant API calls.

        :param tickers: list of ticker symbols
        :return: dict mapping ticker -> price (float or None if unavailable)
        """
        # Filter valid tickers not already cached
        tickers_to_fetch = []
        for t in set(tickers):
            if not t or not isinstance(t, str):
                continue
            t_clean = t.strip().upper()
            if t_clean in ("", "NAN", "--", "-", "NONE"):
                continue
            # yfinance uses dashes for share classes (e.g. BRK-B not BRK.B)
            t_clean = t_clean.replace(".", "-")
            if t_clean not in self.price_cache:
                tickers_to_fetch.append(t_clean)

        if tickers_to_fetch:
            try:
                data = yf.download(
                    tickers_to_fetch,
                    period="1d",
                    progress=False,
                    threads=True,
                    auto_adjust=True
                )

                if len(tickers_to_fetch) == 1:
                    t = tickers_to_fetch[0]
                    if not data.empty:
                        self.price_cache[t] = float(data['Close'].iloc[-1].iloc[0])
                    else:
                        self.price_cache[t] = None
                else:
                    for t in tickers_to_fetch:
                        try:
                            price = float(data[('Close', t)].dropna().iloc[-1])
                            self.price_cache[t] = price
                        except (KeyError, IndexError):
                            self.price_cache[t] = None
            except Exception as e:
                print(f"  yfinance batch download error: {e}")
                for t in tickers_to_fetch:
                    self.price_cache[t] = None

        # Build result for the requested tickers
        result = {}
        for t in tickers:
            if t and isinstance(t, str):
                t_clean = t.strip().upper().replace(".", "-")
                result[t_clean] = self.price_cache.get(t_clean)
        return result

    def analyze_etf(self, etf_ticker):
        """
        Analyze a single ETF for arbitrage opportunity.

        :param etf_ticker: ETF ticker symbol (e.g. "SPY")
        :return: dict with analysis results, or None if data unavailable
        """
        composition_df = self.db.get_latest_composition(etf_ticker)
        if composition_df.empty:
            print(f"  No composition data found for {etf_ticker}")
            return None

        # Fund-level metadata (same across all rows)
        shares_outstanding = composition_df['shares_outstanding'].iloc[0]
        reported_nav = composition_df['nav'].iloc[0]
        composition_date = composition_df['composition_date'].iloc[0]

        if pd.isna(shares_outstanding) or shares_outstanding <= 0:
            print(f"  Invalid shares_outstanding for {etf_ticker}")
            return None

        # Classify each component: cash, stock, or unpriceable
        cash_rows = []
        stock_rows = []
        skipped = []

        for _, row in composition_df.iterrows():
            name = row['component_name']
            ticker_val = row['component_ticker']

            if self._is_cash_component(name):
                cash_rows.append(row)
            elif pd.notna(ticker_val) and str(ticker_val).strip() not in ('', 'nan', 'NAN'):
                stock_rows.append(row)
            else:
                skipped.append({
                    "name": name,
                    "ticker": str(ticker_val),
                    "weight": row['component_weight'],
                    "reason": "no_ticker"
                })

        # Calculate portfolio value
        total_value = 0.0
        total_weight_priced = 0.0
        total_weight_all = composition_df['component_weight'].sum()
        cash_value = 0.0
        stock_value = 0.0

        # Price cash components (USD = $1, foreign = FX rate)
        for row in cash_rows:
            shares = row['component_shares']
            weight = row['component_weight']
            usd_rate = self._get_cash_usd_value(row['component_name'])

            if usd_rate is not None and not pd.isna(shares):
                value = shares * usd_rate
                total_value += value
                cash_value += value
                total_weight_priced += weight
            else:
                skipped.append({
                    "name": row['component_name'],
                    "ticker": "-",
                    "weight": weight,
                    "reason": "fx_rate_not_found"
                })

        # Fetch stock prices + ETF market price
        stock_df = pd.DataFrame(stock_rows) if stock_rows else pd.DataFrame()
        if not stock_df.empty:
            tickers_needed = stock_df['component_ticker'].str.strip().str.upper().str.replace(".", "-", regex=False).unique().tolist()
        else:
            tickers_needed = []
        tickers_needed.append(etf_ticker.upper())
        prices = self.fetch_prices(tickers_needed)

        # Price stock components
        for row in stock_rows:
            ticker = str(row['component_ticker']).strip().upper().replace(".", "-")
            shares = row['component_shares']
            weight = row['component_weight']
            price = prices.get(ticker)

            if price is not None and not pd.isna(shares):
                value = shares * price
                total_value += value
                stock_value += value
                total_weight_priced += weight
            else:
                skipped.append({
                    "name": row['component_name'],
                    "ticker": ticker,
                    "weight": weight,
                    "reason": "price_not_found"
                })

        # Fair NAV = total portfolio value / shares outstanding
        calculated_nav = total_value / shares_outstanding

        # ETF market price
        market_price = prices.get(etf_ticker.upper())
        if market_price is None:
            print(f"  Could not fetch market price for {etf_ticker}")
            return None

        # Premium / Discount
        premium_discount_pct = ((market_price - calculated_nav) / calculated_nav) * 100

        premium_discount_vs_reported = None
        if reported_nav and not pd.isna(reported_nav) and reported_nav > 0:
            premium_discount_vs_reported = ((market_price - reported_nav) / reported_nav) * 100

        # Signal classification and arbitrage strategy
        # ETF arbitrage works through the creation/redemption mechanism:
        #   PREMIUM  -> APs buy the underlying basket, create ETF shares, sell ETF at market
        #   DISCOUNT -> APs buy ETF at market, redeem for underlying basket, sell components
        if premium_discount_pct > 0.1:
            signal = "PREMIUM"
            arbitrage_action = "SELL ETF / BUY BASKET (creation arbitrage)"
        elif premium_discount_pct < -0.1:
            signal = "DISCOUNT"
            arbitrage_action = "BUY ETF / SELL BASKET (redemption arbitrage)"
        else:
            signal = "FAIR"
            arbitrage_action = "NO ACTION"

        estimated_profit_per_share = round(abs(market_price - calculated_nav), 4)

        coverage_pct = (total_weight_priced / total_weight_all * 100) if total_weight_all > 0 else 0.0

        return {
            "etf_ticker": etf_ticker,
            "analysis_timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "composition_date": composition_date,
            "total_components": len(composition_df),
            "priced_components": len(composition_df) - len(skipped),
            "cash_components": len(cash_rows),
            "stock_components": len(stock_rows),
            "skipped_components": skipped,
            "coverage_pct": round(coverage_pct, 2),
            "shares_outstanding": shares_outstanding,
            "total_portfolio_value": round(total_value, 2),
            "stock_value": round(stock_value, 2),
            "cash_value": round(cash_value, 2),
            "calculated_nav": round(calculated_nav, 4),
            "market_price": round(market_price, 4),
            "reported_nav": reported_nav,
            "premium_discount_pct": round(premium_discount_pct, 4),
            "premium_discount_vs_reported_pct": round(premium_discount_vs_reported, 4) if premium_discount_vs_reported is not None else None,
            "signal": signal,
            "arbitrage_action": arbitrage_action,
            "estimated_profit_per_share": estimated_profit_per_share,
        }

    def scan_all_etfs(self, threshold_pct=0.5):
        """
        Scan all ETFs in the database for arbitrage opportunities.

        :param threshold_pct: minimum absolute premium/discount % to flag
        :return: DataFrame with one row per ETF, sorted by |premium/discount|
        """
        tickers = self.db.get_available_tickers()
        print(f"Scanning {len(tickers)} ETFs for arbitrage opportunities...")
        print(f"Threshold: {threshold_pct}% premium/discount\n")

        results = []
        for i, ticker in enumerate(tickers, 1):
            print(f"[{i}/{len(tickers)}] Analyzing {ticker}...")
            try:
                result = self.analyze_etf(ticker)
                if result:
                    results.append(result)
                    self._print_brief(result)
            except Exception as e:
                print(f"  Error analyzing {ticker}: {e}")

        if not results:
            print("No results generated.")
            return pd.DataFrame()

        summary_df = pd.DataFrame([{
            "etf_ticker": r["etf_ticker"],
            "market_price": r["market_price"],
            "calculated_nav": r["calculated_nav"],
            "reported_nav": r["reported_nav"],
            "premium_discount_pct": r["premium_discount_pct"],
            "coverage_pct": r["coverage_pct"],
            "signal": r["signal"],
            "arbitrage_action": r["arbitrage_action"],
            "est_profit_per_share": r["estimated_profit_per_share"],
            "cash_value": r["cash_value"],
            "composition_date": r["composition_date"],
            "priced_components": r["priced_components"],
            "total_components": r["total_components"],
        } for r in results])

        summary_df = summary_df.sort_values(
            key=lambda col: col.abs(),
            by="premium_discount_pct",
            ascending=False
        )

        opportunities = summary_df[summary_df["premium_discount_pct"].abs() >= threshold_pct]

        print(f"\n{'='*70}")
        print(f"SCAN COMPLETE: {len(results)} ETFs analyzed")
        print(f"Arbitrage opportunities (>= {threshold_pct}% deviation): {len(opportunities)}")
        print(f"{'='*70}")

        if not opportunities.empty:
            print("\nTop Opportunities:")
            print(opportunities.to_string(index=False))

        return summary_df

    def _print_brief(self, result):
        """Print a one-line summary for scan progress."""
        marker = ">>>" if abs(result["premium_discount_pct"]) > 0.5 else "   "
        print(f"  {marker} {result['signal']:8s} | "
              f"Mkt: ${result['market_price']:.2f} | "
              f"NAV: ${result['calculated_nav']:.2f} | "
              f"Dev: {result['premium_discount_pct']:+.3f}% | "
              f"Cash: ${result['cash_value']:,.0f} | "
              f"Cov: {result['coverage_pct']:.1f}%")

    def format_result(self, result):
        """Format a full analysis result for detailed console output."""
        lines = [
            f"\n{'='*60}",
            f"ETF Arbitrage Analysis: {result['etf_ticker']}",
            f"{'='*60}",
            f"  Analysis Time:      {result['analysis_timestamp']}",
            f"  Composition Date:   {result['composition_date']}",
            f"  Components:         {result['priced_components']}/{result['total_components']} priced "
            f"({result['stock_components']} stocks, {result['cash_components']} cash)",
            f"  Portfolio Coverage:  {result['coverage_pct']:.2f}%",
            f"",
            f"  Portfolio Breakdown:",
            f"    Stock Value:      ${result['stock_value']:,.2f}",
            f"    Cash Value:       ${result['cash_value']:,.2f}",
            f"    Total Value:      ${result['total_portfolio_value']:,.2f}",
            f"",
            f"  Market Price:       ${result['market_price']:.4f}",
            f"  Calculated NAV:     ${result['calculated_nav']:.4f}",
            f"  Reported NAV:       ${result['reported_nav']}",
            f"  Shares Outstanding: {result['shares_outstanding']:,.0f}",
            f"",
            f"  Premium/Discount:   {result['premium_discount_pct']:+.4f}%",
            f"  Signal:             {result['signal']}",
            f"  Arbitrage Action:   {result['arbitrage_action']}",
            f"  Est. Profit/Share:  ${result['estimated_profit_per_share']:.4f}",
        ]
        if result['skipped_components']:
            lines.append("")
            lines.append(f"  Skipped Components ({len(result['skipped_components'])}):")
            for s in result['skipped_components'][:10]:
                lines.append(f"    - {s['name'][:40]:40s} | {str(s['ticker']):8s} | {s['reason']}")
            if len(result['skipped_components']) > 10:
                lines.append(f"    ... and {len(result['skipped_components']) - 10} more")
        lines.append(f"{'='*60}")
        return "\n".join(lines)


if __name__ == "__main__":
    db = EquityEtfCompositionDb(db_path="data/etf_compositions.db")

    try:
        db.connect_db()
        detector = DetectEtfArbitrage(db)

        # Single ETF analysis
        print("Single ETF Analysis")
        print("=" * 60)
        result = detector.analyze_etf("SPY")
        if result:
            print(detector.format_result(result))

        # Scan all ETFs
        print("\n\nFull ETF Scan")
        print("=" * 60)
        summary_df = detector.scan_all_etfs(threshold_pct=0.5)

        if not summary_df.empty:
            print("\nFull Summary Table:")
            print(summary_df.to_string(index=False))

    finally:
        db.close_db()
