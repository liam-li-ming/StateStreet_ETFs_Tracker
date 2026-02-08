# State Street ETFs Tracker

A data pipeline that scrapes, stores, and analyzes daily holdings for **State Street (SPDR) equity ETFs**. It builds a local SQLite database of ETF compositions and uses live stock prices (plus cash and FX rates) to detect arbitrage opportunities by comparing ETF market prices against calculated fair NAV.

## Architecture

```
SSGA Fund Finder               SSGA Excel Files              Yahoo Finance
(JS-rendered HTML)              (holdings + NAV history)      (live prices)
       |                               |                          |
       v                               v                          v
 GetAvailableEtfs            GetEtfComposition             DetectEtfArbitrage
       |                               |                          |
       v                               v                          v
  ETF metadata                Holdings + NAV data         Fair NAV vs Market Price
       |                               |                          |
       +---------------+---------------+                          |
                       |                                          |
                       v                                          |
              SQLite Database  <-----------------------------------+
         (etf_compositions.db)
```

## Data Pipeline

### Step 1: Fetch and Store ETF Compositions

Run `main.py` to scrape all equity ETFs from the SSGA website and store their daily holdings in the database:

```bash
python main.py
```

This will:
1. Scrape the SSGA fund finder page for all available equity ETFs
2. Download two Excel files per ETF from SSGA (daily holdings + NAV history)
3. Parse and merge holdings data with fund-level NAV metrics
4. Store everything in `data/etf_compositions.db`
5. Skip ETFs already stored for the current date

### Step 2: Detect Arbitrage Opportunities

Run `detect_etf_arbitrage.py` to compare ETF market prices against fair NAV calculated from component stock prices:

```bash
python detect_etf_arbitrage.py
```

This will:
1. Load the latest composition for each ETF from the database
2. Classify each component as stock, cash/currency, or unpriceable
3. Fetch live stock prices via yfinance and FX rates for foreign cash positions
4. Calculate fair NAV: `(Stock Value + Cash Value) / Shares Outstanding`
5. Compare to the ETF's current market price
6. Flag deviations as PREMIUM, DISCOUNT, or FAIR with an arbitrage action

**Example output:**
```
ETF Arbitrage Analysis: SPY
============================================================
  Components:         502/503 priced (501 stocks, 1 cash)
  Portfolio Coverage:  99.93%

  Portfolio Breakdown:
    Stock Value:      $631,234,567,890.12
    Cash Value:       $1,234,567,890.00
    Total Value:      $632,469,135,780.12

  Market Price:       $690.6200
  Calculated NAV:     $687.0275
  Reported NAV:       $686.068797
  Shares Outstanding: 920,560,000

  Premium/Discount:   +0.5229%
  Signal:             PREMIUM
  Arbitrage Action:   SELL ETF / BUY BASKET (creation arbitrage)
  Est. Profit/Share:  $3.5925
```

## Project Structure

```
StateStreet_ETFs_Tracker/
|-- main.py                              # Entry point - runs the full data pipeline
|-- get_available_etfs.py                # Scrapes SSGA fund finder for ETF list
|-- get_etf_composition.py               # Downloads and parses ETF holdings + NAV Excel files
|-- store_equity_etf_compositions_db.py  # SQLite database manager (tables, inserts, queries)
|-- detect_etf_arbitrage.py              # Arbitrage detection - fair NAV vs market price
|-- useful_functions.py                  # Date utility helpers
|-- requirements.txt                     # Python dependencies
|-- data/
|   +-- etf_compositions.db             # SQLite database (created on first run)
```

## Database Schema

### Table: `equity_etf_info`

Stores ETF metadata (one row per ETF).

| Column               | Type | Description                    |
|----------------------|------|--------------------------------|
| ticker               | TEXT | Primary key (e.g. SPY)         |
| name                 | TEXT | ETF full name                  |
| domicile             | TEXT | Fund domicile                  |
| gross_expense_ratio  | TEXT | Expense ratio                  |
| nav                  | TEXT | NAV from fund finder page      |
| aum                  | TEXT | Assets under management        |
| last_updated         | TEXT | Last upsert timestamp          |

