from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse
from typing import Optional
from datetime import date
from uuid import UUID
from sqlalchemy.orm import Session
from core.database import SessionLocal
from models.deadline import Deadline
from services.assistant_service import generate_daily_plan

router = APIRouter()

@router.get("/assistant/daily")
def daily_assistant(user_id: Optional[UUID] = Query(None)):
    # Use a mock user_id if not provided
    if user_id is None:
        user_id = UUID("11111111-1111-1111-1111-111111111111")
    db: Session = SessionLocal()
    try:
        today = date.today()
        deadlines = db.query(Deadline).filter(
            Deadline.user_id == user_id,
            Deadline.due_date >= today
        ).order_by(Deadline.due_date.asc()).all()
        summary = generate_daily_plan(deadlines)
        return JSONResponse(content={
            "deadlines": [
                {
                    "title": d.title,
                    "due_date": d.due_date.isoformat(),
                    "source": d.source.value
                } for d in deadlines
            ],
            "summary": summary
        })
    finally:
        db.close() 