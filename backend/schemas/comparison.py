from pydantic import BaseModel
from typing import Optional


class AddedComponent(BaseModel):
    component_identifier: Optional[str] = None
    component_name: Optional[str] = None
    component_ticker: Optional[str] = None
    weight_new: Optional[float] = None
    component_sector: Optional[str] = None
    component_currency: Optional[str] = None


class RemovedComponent(BaseModel):
    component_identifier: Optional[str] = None
    component_name: Optional[str] = None
    component_ticker: Optional[str] = None
    weight_old: Optional[float] = None
    component_sector: Optional[str] = None
    component_currency: Optional[str] = None


class WeightChange(BaseModel):
    component_identifier: Optional[str] = None
    component_name: Optional[str] = None
    component_ticker: Optional[str] = None
    weight_old: Optional[float] = None
    weight_new: Optional[float] = None
    weight_delta: Optional[float] = None
    component_sector: Optional[str] = None
    shares_old: Optional[float] = None
    shares_new: Optional[float] = None
    shares_delta: Optional[float] = None


class CompareSummary(BaseModel):
    added_count: int
    removed_count: int
    weight_changes_count: int


class CompareResponse(BaseModel):
    ticker: str
    date1: str
    date2: str
    summary: CompareSummary
    added: list[AddedComponent]
    removed: list[RemovedComponent]
    weight_changes: list[WeightChange]


class ChangeEvent(BaseModel):
    date_from: str
    date_to: str
    change_type: str
    component_identifier: Optional[str] = None
    component_name: Optional[str] = None
    component_ticker: Optional[str] = None
    component_sector: Optional[str] = None
    weight_old: Optional[float] = None
    weight_new: Optional[float] = None
    weight_delta: Optional[float] = None


class ChangesResponse(BaseModel):
    ticker: str
    changes: list[ChangeEvent]
