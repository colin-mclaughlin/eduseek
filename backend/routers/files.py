from fastapi import APIRouter, UploadFile, File, HTTPException, Request, Body
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
import openai
import os

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
        # Save file entry to DB (now with text)
        file_entry = FileModel(
            filename=file.filename,
            text=text,  # <-- Save extracted text
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
        return file_entry
    except Exception as e:
        print("SUMMARIZE ERROR:", e)
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=str(e))

class QueryRequest(BaseModel):
    question: str

@router.post("/query/")
def query_files(request: QueryRequest, db: Session = Depends(get_db)):
    print("DEBUG: /query/ endpoint called")
    all_files = db.query(FileModel).all()
    combined_text = " ".join([file.text for file in all_files if file.text])

    print(f"DEBUG: Combined text for Q&A: {repr(combined_text[:500])}")  # Only print first 500 chars

    if not combined_text:
        raise HTTPException(status_code=404, detail="No file text available")

    prompt = f"Answer this question using the course content below.\n\nQuestion: {request.question}\n\nContent:\n{combined_text}"

    try:
        client = openai.Client(api_key=os.getenv("OPENAI_API_KEY"))
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )
        return {"answer": response.choices[0].message.content}
    except Exception as e:
        print(f"OpenAI error: {e}")
        raise HTTPException(status_code=500, detail="OpenAI request failed")

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

@router.delete("/{file_id}", status_code=204)
def delete_file(file_id: int, db: Session = Depends(get_db)):
    file = db.query(FileModel).filter(FileModel.id == file_id).first()
    if not file:
        raise HTTPException(status_code=404, detail="File not found")
    # Delete file from disk if it exists
    file_path = Path('uploads') / file.filename
    try:
        if file_path.exists():
            file_path.unlink()
    except Exception as e:
        print(f"Error deleting file from disk: {e}")
        # Continue to delete from DB anyway
    db.delete(file)
    db.commit()
    return

@router.get("/smart-suggestion")
def get_smart_suggestion(db: Session = Depends(get_db)):
    files = db.query(FileModel).filter(FileModel.summary.isnot(None)).all()
    if not files:
        return {"suggestion": "Upload and summarize a file to get started."}
    
    summaries = [f.summary for f in files if f.summary]
    context = " ".join(summaries)

    prompt = f"Based on the following summarized lecture material, give one helpful study suggestion:\n\n{context}"

    try:
        client = openai.Client(api_key=os.getenv("OPENAI_API_KEY"))
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
        )
        suggestion = response.choices[0].message.content.strip()
        return {"suggestion": suggestion}
    except Exception as e:
        print(f"Suggestion generation failed: {e}")
        return {"suggestion": "Could not generate a suggestion right now."} 