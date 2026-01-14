from pydantic import BaseModel
from typing import Optional, List
from bson import ObjectId
from datetime import datetime


class Department(BaseModel):
    name: str
    description: str
    intent: Optional[List[str]] = []
    tenant_id: str
    duration_threshold: Optional[int] = None
    sentiment_threshold: Optional[int] = None
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {
            ObjectId: str,
            datetime: lambda v: v.isoformat()
        }

