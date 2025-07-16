import uuid
from sqlalchemy import Column, Integer, String, Text, DateTime
from core.database import Base
import datetime

class File(Base):
    __tablename__ = "files"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    text = Column(Text)
    summary = Column(Text)
    deadlines = Column(Text)
    uploaded_at = Column(DateTime, default=datetime.datetime.utcnow)

    # user_id = Column(Integer, ForeignKey("users.id"))  # <-- COMMENTED FOR NOW
    # user = relationship("User", back_populates="files")  # <-- COMMENTED FOR NOW

    # TODO: Re-enable user_id when user table is created 