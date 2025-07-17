from fastapi import APIRouter, UploadFile, File, HTTPException, Request, Body
from services.file_service import save_uploaded_file, extract_text_from_file, chunk_text, summarize_chunks
from services.embedding_service import embed_chunks, get_or_create_chroma_collection, create_file_embeddings, delete_file_embeddings
from services.deadline_service import extract_deadlines_from_text, save_deadlines
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import uuid
from sqlalchemy.orm import Session
from core.database import SessionLocal
from models.file import File as FileModel
from models.deadline import Deadline
from schemas.file import FileOut, UpdateFileRequest
from fastapi import Depends
from typing import List
import traceback
from sqlalchemy import select
from pathlib import Path
import os
import re
from datetime import datetime
from dateutil import parser
from collections import Counter
from services.lms_scraper import scrape_lms_files, LMS_TYPE
from fastapi import status

router = APIRouter()

def extract_dates_from_text(text: str) -> list[str]:
    """
    Extract academic deadlines from text using comprehensive regex patterns.
    Handles various formats like "due on January 26, 2024", "Quiz on Feb 2", etc.
    """
    # Define comprehensive patterns for academic deadline detection
    patterns = [
        # "due on <Month> <Day>[, <Year>]"
        r"\b(?:due|deadline|assignment|project|quiz|test|exam|midterm|final)\s+(?:on|by|is|will\s+be)\s+(?:the\s+)?(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)[.,]?\s+\d{1,2}(?:st|nd|rd|th)?(?:,?\s*\d{4})?\b",
        
        # "<event> on <Month> <Day>[, <Year>]"
        r"\b(?:assignment|project|quiz|test|exam|midterm|final|review|session|class|lecture|lab|workshop|presentation)\s+(?:on|held\s+on|scheduled\s+for)\s+(?:the\s+)?(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)[.,]?\s+\d{1,2}(?:st|nd|rd|th)?(?:,?\s*\d{4})?\b",
        
        # "<Month> <Day>[, <Year>]" (standalone dates)
        r"\b(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)[.,]?\s+\d{1,2}(?:st|nd|rd|th)?(?:,?\s*\d{4})?\b",
        
        # "<Day> <Month>[, <Year>]" (day first format)
        r"\b\d{1,2}(?:st|nd|rd|th)?\s+(?:of\s+)?(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)[.,]?\s*(?:\d{4})?\b"
    ]
    
    matches = []
    for pattern in patterns:
        matches.extend(re.findall(pattern, text, flags=re.IGNORECASE))
    
    # Remove duplicates while preserving order
    unique_matches = []
    for match in matches:
        if match not in unique_matches:
            unique_matches.append(match)
    
    parsed_dates = []
    current_year = datetime.now().year
    
    for match in unique_matches:
        try:
            # Create a default date for parsing (current year if year is missing)
            default_date = datetime(current_year, 1, 1)
            
            # Parse the date with fuzzy parsing
            parsed_date = parser.parse(match, fuzzy=True, default=default_date)
            
            # If the parsed date is in the past relative to default, assume next year
            if parsed_date.year == current_year and parsed_date < datetime.now():
                parsed_date = parsed_date.replace(year=current_year + 1)
            
            # Only include future dates
            if parsed_date >= datetime.now():
                iso_date = parsed_date.date().isoformat()
                parsed_dates.append(iso_date)
                print(f"[deadline-extract] Matched: {match} → Parsed: {iso_date}")
            
        except Exception as e:
            print(f"[deadline-extract] Failed to parse '{match}': {e}")
            continue
    
    # Remove duplicates and sort
    unique_dates = list(dict.fromkeys(parsed_dates))
    unique_dates.sort()
    
    print(f"[deadline-extract] Final extracted dates: {unique_dates}")
    return unique_dates

