from fastapi import APIRouter, UploadFile, File, HTTPException, Request
from services.file_service import save_uploaded_file, extract_text_from_file, chunk_text, summarize_chunks
from services.embedding_service import embed_chunks, get_or_create_chroma_collection
from services.deadline_service import extract_deadlines_from_text, save_deadlines
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import uuid
from sqlalchemy.orm import Session
from core.database import SessionLocal
from models.file import File as FileModel
from models.deadline import Deadline
from schemas.file import FileOut
from fastapi import Depends
from typing import List
import traceback

router = APIRouter()

@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    try:
        file_path = await save_uploaded_file(file)
        text = extract_text_from_file(file_path)
        chunks = chunk_text(text)
        summary = summarize_chunks(chunks)
        # Extract deadlines from the text
        deadlines = extract_deadlines_from_text(text)
        # Mock user_id, course_id, file_id for now
        user_id = uuid.UUID("11111111-1111-1111-1111-111111111111")
        course_id = uuid.UUID("22222222-2222-2222-2222-222222222222")
        file_id = uuid.UUID("33333333-3333-3333-3333-333333333333")
        # Save deadlines to DB
        save_deadlines(deadlines, user_id, course_id, file_id)
        metadata = {
            "user_id": str(user_id),
            "filename": file.filename,
            "course_id": str(course_id)
        }
        embed_chunks(chunks, metadata)
        return JSONResponse(content={"summary": summary, "deadlines": deadlines})
    except Exception as e:
        print("UPLOAD ERROR:", e)
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=str(e))

class QueryRequest(BaseModel):
    query: str

@router.post("/query")
async def query_files(request: QueryRequest):
    try:
        db = get_or_create_chroma_collection()
        results = db.similarity_search_with_score(request.query, k=3)
        matches = [
            {
                "chunk": doc.page_content,
                "metadata": doc.metadata,
                "score": score
            }
            for doc, score in results
        ]
        return {"results": matches}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/", response_model=List[FileOut])
def get_files(db: Session = Depends(get_db)):
    files = db.query(FileModel).all()
    result = []
    for f in files:
        # Find the soonest deadline for this file (if any)
        deadline_obj = (
            db.query(Deadline)
            .filter(Deadline.file_id == f.id)
            .order_by(Deadline.due_date.asc())
            .first()
        )
        deadline = deadline_obj.due_date.isoformat() if deadline_obj else None
        result.append(FileOut(
            filename=f.filename,
            summary=f.summary,
            deadline=deadline
        ))
    return result 