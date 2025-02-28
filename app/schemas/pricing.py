from typing import List, Optional
from datetime import date, datetime
from pydantic import BaseModel


class LLMPricingCreate(BaseModel):
    provider: str
    model: str
    version: str
    input_price_per_million_tokens: float
    output_price_per_million_tokens: float
    effective_from: date


class LLMPricingResponse(LLMPricingCreate):
    id: int
    effective_to: Optional[date]
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


class TokenUsageData(BaseModel):
    date: date
    provider: str
    model: str
    inputTokens: int
    outputTokens: int
    totalCost: float