def extract_tags_from_text(text: str, summary: str) -> List[str]:
    """
    Extract relevant tags from text and summary using regex patterns and keyword analysis.
    """
    
    tags = set()
    
    # Combine text and summary for analysis
    combined_text = f"{text} {summary}".lower()
    
    # Extract course codes (e.g., CISC 235, MATH 101, etc.)
    course_patterns = [
        r"\bA-Z]{2,4}\s+\d{3,4}\b",  # CISC 23511, etc.
        r"\bA-Z]{2,4}\d{3,4}\b",     # CISC235 MATH101, etc.
    ]
    
    for pattern in course_patterns:
        matches = re.findall(pattern, f"{text} {summary}", re.IGNORECASE)
        for match in matches:
            # Clean up the match
            clean_match = re.sub(r'\s+', ' ', match.strip())
            tags.add(clean_match.upper())
    
    # Extract key academic terms
    academic_terms = [
        'assignment', 'homework', 'project', 'quiz', 'exam', 'test', 'midterm', 'final',
        'lecture', 'lab', 'tutorial', 'workshop', 'seminar', 'presentation', 'paper',
        'essay', 'report', 'research', 'analysis', 'algorithm', 'data structure',
        'recursion', 'object-oriented', 'database', 'network', 'security', 'web',
        'machine learning', 'artificial intelligence', 'programming', 'software',
        'hardware', 'operating system', 'compiler', 'interpreter', 'debugging',
        'testing', 'deployment', 'version control', 'git', 'agile', 'scrum'
    ]
    
    # Find academic terms in the text
    for term in academic_terms:
        if term.lower() in combined_text:
            # Capitalize first letter for display
            tags.add(term.title())
    
    # Extract capitalized words that might be important (simple heuristic)
    words = re.findall(r"\b[A-Z][a-z]{2,}\b", f"{text} {summary}")
    word_counts = Counter(words)
    
    # Add the most frequent capitalized words (excluding common words)
    common_words = {'The', 'This', 'That', 'With', 'From', 'When', 'Where', 'What', 'How', 'Why'}
    for word, count in word_counts.most_common(5):
        if word not in common_words and len(word) > 3:
            tags.add(word)
    
    # Limit to top 6 tags
    return list(tags)[:6]

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
            summary=None,
            user_id=uuid.uuid4(),  # Generate a default user_id
            course_id=uuid.uuid4()  # Generate a default course_id
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
async def summarize_file(file_id: int, db: Session = Depends(get_db)):
    try:
        file_entry = db.query(FileModel).filter(FileModel.id == file_id).first()
        if not file_entry:
            raise HTTPException(status_code=404, detail="File not found")
        file_path = Path('uploads') / file_entry.filename
        text = extract_text_from_file(file_path)
        chunks = chunk_text(text)
        summary = summarize_chunks(chunks)
        deadlines_from_text = extract_dates_from_text(text)
        deadlines_from_summary = extract_dates_from_text(summary)
        all_deadlines = list(set(deadlines_from_text + deadlines_from_summary))
        all_deadlines.sort()
        tags = extract_tags_from_text(text, summary)
        file_entry.summary = summary
        file_entry.deadlines = all_deadlines
        file_entry.tags = tags
        db.commit()
        db.refresh(file_entry)
        # Embed with user_id and course_id
        user_id = getattr(file_entry, 'user_id', None)
        course_id = getattr(file_entry, 'course_id', None)
        from services.embedding_service import create_file_embeddings
        create_file_embeddings(file_entry.id, file_entry.filename, text, user_id=user_id, course_id=course_id)
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

@router.get("/files", response_model=List[FileOut])
def get_files_explicit(db: Session = Depends(get_db)):
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
                deadline=deadline,
                deadlines=f.deadlines or [],
                tags=f.tags or []
            ))
        return result
    except Exception as e:
        print("GET FILES ERROR:", e)
        import traceback; traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

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
                deadline=deadline,
                deadlines=f.deadlines or [],
                tags=f.tags or []
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
    # Delete embeddings for this file
    try:
        delete_file_embeddings(file_id)
    except Exception as e:
        print(f"Error deleting embeddings for file_id {file_id}: {e}")
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

@router.post("/test-deadline-extraction")
def test_deadline_extraction(request: dict):
    """
    Test endpoint for deadline extraction. Send a JSON with 'text' field.
    Example: {"text": "Assignment 1 is due on January 26, 2024. Quiz 1 will be held on Feb 2."}
    """
    text = request.get("text", "")
    if not text:
        return {"error": "No text provided"}
    
    deadlines = extract_dates_from_text(text)
    return {
        "input_text": text,
        "extracted_deadlines": deadlines,
        "count": len(deadlines)
    } 

@router.patch("/{file_id}")
def update_file(file_id: int, request: UpdateFileRequest, db: Session = Depends(get_db)):
    try:
        # Validate filename
        if not request.filename.strip():
            raise HTTPException(status_code=400, detail="Filename cannot be empty")
        
        filename = request.filename.strip()
        
        # Check if file exists
        file_entry = db.query(FileModel).filter(FileModel.id == file_id).first()
        if not file_entry:
            raise HTTPException(status_code=404, detail="File not found")
        
        # Check for duplicate filenames (optional)
        existing_file = db.query(FileModel).filter(
            FileModel.filename == filename,
            FileModel.id != file_id
        ).first()
        if existing_file:
            raise HTTPException(status_code=490, detail="A file with this name already exists")
        
        # Update filename
        old_filename = file_entry.filename
        file_entry.filename = filename
        
        # Update the actual file on disk if it exists
        old_file_path = Path('uploads') / old_filename
        new_file_path = Path('uploads') / filename
        
        if old_file_path.exists():
            try:
                old_file_path.rename(new_file_path)
            except Exception as e:
                print(f"Error renaming file on disk: {e}")
                # Continue with DB update anyway
        
        db.commit()
        db.refresh(file_entry)
        
        # Return updated file in FileOut format
        deadline_obj = (
            db.query(Deadline)
            .filter(Deadline.file_id == file_entry.id)
            .order_by(Deadline.due_date.asc())
            .first()
        )
        deadline = deadline_obj.due_date.isoformat() if deadline_obj else None
        
        return FileOut(
            id=file_entry.id,
            filename=file_entry.filename,
            summary=file_entry.summary,
            deadline=deadline,
            deadlines=file_entry.deadlines or [],
            tags=file_entry.tags or []
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"UPDATE FILE ERROR: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Failed to update file") 