### Table: `equity_etf_compositions`

Stores daily holdings snapshots (one row per ETF x date x component).

| Column                | Type    | Description                              |
|-----------------------|---------|------------------------------------------|
| id                    | INTEGER | Auto-increment primary key               |
| etf_ticker            | TEXT    | FK to equity_etf_info.ticker             |
| nav                   | REAL    | Net asset value per ETF share            |
| shares_outstanding    | REAL    | Total ETF shares issued                  |
| total_net_assets      | REAL    | AUM = NAV x shares_outstanding           |
| composition_date      | TEXT    | Date of the snapshot (YYYY-MM-DD)        |
| component_name        | TEXT    | Holding name (e.g. APPLE INC)            |
| component_ticker      | TEXT    | Holding ticker (e.g. AAPL)               |
| component_identifier  | TEXT    | CUSIP or other identifier                |
| component_sedol       | TEXT    | SEDOL identifier                         |
| component_weight      | REAL    | Portfolio weight (%)                     |
| component_sector      | TEXT    | Sector classification                    |
| component_shares      | REAL    | Number of shares held by the ETF         |
| component_currency    | TEXT    | Currency (e.g. USD)                      |
| created_at            | TEXT    | Record insertion timestamp               |

**Unique constraint:** `(etf_ticker, composition_date, component_identifier)`

## Modules

### `GetAvailableEtfs`

Scrapes the SSGA fund finder using Playwright (headless Chromium) to handle JavaScript rendering. Parses the HTML table with BeautifulSoup.

| Method                          | Description                                                 |
|---------------------------------|-------------------------------------------------------------|
| `asset_class_select(class)`     | Builds a filtered URL for an asset class                    |
| `fetch_url_content(url)`        | Fetches JS-rendered HTML via Playwright                     |
| `parse_etf_table(html)`         | Parses HTML into a DataFrame of ETFs                        |

### `GetEtfComposition`

Downloads two Excel files per ETF from SSGA and merges them into a single DataFrame.

| Method                                | Description                                            |
|---------------------------------------|--------------------------------------------------------|
| `fetch_etf_composition_to_df(ticker)` | Downloads holdings + NAV history, returns merged DataFrame |

**Data sources per ETF:**
- `holdings-daily-us-en-{ticker}.xlsx` - component holdings (name, ticker, weight, shares, sector)
- `navhist-us-en-{ticker}.xlsx` - NAV, shares outstanding, total net assets

### `EquityEtfCompositionDb`

SQLite database manager with CRUD operations and performance optimizations (WAL mode, batch inserts).

| Method                                   | Description                                      |
|------------------------------------------|--------------------------------------------------|
| `connect_db()` / `close_db()`           | Manage database connection                        |
| `create_tables()`                        | Create tables and indexes                         |
| `update_etf_info(df)`                    | Upsert ETF metadata                              |
| `insert_composition(df)`                 | Batch insert holdings (skips duplicates)          |
| `get_available_tickers()`                | List all ETF tickers                              |
| `get_composition(ticker, date)`          | Get holdings for a specific ETF and date          |
| `get_latest_composition(ticker)`         | Get most recent holdings for an ETF               |
| `get_composition_dates(ticker)`          | List available dates for an ETF                   |
| `composition_exists(ticker, date)`       | Check if data exists (for skip logic)             |
| `get_stats()`                            | Database summary statistics                       |
| `purge_old_compositions(days)`           | Delete old records and VACUUM (default: 5 years)  |

### `fetch_and_store_all_etfs(db)`

Orchestrator function that ties everything together. Fetches ETF list, downloads compositions concurrently (up to 500 threads), and stores to the database from the main thread.

### `DetectEtfArbitrage`

Calculates fair ETF NAV from live component prices (stocks + cash positions) and compares to market price to identify arbitrage opportunities.

| Method                            | Description                                               |
|-----------------------------------|-----------------------------------------------------------|
| `fetch_prices(tickers)`           | Batch-fetch prices via yfinance with caching              |
| `analyze_etf(ticker)`             | Analyze single ETF: fair NAV vs market price              |
| `scan_all_etfs(threshold_pct)`    | Scan all ETFs, return sorted DataFrame of opportunities   |
| `format_result(result)`           | Format detailed analysis for console output               |

