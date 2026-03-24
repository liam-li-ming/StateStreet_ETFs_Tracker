import sys
import os
from datetime import datetime
from fastapi import APIRouter, BackgroundTasks
from backend.config import DB_PATH, PROJECT_ROOT
from backend.routers.compositions import populate_changes_cache

# Ensure the project root is on sys.path so InteractWithDB can be imported
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

router = APIRouter(prefix="/api/pipeline", tags=["pipeline"])

pipeline_status: dict = {
    "running": False,
    "last_run": None,
    "last_error": None,
}


def _run_pipeline():
    """Synchronous pipeline function — runs in a BackgroundTask thread."""
    pipeline_status["running"] = True
    pipeline_status["last_error"] = None
    try:
        from InteractWithDB.insertintoDB_equity_etf_compositions import (
            EquityEtfCompositionDb,
            fetch_and_store_all_etfs,
        )
        import sqlite3

        db = EquityEtfCompositionDb(db_path=DB_PATH)
        db.connect_db()
        db.create_tables()

        fetch_and_store_all_etfs(db, asset_classes=["equity"], skip_existing=True)

        # After fetch, compute change cache for any new date pairs
        conn = db.conn
        tickers = [r[0] for r in conn.execute(
            "SELECT DISTINCT etf_ticker FROM equity_etf_compositions"
        ).fetchall()]
        conn.row_factory = sqlite3.Row
        for ticker in tickers:
            dates = [r["composition_date"] for r in conn.execute(
                "SELECT DISTINCT composition_date FROM equity_etf_compositions "
                "WHERE etf_ticker=? ORDER BY composition_date ASC",
                (ticker,),
            ).fetchall()]
            for i in range(len(dates) - 1):
                populate_changes_cache(conn, ticker, dates[i], dates[i + 1])

        db.close_db()
        pipeline_status["last_run"] = datetime.now().isoformat()
    except Exception as exc:
        pipeline_status["last_error"] = str(exc)
    finally:
        pipeline_status["running"] = False


@router.post("/refresh")
def trigger_refresh(background_tasks: BackgroundTasks):
    if pipeline_status["running"]:
        return {"status": "already_running", "message": "Pipeline already in progress"}
    background_tasks.add_task(_run_pipeline)
    return {"status": "started", "message": "Pipeline triggered in background"}


@router.get("/status")
def get_status():
    return pipeline_status
