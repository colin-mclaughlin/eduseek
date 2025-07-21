import uuid
from sqlalchemy import Column, Integer, String, Text, DateTime, ARRAY, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from core.database import Base
import datetime

class File(Base):
    __tablename__ = "files"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    text = Column(Text)
    summary = Column(Text)
    deadlines = Column(ARRAY(String), nullable=False, default=list)
    tags = Column(ARRAY(String), nullable=False, default=list)
    uploaded_at = Column(DateTime, default=datetime.datetime.utcnow)
    user_id = Column(UUID(as_uuid=True), nullable=True)  # Remove foreign key constraint temporarily
    course_id = Column(UUID(as_uuid=True), nullable=True)  # Remove foreign key constraint temporarily
    content_hash = Column(String, nullable=True, index=True)  # <-- Added for duplicate detection
    # user = relationship("User", back_populates="files")
    # course = relationship("Course", back_populates="files")
    # TODO: Re-enable foreign key constraints when users and courses tables are properly set up 