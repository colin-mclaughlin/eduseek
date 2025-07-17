from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from typing import Optional, List

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

class UpdateFileRequest(BaseModel):
    filename: str

class FileOut(BaseModel):
    id: int
    filename: str
    summary: str | None = None
    deadline: str | None = None  # ISO 8601 string or None (keeping for backward compatibility)
    deadlines: List[str] = Field(default_factory=list)

    class Config:
        from_attributes = True 