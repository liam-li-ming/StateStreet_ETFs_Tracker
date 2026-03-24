from pydantic import BaseModel
from typing import Optional


class AlertItem(BaseModel):
    etf_ticker: str
    date_from: str
    date_to: str
    change_type: str
    component_identifier: Optional[str] = None
    component_ticker: Optional[str] = None
    component_name: Optional[str] = None
    component_sector: Optional[str] = None
    weight_old: Optional[float] = None
    weight_new: Optional[float] = None
    weight_delta: Optional[float] = None
    shares_old: Optional[float] = None
    shares_new: Optional[float] = None
    detected_at: Optional[str] = None


class AlertsResponse(BaseModel):
    alerts: list[AlertItem]
    total: int
    page: int
    page_size: int
    total_pages: int


class SearchResultItem(BaseModel):
    etf_ticker: str
    etf_name: Optional[str] = None
    composition_date: str
    component_name: Optional[str] = None
    component_identifier: Optional[str] = None
    component_weight: Optional[float] = None
    component_sector: Optional[str] = None
    component_shares: Optional[float] = None


class SearchResponse(BaseModel):
    component_ticker: str
    found_in: list[SearchResultItem]
    total_etfs: int
