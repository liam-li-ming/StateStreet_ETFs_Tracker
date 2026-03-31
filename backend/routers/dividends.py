import math
from fastapi import APIRouter, Query
from backend.database import get_db
from backend.schemas.dividends import DividendItem, DividendsResponse

router = APIRouter(prefix="/api/dividends", tags=["dividends"])


@router.get("", response_model=DividendsResponse)
def get_dividends(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    etf_ticker: str = Query(default="", description="Filter by ETF ticker"),
):
    with get_db() as conn:
        filters = []
        params: list = []

        if etf_ticker:
            filters.append("etf_ticker = ?")
            params.append(etf_ticker.upper())

        where = ("WHERE " + " AND ".join(filters)) if filters else ""

        total = conn.execute(
            f"SELECT COUNT(*) FROM etf_dividends {where}", params
        ).fetchone()[0]

        offset = (page - 1) * page_size
        rows = conn.execute(
            f"SELECT etf_ticker, ex_date, dividend_amount, currency "
            f"FROM etf_dividends {where} "
            f"ORDER BY ex_date DESC, etf_ticker "
            f"LIMIT ? OFFSET ?",
            params + [page_size, offset],
        ).fetchall()

    return DividendsResponse(
        dividends=[DividendItem(**dict(r)) for r in rows],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=math.ceil(total / page_size) if total > 0 else 1,
    )
