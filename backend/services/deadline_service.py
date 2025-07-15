import os
import openai
from typing import List, Dict
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from core.database import SessionLocal
from models.deadline import Deadline, DeadlineSource
from sqlalchemy import and_
from uuid import UUID

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

def extract_deadlines_from_text(text: str) -> List[Dict]:
    prompt = (
        "Extract all assignment, quiz, test, and project deadlines with dates and titles from the following text. "
        "Return a JSON array where each item has: 'title', 'due_date' (ISO 8601 format), and 'source' (always 'file'). "
        "If no deadlines are found, return an empty array.\n\nText:\n" + text
    )
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are an assistant that extracts academic deadlines from course documents."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=512,
        temperature=0.2
    )
    import json
    import re
    content = response.choices[0].message["content"].strip()
    match = re.search(r'\[.*\]', content, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except Exception:
            pass
    try:
        return json.loads(content)
    except Exception:
        return []

def save_deadlines(deadlines: List[dict], user_id: UUID, course_id: UUID, file_id: UUID) -> None:
    db: Session = SessionLocal()
    try:
        for d in deadlines:
            # Check for duplicate
            exists = db.query(Deadline).filter(
                and_(
                    Deadline.title == d["title"],
                    Deadline.due_date == d["due_date"],
                    Deadline.user_id == user_id
                )
            ).first()
            if exists:
                continue
            deadline = Deadline(
                user_id=user_id,
                course_id=course_id,
                file_id=file_id,
                title=d["title"],
                due_date=d["due_date"],
                source=DeadlineSource.file
            )
            db.add(deadline)
        db.commit()
    finally:
        db.close() 