from fastapi import APIRouter, Query, HTTPException
from backend.database import get_db
from backend.schemas.alerts import SearchResultItem, SearchResponse

router = APIRouter(prefix="/api/search", tags=["search"])


@router.get("", response_model=SearchResponse)
def search_by_component(
    component: str = Query(..., min_length=1, description="Component ticker symbol, e.g. NVDA"),
):
    component = component.upper().strip()

    with get_db() as conn:
        # Search latest composition date per ETF for the given component ticker
        rows = conn.execute(
            """
            SELECT c.etf_ticker, i.name AS etf_name, c.composition_date,
                   c.component_name, c.component_identifier,
                   c.component_weight, c.component_sector, c.component_shares
            FROM equity_etf_compositions c
            JOIN equity_etf_info i ON i.ticker = c.etf_ticker
            WHERE c.component_ticker = ?
              AND c.composition_date = (
                  SELECT MAX(composition_date)
                  FROM equity_etf_compositions
                  WHERE etf_ticker = c.etf_ticker
              )
            ORDER BY c.component_weight DESC
            """,
            (component,),
        ).fetchall()

    if not rows:
        # Try case-insensitive partial match as a fallback
        with get_db() as conn:
            rows = conn.execute(
                """
                SELECT c.etf_ticker, i.name AS etf_name, c.composition_date,
                       c.component_name, c.component_identifier,
                       c.component_weight, c.component_sector, c.component_shares
                FROM equity_etf_compositions c
                JOIN equity_etf_info i ON i.ticker = c.etf_ticker
                WHERE c.component_ticker LIKE ?
                  AND c.composition_date = (
                      SELECT MAX(composition_date)
                      FROM equity_etf_compositions
                      WHERE etf_ticker = c.etf_ticker
                  )
                ORDER BY c.component_weight DESC
                """,
                (f"%{component}%",),
            ).fetchall()

    results = [SearchResultItem(**dict(r)) for r in rows]
    return SearchResponse(
        component_ticker=component,
        found_in=results,
        total_etfs=len(results),
    )
