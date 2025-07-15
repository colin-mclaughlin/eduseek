from pydantic import BaseModel
from uuid import UUID
from datetime import datetime

class CourseBase(BaseModel):
    id: UUID
    user_id: UUID
    name: str
    term: str | None = None
    created_at: datetime

    class Config:
        orm_mode = True 