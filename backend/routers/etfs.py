from fastapi import APIRouter, HTTPException, Query
from backend.database import get_db
from backend.schemas.etf import EtfInfo, EtfListResponse, EtfDatesResponse
from backend.schemas.composition import EtfDetailResponse, HoldingItem

router = APIRouter(prefix="/api/etfs", tags=["etfs"])

PAGE_SIZE = 50


@router.get("", response_model=EtfListResponse)
def list_etfs(q: str = Query(default="", description="Filter by ticker or name")):
    with get_db() as conn:
        if q:
            rows = conn.execute(
                "SELECT * FROM equity_etf_info WHERE ticker LIKE ? OR name LIKE ? ORDER BY ticker",
                (f"%{q.upper()}%", f"%{q}%"),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM equity_etf_info ORDER BY ticker"
            ).fetchall()
    etfs = [EtfInfo(**dict(r)) for r in rows]
    return EtfListResponse(etfs=etfs, total=len(etfs))


@router.get("/{ticker}", response_model=EtfDetailResponse)
def get_etf(ticker: str, limit: int = Query(default=PAGE_SIZE, ge=1, le=500)):
    ticker = ticker.upper()
    with get_db() as conn:
        info_row = conn.execute(
            "SELECT * FROM equity_etf_info WHERE ticker = ?", (ticker,)
        ).fetchone()
        if not info_row:
            raise HTTPException(status_code=404, detail=f"ETF '{ticker}' not found")

        dates = conn.execute(
            "SELECT DISTINCT composition_date FROM equity_etf_compositions "
            "WHERE etf_ticker = ? ORDER BY composition_date DESC",
            (ticker,),
        ).fetchall()
        date_list = [r["composition_date"] for r in dates]

        if not date_list:
            return EtfDetailResponse(**dict(info_row), available_dates=[], holdings_count=0)

        latest_date = date_list[0]
        total_count = conn.execute(
            "SELECT COUNT(*) FROM equity_etf_compositions WHERE etf_ticker = ? AND composition_date = ?",
            (ticker, latest_date),
        ).fetchone()[0]

        rows = conn.execute(
            "SELECT component_identifier, component_name, component_ticker, "
            "component_weight, component_sector, component_shares, component_currency, component_sedol "
            "FROM equity_etf_compositions "
            "WHERE etf_ticker = ? AND composition_date = ? "
            "ORDER BY component_weight DESC LIMIT ?",
            (ticker, latest_date, limit),
        ).fetchall()

    holdings = [HoldingItem(**dict(r)) for r in rows]
    return EtfDetailResponse(
        **dict(info_row),
        latest_composition_date=latest_date,
        available_dates=date_list,
        holdings_count=total_count,
        holdings=holdings,
        holdings_truncated=(total_count > limit),
    )


@router.get("/{ticker}/dates", response_model=EtfDatesResponse)
def get_etf_dates(ticker: str):
    ticker = ticker.upper()
    with get_db() as conn:
        info = conn.execute(
            "SELECT ticker FROM equity_etf_info WHERE ticker = ?", (ticker,)
        ).fetchone()
        if not info:
            raise HTTPException(status_code=404, detail=f"ETF '{ticker}' not found")
        rows = conn.execute(
            "SELECT DISTINCT composition_date FROM equity_etf_compositions "
            "WHERE etf_ticker = ? ORDER BY composition_date DESC",
            (ticker,),
        ).fetchall()
    return EtfDatesResponse(ticker=ticker, dates=[r["composition_date"] for r in rows])
