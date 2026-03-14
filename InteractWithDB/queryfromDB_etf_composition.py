import sqlite3
import os
import pandas as pd
from datetime import datetime


def get_etf_composition(etf_ticker, composition_date, db_path="data/etf_compositions.db"):
    """
    Retrieve the holdings composition for a given ETF ticker and date from
    the local SQLite database.

    Returns a DataFrame that joins component-level data from
    equity_etf_compositions with fund-level metadata from equity_etf_info,
    ordered by component weight descending.

    :param etf_ticker: ETF ticker symbol (e.g. 'SPY'). Case-insensitive.
    :param composition_date: Holdings date string in 'YYYY-MM-DD' format.
    :param db_path: Path to the SQLite database file.
    :return: DataFrame with full composition + metadata, or empty DataFrame
             if the ticker / date combination is not found.
    """
    etf_ticker = etf_ticker.strip().upper()

    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # ── Check 1: does the ticker exist at all? ────────────────────────
        cursor.execute(
            "SELECT COUNT(*) FROM equity_etf_info WHERE ticker = ?",
            (etf_ticker,)
        )
        if cursor.fetchone()[0] == 0:
            print(f"Composition not available: '{etf_ticker}' is not tracked in the database.")
            print(f"Make sure '{etf_ticker}' is an ETF from State Street. ")
            print(f"Run main.py to fetch ETF data first.")
            conn.close()
            return pd.DataFrame()

        # ── Check 2: does any data exist for this date? ───────────────────
        cursor.execute(
            """
            SELECT COUNT(*) FROM equity_etf_compositions
            WHERE etf_ticker = ? AND composition_date = ?
            """,
            (etf_ticker, composition_date)
        )
        if cursor.fetchone()[0] == 0:
            # Show which dates ARE available so the user knows what to query
            cursor.execute(
                """
                SELECT DISTINCT composition_date
                FROM equity_etf_compositions
                WHERE etf_ticker = ?
                ORDER BY composition_date DESC
                LIMIT 10
                """,
                (etf_ticker,)
            )
            available = [row[0] for row in cursor.fetchall()]
            conn.close()

            print(f"Composition not available: no data for {etf_ticker} on {composition_date}.")
            if available:
                print(f"Available dates for {etf_ticker} (most recent first):")
                for d in available:
                    print(f"  {d}")
            else:
                print(f"No composition data found for {etf_ticker} at all.")
                print(f"Run main.py to fetch ETF data first.")
            return pd.DataFrame()

        # ── Fetch: join compositions with ETF info metadata ───────────────
        query = """
            SELECT
                -- ETF-level metadata (from equity_etf_info)
                i.ticker            AS etf_ticker,
                i.name              AS etf_name,
                i.domicile,
                i.gross_expense_ratio,
                i.aum,

                -- Fund snapshot data (from equity_etf_compositions, fund-level)
                c.composition_date,
                c.nav               AS nav,
                c.shares_outstanding,
                c.total_net_assets,

                -- Component-level data
                c.component_name,
                c.component_ticker,
                c.component_identifier,
                c.component_sedol,
                c.component_weight,
                c.component_sector,
                c.component_shares,
                c.component_currency

            FROM equity_etf_compositions c
            JOIN equity_etf_info i ON i.ticker = c.etf_ticker
            WHERE c.etf_ticker = ?
              AND c.composition_date = ?
            ORDER BY c.component_weight DESC
        """
        df = pd.read_sql_query(query, conn, params=(etf_ticker, composition_date))
        conn.close()

        print(f"Retrieved {len(df)} holdings for {etf_ticker} on {composition_date}.")
        return df

    except Exception as e:
        print(f"Error querying composition for {etf_ticker} on {composition_date}: {e}")
        return pd.DataFrame()


