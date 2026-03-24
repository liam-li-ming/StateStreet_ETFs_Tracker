from fastapi import APIRouter, HTTPException, Query
from backend.database import get_db
from backend.schemas.composition import CompositionResponse, HoldingItem
from backend.schemas.comparison import (
    CompareResponse, CompareSummary,
    AddedComponent, RemovedComponent, WeightChange,
    ChangesResponse, ChangeEvent,
)

router = APIRouter(prefix="/api/etfs", tags=["compositions"])

PAGE_SIZE = 100


@router.get("/{ticker}/compositions/{date}", response_model=CompositionResponse)
def get_composition(
    ticker: str,
    date: str,
    limit: int = Query(default=PAGE_SIZE, ge=1, le=5000),
    offset: int = Query(default=0, ge=0),
):
    ticker = ticker.upper()
    with get_db() as conn:
        meta = conn.execute(
            "SELECT nav, shares_outstanding, total_net_assets "
            "FROM equity_etf_compositions WHERE etf_ticker=? AND composition_date=? LIMIT 1",
            (ticker, date),
        ).fetchone()
        if not meta:
            raise HTTPException(status_code=404, detail=f"No composition for {ticker} on {date}")

        total_count = conn.execute(
            "SELECT COUNT(*) FROM equity_etf_compositions WHERE etf_ticker=? AND composition_date=?",
            (ticker, date),
        ).fetchone()[0]

        rows = conn.execute(
            "SELECT component_identifier, component_name, component_ticker, "
            "component_weight, component_sector, component_shares, component_currency, component_sedol "
            "FROM equity_etf_compositions WHERE etf_ticker=? AND composition_date=? "
            "ORDER BY component_weight DESC LIMIT ? OFFSET ?",
            (ticker, date, limit, offset),
        ).fetchall()

    return CompositionResponse(
        ticker=ticker,
        composition_date=date,
        nav=meta["nav"],
        shares_outstanding=meta["shares_outstanding"],
        total_net_assets=meta["total_net_assets"],
        holdings_count=total_count,
        holdings=[HoldingItem(**dict(r)) for r in rows],
        holdings_truncated=(offset + limit < total_count),
    )


