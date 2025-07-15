from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from enum import Enum

class DeadlineSource(str, Enum):
    file = "file"
    manual = "manual"

class DeadlineBase(BaseModel):
    id: UUID
    user_id: UUID
    course_id: UUID
    file_id: UUID | None = None
    title: str
    due_date: datetime
    source: DeadlineSource

    class Config:
        orm_mode = True 