def export_composition_to_excel(df, etf_ticker, composition_date, output_dir = "ETF Composition DB"):
    """
    Export an ETF composition DataFrame to a formatted Excel workbook.

    The workbook contains two sheets:
        1. Holdings      — all 504 component rows with every column, formatted
                           as a table with auto-fit column widths.
                           component_weight is displayed as a percentage (%).
        2. Sector Summary — aggregated weight and share count per GICS sector,
                            sorted by total weight descending.

    The output file is saved to output_dir and named:
        {etf_ticker}_composition_{composition_date}.xlsx

    :param df: DataFrame returned by get_etf_composition().
    :param etf_ticker: ETF ticker string used in the filename.
    :param composition_date: Date string used in the filename (YYYY-MM-DD).
    :param output_dir: Directory to write the file into (created if absent).
    :return: Full path to the saved file, or None on failure.
    """
    if df.empty:
        print("Nothing to export — DataFrame is empty.")
        return None

    os.makedirs(output_dir, exist_ok=True)

    filename    = f"{etf_ticker.upper()}_composition_{composition_date}.xlsx"
    output_path = os.path.join(output_dir, filename)

    try:
        # ── Build the export copy ──────────────────────────────────────────
        holdings = df.copy()

        # component_weight is stored as a percentage value (e.g. 7.7849 = 7.7849%).
        # xlsxwriter's '0.0000%' format multiplies by 100 for display, so divide
        # by 100 here so the cell stores the decimal fraction (0.077849) and
        # Excel renders it correctly as 7.7849%.
        if 'component_weight' in holdings.columns:
            holdings['component_weight'] = holdings['component_weight'] / 100

        # ── Sector summary sheet ───────────────────────────────────────────
        sector_summary = (
            df.groupby('component_sector', dropna=False)
            .agg(
                total_weight  = ('component_weight', 'sum'),
                holding_count = ('component_ticker', 'count')
            )
            .reset_index()
            .rename(columns={'component_sector': 'sector'})
            .sort_values('total_weight', ascending=False)
        )
        # Same conversion: divide by 100 so pct_fmt displays correctly.
        sector_summary['total_weight_pct'] = (sector_summary['total_weight'] / 100).round(6)
        sector_summary = sector_summary.drop(columns='total_weight')

        # ── Write to Excel with xlsxwriter for formatting ──────────────────
        with pd.ExcelWriter(output_path, engine='xlsxwriter') as writer:
            holdings.to_excel(writer, sheet_name='Holdings',       index=False)
            sector_summary.to_excel(writer, sheet_name='Sector Summary', index=False)

            workbook = writer.book

            # ── Format: Holdings sheet ─────────────────────────────────────
            ws_holdings = writer.sheets['Holdings']

            header_fmt = workbook.add_format({
                'bold': True, 'bg_color': '#1F3864', 'font_color': '#FFFFFF',
                'border': 1, 'align': 'center'
            })
            pct_fmt    = workbook.add_format({'num_format': '0.0000%', 'border': 1})
            num_fmt    = workbook.add_format({'num_format': '#,##0.00',  'border': 1})
            int_fmt    = workbook.add_format({'num_format': '#,##0',     'border': 1})
            text_fmt   = workbook.add_format({'border': 1})
            alt_fmt    = workbook.add_format({'bg_color': '#EEF2F7',     'border': 1})
            alt_pct    = workbook.add_format({'bg_color': '#EEF2F7', 'num_format': '0.0000%', 'border': 1})
            alt_num    = workbook.add_format({'bg_color': '#EEF2F7', 'num_format': '#,##0.00', 'border': 1})
            alt_int    = workbook.add_format({'bg_color': '#EEF2F7', 'num_format': '#,##0',    'border': 1})

            # Column widths and formats for Holdings sheet
            col_specs = {
                'etf_ticker':           (12,  text_fmt, alt_fmt),
                'etf_name':             (40,  text_fmt, alt_fmt),
                'domicile':             (12,  text_fmt, alt_fmt),
                'gross_expense_ratio':  (18,  text_fmt, alt_fmt),
                'aum':                  (18,  text_fmt, alt_fmt),
                'composition_date':     (16,  text_fmt, alt_fmt),
                'nav':                  (12,  num_fmt,  alt_num),
                'shares_outstanding':   (20,  int_fmt,  alt_int),
                'total_net_assets':     (20,  num_fmt,  alt_num),
                'component_name':       (36,  text_fmt, alt_fmt),
                'component_ticker':     (14,  text_fmt, alt_fmt),
                'component_identifier': (20,  text_fmt, alt_fmt),
                'component_sedol':      (14,  text_fmt, alt_fmt),
                'component_weight':     (16,  pct_fmt,  alt_pct),
                'component_sector':     (30,  text_fmt, alt_fmt),
                'component_shares':     (18,  int_fmt,  alt_int),
                'component_currency':   (14,  text_fmt, alt_fmt),
            }

            for col_idx, col_name in enumerate(holdings.columns):
                spec = col_specs.get(col_name, (16, text_fmt, alt_fmt))
                width, even_fmt, odd_fmt = spec

                # Header
                ws_holdings.write(0, col_idx, col_name, header_fmt)
                ws_holdings.set_column(col_idx, col_idx, width)

                # Data rows with alternating row colours
                for row_idx, value in enumerate(holdings[col_name], start=1):
                    fmt = even_fmt if row_idx % 2 == 0 else odd_fmt
                    if pd.isna(value):
                        ws_holdings.write_blank(row_idx, col_idx, None, fmt)
                    else:
                        ws_holdings.write(row_idx, col_idx, value, fmt)

            ws_holdings.freeze_panes(1, 0)
            ws_holdings.autofilter(0, 0, len(holdings), len(holdings.columns) - 1)

            # ── Format: Sector Summary sheet ──────────────────────────────
            ws_sector = writer.sheets['Sector Summary']

            sec_col_specs = {
                'sector':           (36, text_fmt, alt_fmt),
                'holding_count':    (14, int_fmt,  alt_int),
                'total_weight_pct': (18, pct_fmt,  alt_pct),
            }

            for col_idx, col_name in enumerate(sector_summary.columns):
                spec = sec_col_specs.get(col_name, (16, text_fmt, alt_fmt))
                width, even_fmt, odd_fmt = spec
                ws_sector.write(0, col_idx, col_name, header_fmt)
                ws_sector.set_column(col_idx, col_idx, width)
                for row_idx, value in enumerate(sector_summary[col_name], start=1):
                    fmt = even_fmt if row_idx % 2 == 0 else odd_fmt
                    if pd.isna(value):
                        ws_sector.write_blank(row_idx, col_idx, None, fmt)
                    else:
                        ws_sector.write(row_idx, col_idx, value, fmt)

            ws_sector.freeze_panes(1, 0)

        print(f"Exported to: {output_path}")
        return output_path

    except Exception as e:
        print(f"Error exporting to Excel: {e}")
        return None