**Cash handling:**

Cash and currency positions are identified by component name (exact match against 30+ currencies, plus partial matching for terms like "CASH COLLATERAL", "MONEY MARKET", "TREASURY BILL"). USD-denominated cash is valued at $1 per unit. Foreign currencies are converted to USD using live FX rates from Yahoo Finance.

**Fair NAV formula:**
```
Stock Value = SUM(stock_shares_i x stock_price_i)
Cash Value  = SUM(cash_amount_j x fx_rate_j)
Fair NAV    = (Stock Value + Cash Value) / Shares Outstanding
Premium/Discount % = (market_price - fair_nav) / fair_nav x 100
```

**Signal classification and arbitrage strategy:**

ETF arbitrage works through the **creation/redemption mechanism** used by Authorized Participants (APs):

| Signal     | Condition   | Arbitrage Action                                                   |
|------------|-------------|--------------------------------------------------------------------|
| `PREMIUM`  | > +0.1%     | **Sell ETF / Buy Basket** — APs buy underlying stocks, deliver to issuer to create new ETF shares, sell ETF at the higher market price (creation arbitrage) |
| `DISCOUNT` | < -0.1%     | **Buy ETF / Sell Basket** — APs buy ETF at the lower market price, redeem with issuer for underlying stocks, sell components at their higher individual prices (redemption arbitrage) |
| `FAIR`     | within 0.1% | **No Action** — no significant deviation                           |

## Setup

### 1. Create a Conda Environment

```bash
# Create a new conda environment with Python 3.11
conda create -n etf_tracker python=3.11 -y

# Activate the environment
conda activate etf_tracker
```

### 2. Install Dependencies

```bash
# Install Python packages
pip install -r requirements.txt

# Install Chromium browser for Playwright (required for web scraping)
playwright install chromium
```

### 3. Run the Project

```bash
# Step 1: Fetch and store all ETF compositions into the database
python main.py

# Step 2: Detect arbitrage opportunities using live prices
python detect_etf_arbitrage.py
```

### Deactivate / Remove Environment

```bash
# Deactivate when done
conda deactivate

# Remove the environment entirely (optional)
conda remove -n etf_tracker --all -y
```

## Usage

```python
from store_equity_etf_compositions_db import EquityEtfCompositionDb
from detect_etf_arbitrage import DetectEtfArbitrage

db = EquityEtfCompositionDb(db_path="data/etf_compositions.db")

try:
    db.connect_db()

    # Query stored compositions
    composition = db.get_latest_composition("SPY")

    # Detect arbitrage on a single ETF
    detector = DetectEtfArbitrage(db)
    result = detector.analyze_etf("SPY")
    print(detector.format_result(result))

    # Scan all ETFs for opportunities
    summary = detector.scan_all_etfs(threshold_pct=0.5)

finally:
    db.close_db()
```

## Data Sources

- **ETF list:** [SSGA Fund Finder](https://www.ssga.com/us/en/intermediary/fund-finder)
- **Holdings data:** SSGA daily holdings Excel files
- **NAV history:** SSGA NAV history Excel files
- **Live prices:** Yahoo Finance via [yfinance](https://github.com/ranaroussi/yfinance)

## Limitations

- Holdings data from SSGA has a ~1 day lag (published after market close)
- yfinance provides delayed/closing prices, not real-time
- Cash positions are priced at $1/unit (USD) or via FX rates (foreign currencies); some exotic cash instruments may not be recognized
- Some components cannot be priced: futures contracts and ticker format mismatches (coverage is typically 99%+ for large equity ETFs)
- Non-USD denominated holdings in international ETFs may have lower pricing coverage
- Arbitrage signals do not account for transaction costs, bid-ask spreads, or creation/redemption fees — real-world profitability requires APs to factor in these costs

## Acknowledgements

This project was built with the support of [Claude](https://claude.ai) by Anthropic.
