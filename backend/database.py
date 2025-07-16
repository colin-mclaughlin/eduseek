import os
from sqlalchemy import create_engine
from models.file import Base

# Delete the old SQLite DB if it exists (for dev only)
if os.path.exists("eduseek.db"):
    os.remove("eduseek.db")

engine = create_engine("sqlite:///./eduseek.db")
Base.metadata.create_all(bind=engine) 