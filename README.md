# SSGA Equity ETF Tracker

A full-stack web application that scrapes, stores, and visualises daily holdings snapshots for State Street Global Advisors (SSGA) equity ETFs — surfacing rebalancing events, share count changes, and cross-ETF exposure in a browser UI.

---

## Branch structure

| Branch | Purpose |
|--------|---------|
| `main` | ETF tracker — data pipeline + FastAPI backend + React web app |

---

## Overview

Every trading day, SSGA publishes updated Excel files listing the holdings of each ETF. This tracker automates:

1. **Discovery** — Scraping the SSGA fund finder page (JavaScript SPA, requires Playwright) to get the live list of all equity ETFs.
2. **Fetching** — Concurrently downloading the daily holdings `.xlsx` for every ETF directly from SSGA's CDN.
3. **Storage** — Batch-inserting validated holdings into a local SQLite database, building a historical record over time.
4. **Web UI** — A React frontend with a FastAPI backend to explore holdings, compare dates, and track rebalancing events.

---

## Architecture

### Data Pipeline (`InteractWithDB/` + `main.py`)

| File | Purpose |
|------|---------|
| `retrievefromWEB_available_etfs.py` | Scrapes the SSGA fund finder with headless Chromium (Playwright) — plain HTTP won't work |
| `retrievefromWEB_etf_composition.py` | Downloads and parses the per-ETF holdings `.xlsx` from SSGA's CDN |
| `insertintoDB_equity_etf_compositions.py` | DB manager + concurrent fetch orchestrator (`ThreadPoolExecutor`, up to 200 workers); skips tickers whose exact XLSX date is already in the DB |
| `queryfromDB_etf_composition.py` | Query helper; exports any composition to a formatted two-sheet Excel workbook |

### FastAPI Backend (`backend/`)

| File | Purpose |
|------|---------|
| `backend/main.py` | FastAPI app, CORS, lifespan startup |
| `backend/config.py` | `DB_PATH` (absolute, resolved from `__file__`), CORS origins |
| `backend/database.py` | `get_db()` context manager; creates `etf_composition_changes` table on startup |
| `backend/routers/etfs.py` | `GET /api/etfs`, `/api/etfs/{ticker}`, `/api/etfs/{ticker}/dates` |
| `backend/routers/compositions.py` | `/compositions/{date}`, `/compare`, `/changes`, `/compositions/{date}/download`; populates change cache |
| `backend/routers/alerts.py` | `GET /api/alerts` — paginated global feed of changes across all ETFs |
| `backend/routers/search.py` | `GET /api/search?component=NVDA` — which ETFs hold a given ticker |
| `backend/routers/pipeline.py` | `POST /api/pipeline/refresh` (BackgroundTask), `GET /api/pipeline/status` |

### React Frontend (`frontend/`)

Vite + React 18 + TypeScript + Tailwind CSS + Recharts + TanStack Table + TanStack Query.

| Page | Route | Description |
|------|-------|-------------|
| ETF Directory | `/` | Sortable/searchable table of all tracked ETFs |
| ETF Detail | `/etfs/:ticker` | Holdings table + sector pie chart + top-10 bar chart |
| Composition History | `/etfs/:ticker/history` | Date pickers + color-coded diff (added/removed/share changes) |
| Rebalancing Alerts | `/alerts` | Paginated global feed of component changes across all ETFs |
| Cross-ETF Search | `/search` | "Which ETFs hold NVDA?" search |
| Download | `/download` | Export ETF composition + metadata as XLSX, CSV, or JSON |

Date inputs on ETF Detail and Composition History use a custom `DatePickerCalendar` component: a text input (YYYY-MM-DD) with a calendar popup that highlights only the dates for which data exists. Non-available dates are greyed out and non-selectable.

---

## Database Schema

**`equity_etf_info`** — ETF metadata (upserted on every pipeline run)

| Column | Description |
|--------|-------------|
| `ticker` (PK) | ETF ticker |
| `name` | Full fund name |
| `domicile` | Fund domicile |
| `gross_expense_ratio` | Annual expense ratio |
| `aum` | Assets under management |
| `last_updated` | Last upsert timestamp |

**`equity_etf_compositions`** — Daily holdings snapshots

| Column | Description |
|--------|-------------|
| `etf_ticker` (FK) | Parent ETF |
| `composition_date` | Holdings as-of date (YYYY-MM-DD) |
| `nav` | ETF NAV on that date |
| `shares_outstanding` | Shares outstanding |
| `total_net_assets` | Total net assets (USD) |
| `component_name / ticker / identifier / sedol` | Security identifiers |
| `component_weight` | Portfolio weight as a percentage (e.g. 7.78 = 7.78%) |
| `component_sector` | GICS sector |
| `component_shares` | Shares held by the ETF |
| `component_currency` | Local currency |

