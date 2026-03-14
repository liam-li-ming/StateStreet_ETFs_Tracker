import sqlite3
import pandas as pd
from datetime import datetime
import yfinance as yf
import pytz


class FairNavCalculator:
    """
    Calculates fair NAV estimates for State Street ETFs using live component
    prices from yfinance and stored T-1 holdings from the SQLite database.

    Applies a bid/ask spread simulation and round-trip commission model to
    compute creation and redemption arbitrage profit/loss metrics.

    Limitations:
        - Uses T-1 holdings (SSGA publication lag). Results degrade around
          index rebalance/reconstitution dates.
        - yfinance prices are 15-min delayed during US market hours.
        - Non-USD components are not FX-adjusted. Fair NAV for international
          equity ETFs may be overstated or understated.
        - Only Authorized Participants can exploit creation/redemption
          arbitrage in practice. Minimum creation unit for SPY is ~50,000
          shares (~$28M). This tool is for monitoring and analysis only.
        - Daily expense ratio accrual is not modeled (negligible intraday).
    """

    HALF_SPREAD   = 0.00025   # 0.05% full bid-ask spread divided by 2
    COMMISSION    = 0.0003    # 0.03% commission per trade leg
    COVERAGE_HIGH = 0.95      # >= 95% weight priced  →  quality_flag = 'HIGH'
    COVERAGE_LOW  = 0.80      # 80–95%                →  'LOW_CONFIDENCE'
                              # < 80%                 →  'INSUFFICIENT'

    def __init__(self, db_conn):
        """
        :param db_conn: Active sqlite3.Connection (opened and closed by caller).
        """
        self.conn = db_conn

    # ──────────────────────────────────────────────────────────────────────
    # Ticker normalisation
    # ──────────────────────────────────────────────────────────────────────

    def normalize_ticker_for_yahoo(self, ticker):
        """
        Convert an SSGA component ticker to a Yahoo Finance compatible symbol,
        or return None if the ticker is non-tradeable.

        Rules applied in order:
        1. Strip leading/trailing whitespace.
        2. Skip empty string or the string 'NAN' (pandas NaN coerced to str).
        3. Skip purely numeric strings — SSGA writes CUSIP numbers into the
           Ticker column for cash/index positions (e.g. '594918104').
        4. Skip tickers containing internal spaces (e.g. 'CASH & CASH EQUIV').
        5. Skip tickers starting with '#' (e.g. '#N/A' placeholder values).
        6. Replace the first '.' with '-' for share class tickers:
               BRK.B  →  BRK-B
               BF.B   →  BF-B
        7. Return the normalized ticker.

        :param ticker: Raw ticker string from component_ticker column.
        :return: Yahoo-compatible ticker string, or None if non-tradeable.
        """
        if not isinstance(ticker, str):
            return None

        ticker = ticker.strip()

        # Rule 2: empty or NaN placeholder
        if not ticker or ticker.upper() == 'NAN':
            return None

        # Rule 3: purely numeric — CUSIP written as ticker
        if ticker.replace('-', '').isdigit():
            return None

        # Rule 4: spaces indicate a cash/description field
        if ' ' in ticker:
            return None

        # Rule 5: Yahoo placeholder
        if ticker.startswith('#'):
            return None

        # Rule 6: share class period → hyphen (Yahoo Finance convention)
        if '.' in ticker:
            ticker = ticker.replace('.', '-', 1)

        return ticker

    # ──────────────────────────────────────────────────────────────────────
    # Data loading
    # ──────────────────────────────────────────────────────────────────────

    def load_latest_composition(self, etf_ticker):
        """
        Load the most recent composition snapshot from equity_etf_compositions.

        :param etf_ticker: ETF ticker symbol (e.g. 'SPY').
        :return: DataFrame with all composition columns ordered by
                 component_weight DESC, or empty DataFrame on failure.
        """
        query = """
            SELECT * FROM equity_etf_compositions
            WHERE etf_ticker = ?
              AND composition_date = (
                  SELECT MAX(composition_date)
                  FROM equity_etf_compositions
                  WHERE etf_ticker = ?
              )
            ORDER BY component_weight DESC
        """
        try:
            df = pd.read_sql_query(query, self.conn, params=(etf_ticker, etf_ticker))
            return df
        except Exception as e:
            print(f"Error loading composition for {etf_ticker}: {e}")
            return pd.DataFrame()

    # ──────────────────────────────────────────────────────────────────────
    # Price fetching
    # ──────────────────────────────────────────────────────────────────────

    def fetch_component_prices(self, yahoo_tickers):
        """
        Batch-download the latest and previous closing prices for a list of
        Yahoo-normalized tickers.

        Uses period='5d' to guarantee at least two trading days of data across
        weekends and public holidays. The most recent close is used as the
        current price; the second-most-recent close is the prev_close used by
        the weight-based NAV cross-check formula.

        :param yahoo_tickers: List of Yahoo-compatible ticker strings.
        :return: Dict mapping ticker → {'price': float, 'prev_close': float | None}.
                 Tickers with no price data are absent from the returned dict.
        """
        if not yahoo_tickers:
            return {}

        tickers_str = " ".join(yahoo_tickers)

        try:
            data = yf.download(
                tickers_str,
                period      = "5d",
                interval    = "1d",
                auto_adjust = False,
                progress    = False
            )

            if data.empty:
                print("  Warning: yf.download returned empty DataFrame.")
                return {}

            # data['Close'] is a DataFrame (columns = tickers) for multi-ticker
            # downloads, or a Series for single-ticker downloads.
            close_data = data['Close']

            if isinstance(close_data, pd.Series):
                # Single-ticker edge case: wrap into a DataFrame
                close_df = close_data.to_frame(name=yahoo_tickers[0])
            else:
                close_df = close_data

            # Drop rows where every ticker is NaN (non-trading day padding)
            close_df = close_df.dropna(how='all')

            price_map = {}
            for ticker in yahoo_tickers:
                if ticker not in close_df.columns:
                    continue

                series = close_df[ticker].dropna()
                if series.empty:
                    continue

                price_map[ticker] = {
                    'price':      float(series.iloc[-1]),
                    'prev_close': float(series.iloc[-2]) if len(series) >= 2 else None
                }

            return price_map

        except Exception as e:
            print(f"  Error fetching component prices: {e}")
            return {}

    def fetch_etf_market_price(self, etf_ticker):
        """
        Fetch the ETF's own current market price.

        Tries yf.Ticker.fast_info.last_price first (most current during market
        hours). Falls back to the latest close from yf.download on failure.

        :param etf_ticker: ETF ticker symbol (e.g. 'SPY').
        :return: Float market price, or None on failure.
        """
        try:
            fast_info = yf.Ticker(etf_ticker).fast_info
            price = getattr(fast_info, 'last_price', None)
            if price and float(price) > 0:
                return float(price)
        except Exception as e:
            print(f"  fast_info failed for {etf_ticker}: {e}")

        # Fallback: latest close from download
        try:
            data = yf.download(
                etf_ticker,
                period      = "2d",
                interval    = "1d",
                auto_adjust = False,
                progress    = False
            )
            if not data.empty:
                return float(data['Close'].iloc[-1])
        except Exception as e:
            print(f"  Error fetching ETF market price for {etf_ticker}: {e}")

        return None

    # ──────────────────────────────────────────────────────────────────────
    # Market hours
    # ──────────────────────────────────────────────────────────────────────

    def is_market_open(self):
        """
        Determine whether the US equity market is currently open based on
        current Eastern time.

        Note: Does not account for early closes or public holidays.

        :return: True if between 09:30 and 16:00 ET on a weekday, else False.
        """
        try:
            eastern = pytz.timezone('US/Eastern')
            now = datetime.now(eastern)
            if now.weekday() >= 5:  # Saturday=5, Sunday=6
                return False
            market_open  = now.replace(hour=9,  minute=30, second=0, microsecond=0)
            market_close = now.replace(hour=16, minute=0,  second=0, microsecond=0)
            return market_open <= now <= market_close
        except Exception as e:
            print(f"  Error checking market hours: {e}")
            return False

    # ──────────────────────────────────────────────────────────────────────
    # NAV calculation — master method
    # ──────────────────────────────────────────────────────────────────────

    def calculate_fair_nav(self, etf_ticker):
        """
        Master method: orchestrates composition load, price fetch, coverage
        check, NAV calculation, and arbitrage metric computation for one ETF.

        Primary NAV formula (shares-based, most accurate):
            fair_nav = sum(component_shares_i * price_i) / shares_outstanding

        Fallback NAV formula (weight-based, used as cross-check):
            fair_nav = official_nav * sum(w_i * price_i / prev_close_i)
                       / sum(w_i for priced components)

        :param etf_ticker: ETF ticker to analyse (e.g. 'SPY').
        :return: Result dict with all output fields (see _build_result_dict),
                 or None if no composition data exists in the database.
        """
        print(f"\nCalculating fair NAV for {etf_ticker}...")

        # ── Step 1: Load T-1 composition from DB ──────────────────────────
        composition_df = self.load_latest_composition(etf_ticker)
        if composition_df.empty:
            print(f"  No composition data found for {etf_ticker}. Run main.py first.")
            return None

        composition_date   = composition_df['composition_date'].iloc[0]
        official_nav       = composition_df['nav'].iloc[0]
        shares_outstanding = composition_df['shares_outstanding'].iloc[0]

        print(f"  Composition date:   {composition_date}  (T-1)")
        print(f"  Official NAV (T-1): ${official_nav:.4f}")
        print(f"  Components in DB:   {len(composition_df)}")

        # ── Step 2: Normalize component tickers ───────────────────────────
        priceable = []    # list of (row_index, yahoo_ticker)
        skipped   = []    # non-tradeable raw tickers (cash, futures, etc.)

        for idx, row in composition_df.iterrows():
            raw_ticker   = str(row.get('component_ticker', ''))
            yahoo_ticker = self.normalize_ticker_for_yahoo(raw_ticker)
            if yahoo_ticker:
                priceable.append((idx, yahoo_ticker))
            else:
                skipped.append(raw_ticker)

        priceable_yahoo = [t for _, t in priceable]
        print(f"  Priceable:          {len(priceable)}   Skipped (non-tradeable): {len(skipped)}")

        # ── Step 3: Batch-fetch prices from yfinance ──────────────────────
        print(f"  Fetching prices from yfinance ({len(priceable_yahoo)} tickers)...")
        price_map = self.fetch_component_prices(priceable_yahoo)
        print(f"  Prices received:    {len(price_map)} / {len(priceable_yahoo)}")

        # ── Step 4: Coverage check ────────────────────────────────────────
        total_weight   = composition_df['component_weight'].sum()
        covered_weight = 0.0
        priced_rows    = []    # (row_index, yahoo_ticker) — got a price
        unpriced       = []    # priceable tickers with no yfinance data

        for idx, yahoo_ticker in priceable:
            weight = composition_df.loc[idx, 'component_weight']
            if yahoo_ticker in price_map:
                covered_weight += weight if pd.notna(weight) else 0.0
                priced_rows.append((idx, yahoo_ticker))
            else:
                unpriced.append(yahoo_ticker)

        coverage_pct     = covered_weight / total_weight if total_weight > 0 else 0.0
        uncovered_weight = 1.0 - coverage_pct

        if coverage_pct >= self.COVERAGE_HIGH:
            quality_flag = 'HIGH'
        elif coverage_pct >= self.COVERAGE_LOW:
            quality_flag = 'LOW_CONFIDENCE'
        else:
            quality_flag = 'INSUFFICIENT'

        print(f"  Coverage:           {coverage_pct*100:.2f}%  [{quality_flag}]")

        # ── Step 5: Primary fair NAV — shares-based ───────────────────────
        fair_nav_primary = None
        if quality_flag != 'INSUFFICIENT' and shares_outstanding and shares_outstanding > 0:
            portfolio_value = 0.0
            for idx, yahoo_ticker in priced_rows:
                shares = composition_df.loc[idx, 'component_shares']
                price  = price_map[yahoo_ticker]['price']
                if pd.notna(shares) and price:
                    portfolio_value += shares * price
            fair_nav_primary = portfolio_value / shares_outstanding

        # ── Step 6: Fallback fair NAV — weight-based cross-check ──────────
        fair_nav_weight_based = None
        if quality_flag != 'INSUFFICIENT' and official_nav and covered_weight > 0:
            weighted_ratio   = 0.0
            valid_weight_sum = 0.0
            for idx, yahoo_ticker in priced_rows:
                weight     = composition_df.loc[idx, 'component_weight']
                prev_close = price_map[yahoo_ticker]['prev_close']
                price      = price_map[yahoo_ticker]['price']
                if pd.notna(weight) and price and prev_close and prev_close > 0:
                    weighted_ratio   += weight * (price / prev_close)
                    valid_weight_sum += weight
            if valid_weight_sum > 0:
                fair_nav_weight_based = official_nav * (weighted_ratio / valid_weight_sum)

        # ── Step 7: ETF market price ──────────────────────────────────────
        etf_market_price = self.fetch_etf_market_price(etf_ticker)
        market_open      = self.is_market_open()

        # ── Step 8: Premium / discount ────────────────────────────────────
        premium_discount_pct = None
        if fair_nav_primary and etf_market_price:
            premium_discount_pct = (
                (etf_market_price - fair_nav_primary) / fair_nav_primary * 100
            )

        # ── Step 9: Currency warning ──────────────────────────────────────
        currency_warning = None
        if 'component_currency' in composition_df.columns:
            non_usd = composition_df[
                composition_df['component_currency'].notna() &
                (composition_df['component_currency'].str.upper() != 'USD')
            ]
            if not non_usd.empty:
                currencies = non_usd['component_currency'].unique().tolist()
                currency_warning = (
                    f"Non-USD components detected ({', '.join(currencies)}). "
                    f"FX conversion not applied — fair NAV may be inaccurate "
                    f"for international holdings."
                )

        # ── Step 10: Arbitrage metrics ────────────────────────────────────
        if quality_flag != 'INSUFFICIENT' and fair_nav_primary and etf_market_price:
            arb_metrics = self.calculate_arb_metrics(fair_nav_primary, etf_market_price)
        else:
            arb_metrics = {
                'arb_a_etf_bid_net':    None,
                'arb_a_basket_ask_net': None,
                'arb_a_profit_pct':     None,
                'arb_a_signal':         'INSUFFICIENT_COVERAGE',
                'arb_b_etf_ask_net':    None,
                'arb_b_basket_bid_net': None,
                'arb_b_profit_pct':     None,
                'arb_b_signal':         'INSUFFICIENT_COVERAGE',
            }

        return self._build_result_dict(
            etf_ticker            = etf_ticker,
            composition_date      = composition_date,
            official_nav          = official_nav,
            shares_outstanding    = shares_outstanding,
            fair_nav_primary      = fair_nav_primary,
            fair_nav_weight_based = fair_nav_weight_based,
            etf_market_price      = etf_market_price,
            premium_discount_pct  = premium_discount_pct,
            coverage_pct          = coverage_pct,
            uncovered_weight      = uncovered_weight,
            total_components      = len(composition_df),
            priced_components     = len(priced_rows),
            unpriced_components   = len(unpriced),
            unpriced_tickers      = unpriced,
            skipped_components    = len(skipped),
            quality_flag          = quality_flag,
            market_open           = market_open,
            currency_warning      = currency_warning,
            arb_metrics           = arb_metrics,
        )

    # ──────────────────────────────────────────────────────────────────────
    # Arbitrage metrics
    # ──────────────────────────────────────────────────────────────────────

    def calculate_arb_metrics(self, fair_nav, etf_market_price):
        """
        Compute creation and redemption arbitrage P&L after simulated
        bid/ask spread (0.05%) and commission (0.03% per leg).

        Scenario A — Creation arb (ETF at PREMIUM: sell ETF, buy basket):
            Revenue: etf_market_price × (1 − HALF_SPREAD − COMMISSION)
            Cost:    fair_nav         × (1 + HALF_SPREAD + COMMISSION)
            Profit % = (Revenue − Cost) / etf_market_price × 100

        Scenario B — Redemption arb (ETF at DISCOUNT: buy ETF, sell basket):
            Cost:    etf_market_price × (1 + HALF_SPREAD + COMMISSION)
            Revenue: fair_nav         × (1 − HALF_SPREAD − COMMISSION)
            Profit % = (Revenue − Cost) / etf_market_price × 100

        Breakeven threshold per direction ≈ 0.055% (HALF_SPREAD + COMMISSION).
        At least 0.11% premium or discount is needed for a round-trip profit.

        :param fair_nav: Estimated fair NAV per share.
        :param etf_market_price: Current ETF market price.
        :return: Dict with all Scenario A and Scenario B fields.
        """
        cost_factor = self.HALF_SPREAD + self.COMMISSION  # 0.00055

        # Scenario A: sell ETF at bid (net of commission), buy basket at ask
        arb_a_etf_bid_net    = etf_market_price * (1 - cost_factor)
        arb_a_basket_ask_net = fair_nav         * (1 + cost_factor)
        arb_a_profit_pct     = (arb_a_etf_bid_net - arb_a_basket_ask_net) / etf_market_price * 100
        arb_a_signal         = 'OPPORTUNITY' if arb_a_profit_pct > 0 else 'NO_OPPORTUNITY'

        # Scenario B: buy ETF at ask, sell basket at bid (net of commission)
        arb_b_etf_ask_net    = etf_market_price * (1 + cost_factor)
        arb_b_basket_bid_net = fair_nav         * (1 - cost_factor)
        arb_b_profit_pct     = (arb_b_basket_bid_net - arb_b_etf_ask_net) / etf_market_price * 100
        arb_b_signal         = 'OPPORTUNITY' if arb_b_profit_pct > 0 else 'NO_OPPORTUNITY'

        return {
            'arb_a_etf_bid_net':    round(arb_a_etf_bid_net,    4),
            'arb_a_basket_ask_net': round(arb_a_basket_ask_net, 4),
            'arb_a_profit_pct':     round(arb_a_profit_pct,     6),
            'arb_a_signal':         arb_a_signal,
            'arb_b_etf_ask_net':    round(arb_b_etf_ask_net,    4),
            'arb_b_basket_bid_net': round(arb_b_basket_bid_net, 4),
            'arb_b_profit_pct':     round(arb_b_profit_pct,     6),
            'arb_b_signal':         arb_b_signal,
        }

    # ──────────────────────────────────────────────────────────────────────
    # Result assembly
    # ──────────────────────────────────────────────────────────────────────

    def _build_result_dict(self, etf_ticker, composition_date, official_nav,
                           shares_outstanding, fair_nav_primary,
                           fair_nav_weight_based, etf_market_price,
                           premium_discount_pct, coverage_pct, uncovered_weight,
                           total_components, priced_components,
                           unpriced_components, unpriced_tickers, skipped_components,
                           quality_flag, market_open, currency_warning,
                           arb_metrics):
        """
        Assemble the final result dictionary with all output fields in a
        consistent structure. Called exclusively by calculate_fair_nav().

        All monetary values are rounded to 4 decimal places.
        Percentage values are rounded to 4–6 decimal places for precision.
        Coverage percentages are stored as 0–100 values (not 0–1 decimals).

        :return: Dict with all result fields ready for DB insertion and reporting.
        """
        calculation_timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        def _round(value, ndigits=4):
            return round(value, ndigits) if value is not None else None

        result = {
            # Identity
            'etf_ticker':            etf_ticker,
            'composition_date':      composition_date,
            'calculation_timestamp': calculation_timestamp,

            # Fund-level inputs from DB (T-1)
            'official_nav':        official_nav,
            'shares_outstanding':  shares_outstanding,

            # Calculated NAV
            'fair_nav_primary':       _round(fair_nav_primary),
            'fair_nav_weight_based':  _round(fair_nav_weight_based),

            # ETF market price & premium/discount
            'etf_market_price':       _round(etf_market_price),
            'premium_discount_pct':   _round(premium_discount_pct, 6),

            # Coverage metrics (stored as 0–100 percentages)
            'covered_weight_pct':   _round(coverage_pct * 100,      4),
            'uncovered_weight_pct': _round(uncovered_weight * 100,   4),
            'total_components':     total_components,
            'priced_components':    priced_components,
            'unpriced_components':  unpriced_components,
            'unpriced_tickers':     unpriced_tickers,
            'skipped_components':   skipped_components,
            'quality_flag':         quality_flag,
            'market_open':          1 if market_open else 0,

            # Warnings
            'currency_warning': currency_warning,
        }

        # Merge arbitrage metrics dict into result
        result.update(arb_metrics)

        return result


