from typing import Literal
from fastapi import HTTPException
import asyncio
import sys
import os
import time
import uuid
from pathlib import Path
from sqlalchemy.orm import Session
from core.database import SessionLocal
from models.file import File as FileModel
from services.file_service import extract_text_from_file, chunk_text, summarize_chunks
from services.embedding_service import create_file_embeddings

# Supported LMS types (expand as needed)
LMS_TYPE = Literal["brightspace", "moodle", "canvas"]

class LMSScraperError(Exception):
    pass

BRIGHTSPACE_URL = "https://onq.queensu.ca/"

def get_db():
    db = SessionLocal()
    try:
        return db
    finally:
        db.close()

def create_mock_file_content(filename: str) -> str:
    """Generate realistic mock content based on filename"""
    base_name = filename.split('.')[0].lower()
    
    if 'lecture' in base_name:
        return f"""
Lecture 1: Introduction to Course Material

Welcome to this comprehensive course on academic content. This lecture covers the fundamental concepts that will be essential for your understanding throughout the semester.

Key Topics Covered:
- Basic principles and methodologies
- Historical context and background
- Practical applications and examples
- Important definitions and terminology

Learning Objectives:
By the end of this lecture, students should be able to:
1. Understand the core concepts presented
2. Apply basic principles to simple problems
3. Recognize key terminology and definitions
4. Prepare for upcoming assignments and assessments

Important Dates:
- Assignment 1 due: January 15, 2024
- Quiz 1 scheduled: January 20, 2024
- Midterm exam: February 10, 2024

Please review this material before the next lecture and complete the assigned readings.
        """
    elif 'assignment' in base_name:
        return f"""
Assignment 1: Guidelines and Requirements

This assignment will test your understanding of the material covered in the first few weeks of the course.

Assignment Details:
- Due Date: January 15, 2024
- Weight: 15% of final grade
- Format: Written report (1500-2000 words)
- Submission: Online through the course portal

Requirements:
1. Clear introduction and thesis statement
2. Well-structured arguments with evidence
3. Proper citations and references
4. Conclusion that summarizes key points

Grading Criteria:
- Content and analysis (40%)
- Structure and organization (25%)
- Writing quality and clarity (20%)
- Citations and references (15%)

Late submissions will be penalized 10% per day. Extensions may be granted in exceptional circumstances with prior approval.
        """
    elif 'syllabus' in base_name:
        return f"""
Course Syllabus: Academic Content and Structure

Course Overview:
This course provides a comprehensive introduction to the subject matter, covering both theoretical foundations and practical applications.

Course Schedule:
Week 1-2: Introduction and Basic Concepts
Week 3-4: Core Principles and Methods
Week 5-6: Advanced Topics and Applications
Week 7-8: Review and Assessment

Assessment Structure:
- Assignments: 40% (4 assignments, 10% each)
- Quizzes: 20% (4 quizzes, 5% each)
- Midterm Exam: 20%
- Final Exam: 20%

Important Deadlines:
- Assignment 1: January 15, 2024
- Assignment 2: February 15, 2024
- Assignment 3: March 15, 2024
- Assignment 4: April 15, 2024
- Midterm Exam: February 10, 2024
- Final Exam: April 25, 2024

Office Hours: Tuesdays and Thursdays, 2:00-4:00 PM
        """
    elif 'lab' in base_name:
        return f"""
Lab 1: Practical Application and Hands-on Experience

This laboratory session will provide hands-on experience with the concepts discussed in the lectures.

Lab Objectives:
- Apply theoretical concepts in a practical setting
- Develop technical skills and competencies
- Practice problem-solving and critical thinking
- Prepare for upcoming assessments

Lab Schedule:
- Duration: 3 hours
- Location: Computer Lab 101
- Required Materials: Laptop, course textbook, calculator

Pre-lab Requirements:
- Complete assigned readings
- Review lecture notes from previous week
- Bring necessary materials and equipment

Post-lab Deliverables:
- Lab report (due within 1 week)
- Code/analysis files (if applicable)
- Reflection on learning outcomes

Safety Guidelines:
- Follow all laboratory safety protocols
- Report any incidents immediately
- Maintain clean and organized workspace
        """
    else:
        return f"""
Document: {filename}

This is a sample document containing academic content related to the course material. It includes various topics, concepts, and information that students need to understand and apply throughout their studies.

Content includes:
- Theoretical frameworks and models
- Practical examples and case studies
- Important definitions and terminology
- References to additional resources

Please review this document carefully and ensure you understand all concepts before proceeding to the next section.
        """

