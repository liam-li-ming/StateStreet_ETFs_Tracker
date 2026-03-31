from pydantic import BaseModel


class DividendItem(BaseModel):
    etf_ticker: str
    ex_date: str
    dividend_amount: float
    currency: str


class DividendsResponse(BaseModel):
    dividends: list[DividendItem]
    total: int
    page: int
    page_size: int
    total_pages: int