Unique constraint: `(etf_ticker, composition_date, component_identifier)`

**`etf_composition_changes`** — Materialized cache of component changes between consecutive dates

Populated lazily on first `/api/alerts` or `/api/etfs/{ticker}/changes` request. A "share change" event is recorded when the ETF's share count for a component actually changes (additions, removals, and share count changes). Weight drift from price movements alone is not recorded.

| Column | Description |
|--------|-------------|
| `change_type` | `added` / `removed` / `weight_change` |
| `date_from` / `date_to` | The two consecutive snapshot dates |
| `shares_old` / `shares_new` | Share counts before and after |
| `weight_old` / `weight_new` / `weight_delta` | Weight percentages before and after |

---

## Installation

```bash
git clone https://github.com/your-username/StateStreet_ETFs_Tracker.git
cd StateStreet_ETFs_Tracker

# Python dependencies
python -m venv venv
source venv/bin/activate       # macOS/Linux
pip install -r requirements.txt
playwright install chromium

# Node dependencies (requires Node.js)
cd frontend && npm install && cd ..
```

---

## Usage

### Fetch today's holdings (CLI)

```bash
python main.py
```

### Start the backend and frontend together

```bash
# Only needed if you use NVM to manage Node versions. Skip this if Node is already available (check with `node -v`).
source ~/.nvm/nvm.sh
cd frontend && npm run dev:all
```

This starts both servers concurrently with labeled output. Backend at `http://localhost:8002` (docs at `/docs`), frontend at `http://localhost:8003`.

### Start them separately

```bash
# Backend (run from project root)
uvicorn backend.main:app --reload --port 8002

# Frontend (in a separate terminal)
source ~/.nvm/nvm.sh
cd frontend && npm run dev
```

All `/api/*` requests are proxied to the backend automatically in development.

### Query the database / export to Excel (CLI)

```bash
python InteractWithDB/queryfromDB_etf_composition.py
```

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/etfs` | All ETFs, optional `?q=` filter |
| GET | `/api/etfs/{ticker}` | ETF metadata + latest holdings |
| GET | `/api/etfs/{ticker}/dates` | All stored composition dates |
| GET | `/api/etfs/{ticker}/compositions/{date}` | Full holdings for a date |
| GET | `/api/etfs/{ticker}/compositions/{date}/download` | Download composition as `?format=xlsx\|csv\|json` |
| GET | `/api/etfs/{ticker}/compare` | Diff between two dates |
| GET | `/api/etfs/{ticker}/changes` | Timeline of all consecutive-date changes |
| GET | `/api/alerts` | Global paginated feed of changes across all ETFs |
| GET | `/api/search` | `?component=NVDA` — ETFs holding that ticker |
| POST | `/api/pipeline/refresh` | Trigger a background holdings fetch |
| GET | `/api/pipeline/status` | `{running, last_run, last_error}` |

---

## Automated Pipeline (Cron)

The pipeline runs automatically six times every weekday via user crontab (UTC+8).
US markets close at 4 PM ET. During EDT (UTC-4) SSGA data lands around 05:00 UTC+8; during EST (UTC-5) it lands around 06:00 UTC+8 — one hour later. The extra runs at 21:20, 22:00, and 22:20 ensure holdings are captured year-round regardless of daylight saving time.

| Time (UTC+8) | Cron expression  |
|--------------|------------------|
| 20:00        | `0 20 * * 1-5`   |
| 20:30        | `30 20 * * 1-5`  |
| 21:00        | `0 21 * * 1-5`   |
| 21:20        | `20 21 * * 1-5`  |
| 22:00        | `0 22 * * 1-5`   |
| 22:20        | `20 22 * * 1-5`  |

Multiple runs are safe — `skip_existing=True` checks whether the exact `(ticker, composition_date)` from the downloaded XLSX already exists in the DB (14-day window). If it does, the ticker is skipped without a DB write. The composition date is sourced directly from the holdings-daily XLSX and cross-checked against the navhist XLSX; a date mismatch between the two files causes the ticker to be skipped.

Logs are written to `logs/pipeline.log`. See `cron_management.txt` for instructions on viewing and editing the schedule.

---

## Notes

- **T-1 holdings** — SSGA publishes the previous trading day's holdings.
- **`component_weight`** is stored as a 0–100 float (e.g. `7.7849` means 7.7849%). The API returns it as-is; the frontend appends `%` for display.
- **Change detection** uses share counts, not weight percentages. Weight can drift from price movements without any actual trade; only changes in `component_shares` are recorded as rebalancing events.