async def scrape_lms_files(lms_type: LMS_TYPE, username: str, password: str) -> dict:
    print(f"[LMS DEBUG] Starting scrape for {lms_type}")
    print(f"[LMS DEBUG] Platform: {sys.platform}")
    print(f"[LMS DEBUG] Python version: {sys.version}")
    print(f"[LMS DEBUG] Current working directory: {os.getcwd()}")
    
    if lms_type != "brightspace":
        raise NotImplementedError(f"LMS type '{lms_type}' is not supported yet.")
    
    try:
        print("[LMS DEBUG] Using mock implementation with real file processing")
        
        # Simulate the LMS scraping process
        print("[LMS DEBUG] Simulating login to Brightspace...")
        await asyncio.sleep(2)  # Simulate network delay
        
        # Simulate login validation
        if not username or not password:
            print("[LMS DEBUG] Missing credentials")
            raise HTTPException(status_code=401, detail="Missing username or password")
        
        # Simulate specific login failure for testing
        if username == "fail@queensu.ca":
            print("[LMS DEBUG] Simulating login failure")
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        print("[LMS DEBUG] Login successful, navigating to course content...")
        await asyncio.sleep(1)  # Simulate page load
        
        print("[LMS DEBUG] Scanning for course files...")
        await asyncio.sleep(1)  # Simulate file discovery
        
        # Mock file list based on username
        mock_files = [
            f"Lecture_1_Introduction_{username.split('@')[0]}.pdf",
            f"Assignment_1_Guidelines_{username.split('@')[0]}.docx",
            f"Course_Syllabus_{username.split('@')[0]}.pdf",
            f"Lab_1_Instructions_{username.split('@')[0]}.pdf"
        ]
        
        print(f"[LMS DEBUG] Found {len(mock_files)} files")
        print(f"[LMS DEBUG] Files: {mock_files}")
        
        # Create LMS uploads directory
        lms_upload_dir = Path("uploads/lms")
        lms_upload_dir.mkdir(exist_ok=True, parents=True)
        print(f"[LMS DEBUG] Created LMS upload directory: {lms_upload_dir}")
        
        # Process files through the real pipeline
        processed_count = 0
        db = get_db()
        
        try:
            for filename in mock_files:
                print(f"[LMS DEBUG] Processing file: {filename}")
                
                # Create mock file with realistic content
                file_path = lms_upload_dir / filename
                content = create_mock_file_content(filename)
                
                # Write content to file (simulate different file types)
                if filename.endswith('.pdf'):
                    # For PDF, we'll create a text file that the PDF loader can handle
                    # In a real scenario, this would be an actual PDF
                    file_path = lms_upload_dir / filename.replace('.pdf', '.txt')
                    file_path.write_text(content)
                elif filename.endswith('.docx'):
                    # For DOCX, create a text file that the Word loader can handle
                    file_path = lms_upload_dir / filename.replace('.docx', '.txt')
                    file_path.write_text(content)
                else:
                    file_path.write_text(content)
                
                print(f"[LMS DEBUG] Created mock file: {file_path}")
                
                try:
                    # Extract text from file
                    print(f"[LMS DEBUG] Extracting text from {file_path}")
                    text = extract_text_from_file(file_path)
                    print(f"[LMS DEBUG] Extracted {len(text)} characters of text")
                    
                    # Create file entry in database
                    file_entry = FileModel(
                        filename=filename,
                        text=text,
                        summary=None,
                        user_id=uuid.uuid4(),
                        course_id=uuid.uuid4()
                    )
                    db.add(file_entry)
                    db.commit()
                    db.refresh(file_entry)
                    print(f"[LMS DEBUG] Saved file entry to database: {file_entry.id}")
                    
                    # Process text through the pipeline
                    print(f"[LMS DEBUG] Processing text through pipeline")
                    chunks = chunk_text(text)
                    summary = summarize_chunks(chunks)
                    
                    # Extract deadlines and tags (using functions from files.py)
                    from routers.files import extract_dates_from_text, extract_tags_from_text
                    deadlines_from_text = extract_dates_from_text(text)
                    deadlines_from_summary = extract_dates_from_text(summary)
                    all_deadlines = list(set(deadlines_from_text + deadlines_from_summary))
                    all_deadlines.sort()
                    tags = extract_tags_from_text(text, summary)
                    
                    # Update file entry with processed data
                    file_entry.summary = summary
                    file_entry.deadlines = all_deadlines
                    file_entry.tags = tags
                    db.commit()
                    db.refresh(file_entry)
                    
                    # Create embeddings
                    user_id = getattr(file_entry, 'user_id', None)
                    course_id = getattr(file_entry, 'course_id', None)
                    create_file_embeddings(file_entry.id, file_entry.filename, text, user_id=user_id, course_id=course_id)
                    
                    processed_count += 1
                    print(f"[LMS DEBUG] Successfully processed file: {filename}")
                    
                except Exception as file_error:
                    print(f"[LMS DEBUG] Error processing file {filename}: {file_error}")
                    continue
                    
        finally:
            db.close()
        
        print(f"[LMS DEBUG] Mock LMS import completed successfully")
        print(f"[LMS DEBUG] Processed {processed_count} out of {len(mock_files)} files")
        
        return {
            "status": "success",
            "message": f"Successfully imported and processed {processed_count} files from {lms_type}",
            "files": mock_files,
            "processed": processed_count,
            "details": {
                "lms_type": lms_type,
                "username": username,
                "files_count": len(mock_files),
                "processed_count": processed_count,
                "timestamp": time.time()
            }
        }
        
    except NotImplementedError as e:
        print(f"[LMS DEBUG] NotImplementedError: {e}")
        raise e
    except HTTPException as e:
        print(f"[LMS DEBUG] HTTPException: {e}")
        raise e
    except Exception as e:
        print(f"[LMS DEBUG] General exception: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Scraping failed: {str(e)}") 