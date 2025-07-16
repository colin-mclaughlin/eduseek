from pydantic import BaseModel
from uuid import UUID
from datetime import datetime

class FileBase(BaseModel):
    id: UUID
    user_id: UUID
    course_id: UUID
    filename: str
    filepath: str
    summary: str | None = None
    upload_date: datetime
    embedding_id: str | None = None

    class Config:
        orm_mode = True

class FileOut(BaseModel):
    id: int
    filename: str
    summary: str | None = None
    deadline: str | None = None  # ISO 8601 string or None

    class Config:
        from_attributes = True 