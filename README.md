# StateStreet ETFs Tracker

A Python pipeline that scrapes, fetches, and stores daily holdings snapshots for State Street Global Advisors (SSGA) ETFs into a local SQLite database — then calculates fair NAV estimates and arbitrage signals for any tracked ETF on any stored date.

---

## Overview

Every trading day, SSGA publishes updated Excel files listing the holdings of each of their ETFs. This tracker automates:

1. **Discovery** — Scraping the SSGA fund finder page (with JavaScript rendering via Playwright) to get the live list of all available ETFs for a given asset class.
2. **Fetching** — Concurrently downloading the daily holdings `.xlsx` file for every discovered ETF directly from SSGA.
3. **Storage** — Batch-inserting validated holdings data into a local SQLite database, building a historical record over time.
4. **Fair NAV Calculation** — Pricing each holding via yfinance (open prices on the composition date) to compute a fair NAV estimate, compare against the ETF's market price, and surface creation/redemption arbitrage signals.

---

## Project Structure

```
StateStreet_ETFs_Tracker/
├── main.py                          # Entry point — runs the full pipeline end-to-end
├── fair_nav_calculator.py           # FairNavCalculator class — NAV computation engine
├── run_arb_monitor.py               # Orchestrator for fair NAV runs + arb report printer
├── arb_monitor_db.py                # SQLite manager for etf_nav_estimates results table
├── requirements.txt
├── data/
│   └── etf_compositions.db          # SQLite database (auto-created on first run)
├── InteractWithDB/
│   ├── retrievefromWEB_available_etfs.py   # Scrapes SSGA fund finder for ETF list
│   ├── retrievefromWEB_etf_composition.py  # Downloads & parses per-ETF holdings Excel
│   ├── insertintoDB_equity_etf_compositions.py  # DB manager + concurrent fetch orchestrator
│   ├── queryfromDB_etf_composition.py      # DB query helper + Excel export
│   └── useful_functions.py                 # Date utility helpers
└── ETF Composition DB/              # Excel exports from queryfromDB (auto-created)
```

---

## Modules

### `main.py` — Entry Point

Runs the full pipeline in sequence:

1. Fetches and stores all SSGA equity ETF compositions into the DB.
2. Prompts the user to optionally calculate fair NAV.
3. Shows available composition dates for the chosen ETF ticker, then runs the arb monitor for the selected date.

```
python main.py
```

---

### `InteractWithDB/` — Data Acquisition & Storage

**`retrievefromWEB_available_etfs.py`** — `GetAvailableEtfs`

Scrapes the SSGA fund finder page using headless Chromium (Playwright) to get the live list of ETFs. Plain HTTP requests do not work — Playwright is required because the page is a JavaScript SPA.

**`retrievefromWEB_etf_composition.py`** — `GetEtfComposition`

Downloads the daily holdings Excel file for a given ETF ticker from SSGA's CDN. Parses the holdings table, cross-checks the holdings date with the NAV history file, and returns a merged DataFrame. The Excel file is downloaded once into memory and read twice (metadata + holdings rows) without a second HTTP request.

**`insertintoDB_equity_etf_compositions.py`** — `EquityEtfCompositionDb` + `fetch_and_store_all_etfs`

SQLite database manager and top-level orchestration function. Key behaviors:
- Uses a `ThreadPoolExecutor` (up to 100 workers) to fetch all ETF compositions concurrently — network I/O is the bottleneck.
- All DB writes happen on the main thread after all fetches complete.
- Uses a pre-built in-memory set of already-stored tickers for O(1) duplicate checks, avoiding per-ticker DB queries.
- Single `COMMIT` after all inserts for performance.
- `INSERT OR IGNORE` prevents duplicate records on re-runs.

**`queryfromDB_etf_composition.py`**

Query helper for reading compositions from the DB. Also exports any composition to a formatted two-sheet Excel workbook (Holdings + Sector Summary).

---

### `fair_nav_calculator.py` — `FairNavCalculator`

Core NAV computation engine. For a given ETF ticker and composition date:

1. Loads the holdings snapshot from the DB for that date.
2. Normalizes component tickers to Yahoo Finance format (handles CUSIP placeholders, share class periods, cash rows, etc.).
3. Fetches **open prices on the composition date** from yfinance for all priceable components. USD cash rows (`-` ticker, "US DOLLAR" name) are priced at $1.00/unit without a yfinance call.
4. Computes a **primary fair NAV** (shares-based): `Σ(component_shares × price) / shares_outstanding`.
5. Computes a **weight-based cross-check NAV**: `official_nav × Σ(w_i × open_i / prev_close_i)`.
6. Fetches the ETF's own market open price for the same date and computes premium/discount.
7. Reports coverage quality (HIGH ≥ 95%, LOW_CONFIDENCE 80–95%, INSUFFICIENT < 80%).

**Date alignment:** Both the holdings and all prices (component open prices + ETF market price) refer to the same user-selected composition date, so the fair NAV reflects that specific day.

**Interactive use:**
```
python fair_nav_calculator.py
```
Prompts for ETF ticker → shows up to 10 available dates → prompts for date → prints results.

---

### `run_arb_monitor.py` — Arb Monitor

Orchestrates fair NAV runs for one or more tickers on a chosen composition date, prints a formatted report, and optionally stores results to `etf_nav_estimates`.

**Arbitrage signals** model creation and redemption arb after simulated bid/ask spread (0.05%) and commission (0.03% per leg):

- **Scenario A** — Sell ETF at premium, buy basket (creation arb)
- **Scenario B** — Buy ETF at discount, sell basket (redemption arb)

Breakeven threshold ≈ 0.055% per direction.

**Interactive use:**
```
python run_arb_monitor.py
```
Same prompts as `fair_nav_calculator.py`.

---

### `arb_monitor_db.py` — `ArbMonitorDb`

Manages the `etf_nav_estimates` table in the same SQLite database. Stores each calculator run as a row for historical tracking. No unique constraint — multiple runs on the same date are kept as separate rows.

---

## Database Schema

**`equity_etf_info`** — ETF metadata (upserted on every pipeline run)

| Column | Description |
|---|---|
| `ticker` (PK) | ETF ticker |
| `name` | Full fund name |
| `domicile` | Fund domicile |
| `gross_expense_ratio` | Annual expense ratio |
| `aum` | Assets under management |
| `last_updated` | Last upsert timestamp |

**`equity_etf_compositions`** — Daily holdings snapshots

| Column | Description |
|---|---|
| `etf_ticker` (FK) | Parent ETF |
| `composition_date` | Holdings as-of date (YYYY-MM-DD) |
| `nav` | ETF NAV on that date |
| `shares_outstanding` | Shares outstanding |
| `total_net_assets` | Total net assets (USD) |
| `component_name / ticker / identifier / sedol` | Security identifiers |
| `component_weight` | Portfolio weight (percentage, e.g. 7.78 = 7.78%) |
| `component_sector` | GICS sector |
| `component_shares` | Shares held |
| `component_currency` | Local currency |

Unique constraint: `(etf_ticker, composition_date, component_identifier)` — prevents duplicates on re-runs.

**`etf_nav_estimates`** — Fair NAV calculation results

Stores fair NAV, market price, premium/discount, coverage metrics, and arb signals for each calculator run.

---

## Installation

```bash
git clone https://github.com/your-username/StateStreet_ETFs_Tracker.git
cd StateStreet_ETFs_Tracker
python -m venv venv
source venv/bin/activate       # macOS/Linux
pip install -r requirements.txt
playwright install chromium
mkdir -p data
```

---

## Usage

### Full pipeline (fetch + NAV calculation)

```bash
python main.py
```

Fetches today's compositions for all SSGA equity ETFs, then optionally prompts for a fair NAV calculation run.

### Fair NAV only (interactive)

```bash
python run_arb_monitor.py
# or
python fair_nav_calculator.py
```

### Query the database / export to Excel

```bash
python InteractWithDB/queryfromDB_etf_composition.py
```

---

## Limitations

- **T-1 holdings** — SSGA publishes the previous day's holdings. Results degrade around index rebalance dates.
- **Open prices** — Fair NAV uses open prices on the composition date. Intraday fair value requires real-time price feeds.
- **No FX conversion** — Non-USD components are priced in their local currency without FX adjustment. Fair NAV for international ETFs may be inaccurate.