# ──────────────────────────────────────────────────────────────────────────────
# Quick smoke-test — run directly to verify against SPY
# ──────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":

    conn = sqlite3.connect("data/etf_compositions.db")
    conn.row_factory = sqlite3.Row

    calc   = FairNavCalculator(conn)
    result = calc.calculate_fair_nav("SPY")

    if result:
        market_status = "OPEN (15-min delayed)" if result['market_open'] else "CLOSED (prior close)"

        print(f"\n{'='*64}")
        print(f"  {result['etf_ticker']}  |  Holdings: {result['composition_date']} (T-1)  |  Market: {market_status}")
        print(f"  Calculated: {result['calculation_timestamp']}")
        print(f"{'='*64}")

        print(f"\n  NAV")
        print(f"    Official (T-1):      ${result['official_nav']:.4f}")
        if result['fair_nav_primary']:
            print(f"    Fair (primary):      ${result['fair_nav_primary']:.4f}   ← shares-based")
        else:
            print(f"    Fair (primary):      N/A  (insufficient coverage)")
        if result['fair_nav_weight_based']:
            delta = result['fair_nav_weight_based'] - result['fair_nav_primary']
            print(f"    Fair (weight check): ${result['fair_nav_weight_based']:.4f}   [delta: {delta:+.4f}]")
        if result['etf_market_price']:
            direction = "PREMIUM" if result['premium_discount_pct'] > 0 else "DISCOUNT"
            print(f"    ETF market price:    ${result['etf_market_price']:.4f}")
            print(f"    Premium/Discount:    {result['premium_discount_pct']:+.4f}%  [{direction}]")

        print(f"\n  Coverage: {result['priced_components']}/{result['total_components']} "
              f"components priced  ({result['covered_weight_pct']:.2f}% by weight)  "
              f"[{result['quality_flag']}]")
        print(f"    Unpriced (no yfinance data): {result['unpriced_components']}")
        print(f"    Skipped  (non-tradeable):    {result['skipped_components']}")

        print(f"\n  Arb Signals  (spread=0.05%, commission=0.03%/leg)")
        print(f"    Scenario A — Sell ETF, buy basket (creation):")
        if result['arb_a_profit_pct'] is not None:
            print(f"      ETF bid net:     ${result['arb_a_etf_bid_net']:.4f}")
            print(f"      Basket ask net:  ${result['arb_a_basket_ask_net']:.4f}")
            print(f"      Profit:          {result['arb_a_profit_pct']:+.6f}%  →  {result['arb_a_signal']}")
        else:
            print(f"      {result['arb_a_signal']}")

        print(f"    Scenario B — Buy ETF, sell basket (redemption):")
        if result['arb_b_profit_pct'] is not None:
            print(f"      ETF ask net:     ${result['arb_b_etf_ask_net']:.4f}")
            print(f"      Basket bid net:  ${result['arb_b_basket_bid_net']:.4f}")
            print(f"      Profit:          {result['arb_b_profit_pct']:+.6f}%  →  {result['arb_b_signal']}")
        else:
            print(f"      {result['arb_b_signal']}")

        if result['currency_warning']:
            print(f"\n  WARNING: {result['currency_warning']}")

        print(f"\n  NOTE: Creation/redemption arb requires AP status (~50,000 share")
        print(f"        minimum unit for SPY). For monitoring/analysis only.")
        print(f"{'='*64}\n")

    conn.close()
