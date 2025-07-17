from fastapi import APIRouter, Query, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional
from datetime import date
from uuid import UUID
from sqlalchemy.orm import Session
from core.database import SessionLocal
from models.deadline import Deadline
from models.file import File as FileModel
from services.assistant_service import generate_daily_plan, query_files
from routers.files import get_db

class QueryRequest(BaseModel):
    query: str
    course_filter: Optional[str] = None
    course_id: Optional[str] = None
    file_id: Optional[str] = None

router = APIRouter(prefix="/api/assistant", tags=["Assistant"])

@router.get("/daily")
def daily_assistant(user_id: Optional[UUID] = Query(None)):
    # Use a mock user_id if not provided
    if user_id is None:
        user_id = UUID(1111111111111111111111111111111)
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

@router.post("/query")
def query_assistant(request: QueryRequest, db: Session = Depends(get_db)):
    """
    Query the assistant with a question about uploaded files.
    Args:
        request: QueryRequest containing query and optional course_filter, course_id, file_id
    Returns:
        JSON response with answer and sources
    Example payloads:
        {
            "query": "Summarize labs",
            "course_id": "cisc235"
        }
        {
            "query": "What is in this file?",
            "file_id": "123"
        }
    """
    try:
        # Try to get user_id and course_id from the most recent file (or use a better strategy as needed)
        file_entry = db.query(FileModel).order_by(FileModel.id.desc()).first()
        user_id = getattr(file_entry, 'user_id', None) if file_entry else None
        course_id = getattr(file_entry, 'course_id', None) if file_entry else None
        print(f"[AssistantRouter] Using user_id={user_id}, course_id={course_id} for query filter.")
        print(f"[AssistantRouter] Query: {request.query}")
        result = query_files(
            request.query,
            request.course_filter,
            user_id=user_id,
            course_id=request.course_id or course_id,
            file_id=request.file_id
        )
        return JSONResponse(content=result)
    except Exception as e:
        print(f"[AssistantRouter] Error: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "answer": "Sorry, I encountered an error while processing your question. Please try again.",
                "sources": []
            }
        ) 