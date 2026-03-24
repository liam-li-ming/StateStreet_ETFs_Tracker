import math
from fastapi import APIRouter, Query
from backend.database import get_db
from backend.schemas.alerts import AlertItem, AlertsResponse
from backend.routers.compositions import populate_changes_cache

router = APIRouter(prefix="/api/alerts", tags=["alerts"])


def _ensure_all_changes_cached(conn):
    """Populate changes cache for all ETFs and all consecutive date pairs."""
    tickers = [r[0] for r in conn.execute(
        "SELECT DISTINCT etf_ticker FROM equity_etf_compositions"
    ).fetchall()]
    for ticker in tickers:
        dates = [r[0] for r in conn.execute(
            "SELECT DISTINCT composition_date FROM equity_etf_compositions "
            "WHERE etf_ticker=? ORDER BY composition_date ASC",
            (ticker,),
        ).fetchall()]
        for i in range(len(dates) - 1):
            populate_changes_cache(conn, ticker, dates[i], dates[i + 1])


@router.get("", response_model=AlertsResponse)
def get_alerts(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    etf_ticker: str = Query(default="", description="Filter by ETF ticker"),
    change_type: str = Query(default="", description="Filter: added | removed | weight_change"),
):
    with get_db() as conn:
        _ensure_all_changes_cached(conn)

        filters = []
        params: list = []

        if etf_ticker:
            filters.append("etf_ticker = ?")
            params.append(etf_ticker.upper())
        if change_type:
            filters.append("change_type = ?")
            params.append(change_type)

        where = ("WHERE " + " AND ".join(filters)) if filters else ""

        total = conn.execute(
            f"SELECT COUNT(*) FROM etf_composition_changes {where}", params
        ).fetchone()[0]

        offset = (page - 1) * page_size
        rows = conn.execute(
            f"SELECT etf_ticker, date_from, date_to, change_type, component_identifier, "
            f"component_ticker, component_name, component_sector, "
            f"weight_old, weight_new, weight_delta, shares_old, shares_new, detected_at "
            f"FROM etf_composition_changes {where} "
            f"ORDER BY date_to DESC, etf_ticker, change_type "
            f"LIMIT ? OFFSET ?",
            params + [page_size, offset],
        ).fetchall()

    return AlertsResponse(
        alerts=[AlertItem(**dict(r)) for r in rows],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=math.ceil(total / page_size) if total > 0 else 1,
    )
