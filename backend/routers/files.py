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
from sqlalchemy import select
from pathlib import Path

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/upload")
async def upload_file(file: UploadFile = File(...), db: Session = Depends(get_db)):
    try:
        file_path = await save_uploaded_file(file)
        text = extract_text_from_file(file_path)
        # Save file entry to DB (no summary yet)
        file_entry = FileModel(
            filename=file.filename,
            summary=None
        )
        db.add(file_entry)
        db.commit()
        db.refresh(file_entry)
        return {"id": str(file_entry.id), "filename": file_entry.filename}
    except Exception as e:
        print("UPLOAD ERROR:", e)
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/summarize/{file_id}")
async def summarize_file(file_id: str, db: Session = Depends(get_db)):
    try:
        file_entry = db.query(FileModel).filter(FileModel.id == file_id).first()
        if not file_entry:
            raise HTTPException(status_code=404, detail="File not found")
        # Load text from file
        file_path = Path('uploads') / file_entry.filename
        text = extract_text_from_file(file_path)
        chunks = chunk_text(text)
        summary = summarize_chunks(chunks)
        file_entry.summary = summary
        db.commit()
        db.refresh(file_entry)
        return {"id": str(file_entry.id), "filename": file_entry.filename, "summary": file_entry.summary}
    except Exception as e:
        print("SUMMARIZE ERROR:", e)
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

@router.get("/", response_model=List[FileOut])
def get_files(db: Session = Depends(get_db)):
    try:
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
                id=f.id,
                filename=f.filename,
                summary=f.summary,
                deadline=deadline
            ))
        return result
    except Exception as e:
        print("GET FILES ERROR:", e)
        import traceback; traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e)) 