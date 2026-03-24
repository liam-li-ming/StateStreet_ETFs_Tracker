from pydantic import BaseModel
from typing import Optional


class HoldingItem(BaseModel):
    component_identifier: Optional[str] = None
    component_name: Optional[str] = None
    component_ticker: Optional[str] = None
    component_weight: Optional[float] = None
    component_sector: Optional[str] = None
    component_shares: Optional[float] = None
    component_currency: Optional[str] = None
    component_sedol: Optional[str] = None


class CompositionResponse(BaseModel):
    ticker: str
    composition_date: str
    nav: Optional[float] = None
    shares_outstanding: Optional[float] = None
    total_net_assets: Optional[float] = None
    holdings_count: int
    holdings: list[HoldingItem]
    holdings_truncated: bool = False


class EtfDetailResponse(BaseModel):
    ticker: str
    name: Optional[str] = None
    domicile: Optional[str] = None
    gross_expense_ratio: Optional[str] = None
    nav: Optional[str] = None
    aum: Optional[str] = None
    last_updated: Optional[str] = None
    latest_composition_date: Optional[str] = None
    available_dates: list[str] = []
    holdings_count: int = 0
    holdings: list[HoldingItem] = []
    holdings_truncated: bool = False
