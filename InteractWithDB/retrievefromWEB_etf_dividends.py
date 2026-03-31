import yfinance as yf
import pandas as pd


class GetEtfDividends:
    def fetch_dividends(self, ticker: str) -> pd.DataFrame | None:
        """
        Fetch full dividend history for an ETF ticker via yfinance.

        Returns a DataFrame with columns:
            etf_ticker   - str
            ex_date      - str (YYYY-MM-DD)
            dividend_amount - float

        Returns None if no dividend data is available or on fetch error.
        """
        try:
            yf_ticker = yf.Ticker(ticker)
            dividends = yf_ticker.dividends  # pandas Series: DatetimeIndex -> float
        except Exception as e:
            print(f"[dividends] Error fetching {ticker}: {e}")
            return None

        if dividends is None or dividends.empty:
            return None

        df = dividends.reset_index()
        df.columns = ["ex_date", "dividend_amount"]
        df["ex_date"] = df["ex_date"].dt.strftime("%Y-%m-%d")
        df["etf_ticker"] = ticker
        df["dividend_amount"] = pd.to_numeric(df["dividend_amount"], errors="coerce")
        df = df.dropna(subset=["dividend_amount"])

        return df[["etf_ticker", "ex_date", "dividend_amount"]]
