from typing import List, Optional
from pydantic import BaseModel, Field


class FundingCall(BaseModel):
    source: str
    source_url: str
    call_id: Optional[str] = None
    title: str
    summary: str = ""
    program: Optional[str] = None
    opening_date: Optional[str] = None
    deadline_date: Optional[str] = None
    budget_total: Optional[float] = None
    funding_type: Optional[str] = None
    record_type: str = "call"
    why_relevant: List[str] = Field(default_factory=list)
    eligible_entities: List[str] = Field(default_factory=list)
    countries: List[str] = Field(default_factory=list)
    topics: List[str] = Field(default_factory=list)
    raw_text: str = ""
    relevance_score: float = 0.0