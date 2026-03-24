# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Branch structure

- **`main`** — ETF tracker only (data pipeline + web app). No NAV/arb code.
- **`arb-monitor`** — Preserves the NAV/arbitrage calculation modules (`fair_nav_calculator.py`, `run_arb_monitor.py`, `arb_monitor_db.py`).

## Commands

```bash
# Install Python dependencies
pip install -r requirements.txt
playwright install chromium

# Fetch today's compositions for all SSGA equity ETFs (CLI)
# Must be run from the project root — uses relative path data/etf_compositions.db
python main.py

# Start FastAPI backend (run from project root)
uvicorn backend.main:app --reload --port 8002

# Query DB / export holdings to Excel (CLI)
python InteractWithDB/queryfromDB_etf_composition.py

# Frontend — development (requires Node.js via nvm)
source ~/.nvm/nvm.sh
cd frontend && npm install && npm run dev   # http://localhost:8003

# Frontend — production build
cd frontend && npm run build
```

No test suite exists in this project.

## Automated pipeline (cron)

Three runs every weekday via user crontab, at 20:00, 20:30, and 21:00 local time (UTC+8).
US markets close at 4 PM ET = 4 AM UTC+8, so these runs reliably catch the published data.
Logs append to `logs/pipeline.log`. See `cron_management.txt` for schedule management.

## Architecture

### Data Pipeline (`InteractWithDB/` + `main.py`)

1. **`retrievefromWEB_available_etfs.py` (`GetAvailableEtfs`)** — Scrapes the SSGA fund finder page using headless Chromium via Playwright (plain HTTP won't work; it's a JS SPA). Returns a DataFrame of all ETFs for a given asset class (`"equity"`, `"fixed-income"`, `"alternative"`, `"Multi-Asset"`).

2. **`retrievefromWEB_etf_composition.py` (`GetEtfComposition`)** — Downloads the daily holdings `.xlsx` from SSGA's CDN for one ticker. Parses metadata + holdings rows from the same in-memory file. Cross-checks the holdings date against the NAV history sheet — returns `None` on mismatch.

3. **`insertintoDB_equity_etf_compositions.py` (`EquityEtfCompositionDb` + `fetch_and_store_all_etfs`)** — Manages the SQLite DB and orchestrates concurrent fetching. Uses `ThreadPoolExecutor` (up to 100 workers), writes in a single transaction. O(1) duplicate skip via in-memory set.

### FastAPI Backend (`backend/`)

Run from project root so `InteractWithDB` package is importable: `uvicorn backend.main:app --reload --port 8002`

| File | Purpose |
|------|---------|
| `backend/main.py` | FastAPI app, CORS, lifespan startup |
| `backend/config.py` | `DB_PATH` (absolute, resolved from `__file__`), CORS origins |
| `backend/database.py` | `get_db()` context manager; creates `etf_composition_changes` table on startup; runs schema migrations on boot |
| `backend/routers/etfs.py` | `GET /api/etfs`, `/api/etfs/{ticker}`, `/api/etfs/{ticker}/dates` |
| `backend/routers/compositions.py` | `/compositions/{date}`, `/compare`, `/changes`; populates change cache |
| `backend/routers/alerts.py` | `GET /api/alerts` (paginated, filterable) |
| `backend/routers/search.py` | `GET /api/search?component=NVDA` |
| `backend/routers/pipeline.py` | `POST /api/pipeline/refresh` (BackgroundTask), `GET /api/pipeline/status` |
| `backend/schemas/` | Pydantic response models |

**CORS**: Dev origins hardcoded (`localhost:8003`). Production: set `ENV=production` and `ALLOWED_ORIGINS=https://...` env vars.

**Playwright + FastAPI**: `GetAvailableEtfs.fetch_url_content()` uses `sync_playwright()` — must always run in a plain Python function/thread, never in an async handler directly.

### React Frontend (`frontend/`)

Vite + React 18 + TypeScript + Tailwind CSS 3 + Recharts + TanStack Table + TanStack Query.

Vite proxy: all `/api/*` requests forwarded to `http://localhost:8002` in dev (see `vite.config.ts`).

| Page | Route | Description |
|------|-------|-------------|
| ETF Directory | `/` | Sortable/searchable table of all 104+ ETFs |
| ETF Detail | `/etfs/:ticker` | Holdings table + sector pie chart + top-10 bar chart |
| Composition History | `/etfs/:ticker/history` | Date pickers + color-coded diff (added/removed/share changes) |
| Rebalancing Alerts | `/alerts` | Paginated global feed of component changes across all ETFs |
| Cross-ETF Search | `/search` | "Which ETFs hold NVDA?" search |

### Database (`data/etf_compositions.db`)

SQLite with WAL mode. Four tables:
- `equity_etf_info` — ETF metadata (PK: `ticker`)
- `equity_etf_compositions` — Daily holdings; UNIQUE on `(etf_ticker, composition_date, component_identifier)`; `component_weight` stored as 0–100 float (e.g. 7.7849 = 7.7849%)
- `etf_nav_estimates` — Legacy NAV results (from `arb-monitor` branch; unused in main)
- `etf_composition_changes` — Materialized cache of component changes between consecutive dates; populated lazily on first `/changes` or `/alerts` request

### Key notes

- `component_weight` in DB is already a percentage (0–100), not a 0–1 decimal. The API returns it as-is; the frontend appends `%` for display.
- **Change detection uses `component_shares`, not weight.** Weight can drift from price movements without any actual trade. A `weight_change` event is only recorded when `shares_old != shares_new`. This logic lives in `_compute_changes_for_pair()` and `compare_compositions()` in `backend/routers/compositions.py`.
- The `etf_composition_changes` table has `shares_old` and `shares_new` columns added via `ALTER TABLE` migration in `backend/database.py` `init_db()`. Any stale `weight_change` rows where shares did not actually change are purged on startup.
- The `etf_composition_changes` table is computed on-demand and cached with `INSERT OR IGNORE`. It's populated when `/api/alerts` or `/api/etfs/{ticker}/changes` is first hit, and repopulated when the pipeline refresh runs.
- Large ETFs (e.g. EWX with 3,453 components): comparison queries use `LEFT JOIN` not `NOT IN` to avoid N-deep subqueries.
- `main.py` uses a relative DB path (`data/etf_compositions.db`) — always run it from the project root directory.