def get_available_dates(etf_ticker, db_path="data/etf_compositions.db"):
    """
    Return all composition dates stored for a given ETF, newest first.

    :param etf_ticker: ETF ticker symbol (e.g. 'SPY'). Case-insensitive.
    :param db_path: Path to the SQLite database file.
    :return: List of date strings in 'YYYY-MM-DD' format, or empty list.
    """
    etf_ticker = etf_ticker.strip().upper()
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT DISTINCT composition_date
            FROM equity_etf_compositions
            WHERE etf_ticker = ?
            ORDER BY composition_date DESC
            """,
            (etf_ticker,)
        )
        dates = [row[0] for row in cursor.fetchall()]
        conn.close()
        return dates
    except Exception as e:
        print(f"Error fetching available dates for {etf_ticker}: {e}")
        return []


# ──────────────────────────────────────────────────────────────────────────────
# Run directly to query interactively
# ──────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":

    ticker = input("ETF ticker (e.g. SPY): ").strip().upper()

    # Show available dates first so the user can pick a valid one
    dates = get_available_dates(ticker)
    if dates:
        print(f"\nAvailable dates for {ticker} ({len(dates)} total, most recent first):")
        for d in dates[:10]:
            print(f"  {d}")
        if len(dates) > 10:
            print(f"  ... and {len(dates) - 10} more")
        print()

    date = input("Composition date (YYYY-MM-DD): ").strip()

    df = get_etf_composition(ticker, date)

    if not df.empty:
        # Print summary header
        print(f"\n{'='*64}")
        print(f"  {df['etf_name'].iloc[0]}  ({ticker})")
        print(f"  Date:              {df['composition_date'].iloc[0]}")
        print(f"  NAV:               ${float(df['nav'].iloc[0]):.4f}")
        print(f"  Shares Outstanding:{float(df['shares_outstanding'].iloc[0]):,.0f}")
        print(f"  Total Net Assets:  ${float(df['total_net_assets'].iloc[0]):,.0f}")
        print(f"  Gross Exp. Ratio:  {df['gross_expense_ratio'].iloc[0]}")
        print(f"  AUM:               {df['aum'].iloc[0]}")
        print(f"  Domicile:          {df['domicile'].iloc[0]}")
        print(f"  Holdings:          {len(df)}")
        print(f"{'='*64}")

        # Print top 10 holdings
        print(f"\nTop 10 Holdings:")
        print(f"{'─'*64}")
        print(f"  {'Ticker':<8} {'Name':<35} {'Weight':>8}  {'Sector'}")
        print(f"{'─'*64}")
        for _, row in df.head(10).iterrows():
            weight_pct = f"{float(row['component_weight']):.2f}%" if pd.notna(row['component_weight']) else "N/A"
            sector     = row['component_sector'] if pd.notna(row['component_sector']) else ""
            name       = str(row['component_name'])[:34] if pd.notna(row['component_name']) else ""
            tkr        = str(row['component_ticker'])[:7] if pd.notna(row['component_ticker']) else ""
            print(f"  {tkr:<8} {name:<35} {weight_pct:>8}  {sector}")
        print(f"{'─'*64}")

        # Sector breakdown
        if 'component_sector' in df.columns:
            print(f"\nSector Breakdown:")
            sector_weights = (
                df.groupby('component_sector')['component_weight']
                .sum()
                .sort_values(ascending=False)
            )
            for sector, weight in sector_weights.items():
                if pd.notna(sector) and sector:
                    print(f"  {sector:<40} {weight:.2f}%")

        print(f"\nDataFrame shape: {df.shape[0]} rows × {df.shape[1]} columns")
        print(f"Columns: {list(df.columns)}")

        # ── Export to Excel ────────────────────────────────────────────────
        export = input("\nExport to Excel? (y/n): ").strip().lower()
        if export == 'y':
            export_composition_to_excel(df, ticker, date)