@router.get("/{ticker}/compare", response_model=CompareResponse)
def compare_compositions(
    ticker: str,
    date1: str = Query(..., description="Earlier date YYYY-MM-DD"),
    date2: str = Query(..., description="Later date YYYY-MM-DD"),
):
    ticker = ticker.upper()
    if date1 == date2:
        raise HTTPException(status_code=400, detail="date1 and date2 must be different")

    with get_db() as conn:
        # Validate both dates exist
        for d in (date1, date2):
            exists = conn.execute(
                "SELECT 1 FROM equity_etf_compositions WHERE etf_ticker=? AND composition_date=? LIMIT 1",
                (ticker, d),
            ).fetchone()
            if not exists:
                raise HTTPException(status_code=404, detail=f"No composition for {ticker} on {d}")

        # Additions: in date2, not in date1
        added_rows = conn.execute(
            """
            SELECT c2.component_identifier, c2.component_name, c2.component_ticker,
                   c2.component_weight AS weight_new, c2.component_shares AS shares_new,
                   c2.component_sector, c2.component_currency
            FROM equity_etf_compositions c2
            LEFT JOIN equity_etf_compositions c1
                ON  c1.etf_ticker           = c2.etf_ticker
                AND c1.component_identifier = c2.component_identifier
                AND c1.composition_date     = ?
            WHERE c2.etf_ticker       = ?
              AND c2.composition_date = ?
              AND c1.component_identifier IS NULL
            ORDER BY c2.component_weight DESC
            """,
            (date1, ticker, date2),
        ).fetchall()

        # Removals: in date1, not in date2
        removed_rows = conn.execute(
            """
            SELECT c1.component_identifier, c1.component_name, c1.component_ticker,
                   c1.component_weight AS weight_old, c1.component_shares AS shares_old,
                   c1.component_sector, c1.component_currency
            FROM equity_etf_compositions c1
            LEFT JOIN equity_etf_compositions c2
                ON  c2.etf_ticker           = c1.etf_ticker
                AND c2.component_identifier = c1.component_identifier
                AND c2.composition_date     = ?
            WHERE c1.etf_ticker       = ?
              AND c1.composition_date = ?
              AND c2.component_identifier IS NULL
            ORDER BY c1.component_weight DESC
            """,
            (date2, ticker, date1),
        ).fetchall()

        # Weight changes: present in both, shares count actually changed
        changed_rows = conn.execute(
            """
            SELECT c1.component_identifier, c1.component_name, c1.component_ticker,
                   c1.component_weight AS weight_old, c2.component_weight AS weight_new,
                   (c2.component_weight - c1.component_weight) AS weight_delta,
                   c1.component_sector,
                   c1.component_shares AS shares_old, c2.component_shares AS shares_new,
                   (c2.component_shares - c1.component_shares) AS shares_delta
            FROM equity_etf_compositions c1
            JOIN equity_etf_compositions c2
                ON  c2.etf_ticker           = c1.etf_ticker
                AND c2.component_identifier = c1.component_identifier
                AND c2.composition_date     = ?
            WHERE c1.etf_ticker       = ?
              AND c1.composition_date = ?
              AND c1.component_shares IS NOT NULL AND c2.component_shares IS NOT NULL
              AND c1.component_shares != c2.component_shares
            ORDER BY ABS(c2.component_shares - c1.component_shares) DESC
            """,
            (date2, ticker, date1),
        ).fetchall()

    added = [AddedComponent(**dict(r)) for r in added_rows]
    removed = [RemovedComponent(**dict(r)) for r in removed_rows]
    weight_changes = [WeightChange(**dict(r)) for r in changed_rows]

    return CompareResponse(
        ticker=ticker,
        date1=date1,
        date2=date2,
        summary=CompareSummary(
            added_count=len(added),
            removed_count=len(removed),
            weight_changes_count=len(weight_changes),
        ),
        added=added,
        removed=removed,
        weight_changes=weight_changes,
    )


def _compute_changes_for_pair(conn, ticker: str, date_from: str, date_to: str) -> list[dict]:
    """Compute and return change rows for a consecutive date pair. Does not commit."""
    changes = []

    added_rows = conn.execute(
        """
        SELECT c2.component_identifier, c2.component_name, c2.component_ticker,
               c2.component_sector, c2.component_weight AS weight_new,
               c2.component_shares AS shares_new
        FROM equity_etf_compositions c2
        LEFT JOIN equity_etf_compositions c1
            ON c1.etf_ticker=c2.etf_ticker AND c1.component_identifier=c2.component_identifier AND c1.composition_date=?
        WHERE c2.etf_ticker=? AND c2.composition_date=? AND c1.component_identifier IS NULL
        """,
        (date_from, ticker, date_to),
    ).fetchall()
    for r in added_rows:
        changes.append({
            "etf_ticker": ticker, "date_from": date_from, "date_to": date_to,
            "change_type": "added",
            "component_identifier": r["component_identifier"],
            "component_name": r["component_name"],
            "component_ticker": r["component_ticker"],
            "component_sector": r["component_sector"],
            "weight_old": None, "weight_new": r["weight_new"], "weight_delta": None,
            "shares_old": None, "shares_new": r["shares_new"],
        })

    removed_rows = conn.execute(
        """
        SELECT c1.component_identifier, c1.component_name, c1.component_ticker,
               c1.component_sector, c1.component_weight AS weight_old,
               c1.component_shares AS shares_old
        FROM equity_etf_compositions c1
        LEFT JOIN equity_etf_compositions c2
            ON c2.etf_ticker=c1.etf_ticker AND c2.component_identifier=c1.component_identifier AND c2.composition_date=?
        WHERE c1.etf_ticker=? AND c1.composition_date=? AND c2.component_identifier IS NULL
        """,
        (date_to, ticker, date_from),
    ).fetchall()
    for r in removed_rows:
        changes.append({
            "etf_ticker": ticker, "date_from": date_from, "date_to": date_to,
            "change_type": "removed",
            "component_identifier": r["component_identifier"],
            "component_name": r["component_name"],
            "component_ticker": r["component_ticker"],
            "component_sector": r["component_sector"],
            "weight_old": r["weight_old"], "weight_new": None, "weight_delta": None,
            "shares_old": r["shares_old"], "shares_new": None,
        })

    changed_rows = conn.execute(
        """
        SELECT c1.component_identifier, c1.component_name, c1.component_ticker,
               c1.component_sector, c1.component_weight AS weight_old,
               c2.component_weight AS weight_new,
               (c2.component_weight - c1.component_weight) AS weight_delta,
               c1.component_shares AS shares_old,
               c2.component_shares AS shares_new
        FROM equity_etf_compositions c1
        JOIN equity_etf_compositions c2
            ON c2.etf_ticker=c1.etf_ticker AND c2.component_identifier=c1.component_identifier AND c2.composition_date=?
        WHERE c1.etf_ticker=? AND c1.composition_date=?
          AND c1.component_shares IS NOT NULL AND c2.component_shares IS NOT NULL
          AND c1.component_shares != c2.component_shares
        """,
        (date_to, ticker, date_from),
    ).fetchall()
    for r in changed_rows:
        changes.append({
            "etf_ticker": ticker, "date_from": date_from, "date_to": date_to,
            "change_type": "weight_change",
            "component_identifier": r["component_identifier"],
            "component_name": r["component_name"],
            "component_ticker": r["component_ticker"],
            "component_sector": r["component_sector"],
            "weight_old": r["weight_old"],
            "weight_new": r["weight_new"],
            "weight_delta": r["weight_delta"],
            "shares_old": r["shares_old"],
            "shares_new": r["shares_new"],
        })

    return changes


