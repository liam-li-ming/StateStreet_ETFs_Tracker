from pydantic import BaseModel
from typing import Optional


class EtfInfo(BaseModel):
    ticker: str
    name: Optional[str] = None
    domicile: Optional[str] = None
    gross_expense_ratio: Optional[str] = None
    nav: Optional[str] = None
    aum: Optional[str] = None
    last_updated: Optional[str] = None


class EtfListResponse(BaseModel):
    etfs: list[EtfInfo]
    total: int


class EtfDatesResponse(BaseModel):
    ticker: str
    dates: list[str]
