import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, Enum, Integer
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
from enum import Enum as PyEnum
from core.database import Base

class DeadlineSource(PyEnum):
    file = "file"
    manual = "manual"

class Deadline(Base):
    __tablename__ = "deadlines"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True, nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    course_id = Column(UUID(as_uuid=True), ForeignKey("courses.id"), nullable=False)
    file_id = Column(Integer, ForeignKey("files.id"), nullable=True)
    title = Column(String, nullable=False)
    due_date = Column(DateTime, nullable=False)
    source = Column(Enum(DeadlineSource), nullable=False) 