def populate_changes_cache(conn, ticker: str, date_from: str, date_to: str):
    """Compute changes for a date pair and insert into etf_composition_changes."""
    # Skip if already cached
    existing = conn.execute(
        "SELECT 1 FROM etf_composition_changes WHERE etf_ticker=? AND date_from=? AND date_to=? LIMIT 1",
        (ticker, date_from, date_to),
    ).fetchone()
    if existing:
        return

    changes = _compute_changes_for_pair(conn, ticker, date_from, date_to)
    if not changes:
        return

    conn.executemany(
        """
        INSERT OR IGNORE INTO etf_composition_changes
            (etf_ticker, date_from, date_to, change_type, component_identifier,
             component_name, component_ticker, component_sector,
             weight_old, weight_new, weight_delta, shares_old, shares_new)
        VALUES (:etf_ticker, :date_from, :date_to, :change_type, :component_identifier,
                :component_name, :component_ticker, :component_sector,
                :weight_old, :weight_new, :weight_delta, :shares_old, :shares_new)
        """,
        changes,
    )
    conn.commit()


@router.get("/{ticker}/changes", response_model=ChangesResponse)
def get_etf_changes(ticker: str):
    ticker = ticker.upper()
    with get_db() as conn:
        info = conn.execute(
            "SELECT ticker FROM equity_etf_info WHERE ticker=?", (ticker,)
        ).fetchone()
        if not info:
            raise HTTPException(status_code=404, detail=f"ETF '{ticker}' not found")

        dates = conn.execute(
            "SELECT DISTINCT composition_date FROM equity_etf_compositions "
            "WHERE etf_ticker=? ORDER BY composition_date ASC",
            (ticker,),
        ).fetchall()
        date_list = [r["composition_date"] for r in dates]

        # Populate cache for any un-cached consecutive pairs
        for i in range(len(date_list) - 1):
            populate_changes_cache(conn, ticker, date_list[i], date_list[i + 1])

        rows = conn.execute(
            "SELECT date_from, date_to, change_type, component_identifier, "
            "component_name, component_ticker, component_sector, "
            "weight_old, weight_new, weight_delta "
            "FROM etf_composition_changes WHERE etf_ticker=? "
            "ORDER BY date_to DESC, change_type",
            (ticker,),
        ).fetchall()

    return ChangesResponse(
        ticker=ticker,
        changes=[ChangeEvent(**dict(r)) for r in rows],
    )
