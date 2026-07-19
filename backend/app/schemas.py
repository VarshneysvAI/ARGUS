from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List

class ExtractionSchema(BaseModel):
    corridor: Optional[str] = "unknown"
    commodity: Optional[str] = "crude_oil"
    economy: Optional[str] = "IN"
    named_refinery: Optional[str] = "Jamnagar"
    volume_lost_mbd: float = Field(ge=0.0, le=21.0)
    duration_days: int = Field(ge=1, le=180)
    confidence: float = Field(ge=0.0, le=1.0)

class MathStateSchema(BaseModel):
    c_delta_usd_day: float
    c_delta_inr_crore_day: float
    # More properties will be added in Sprint 2
