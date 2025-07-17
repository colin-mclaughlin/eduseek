import os
from pathlib import Path
from typing import List
from fastapi import UploadFile
from langchain_community.document_loaders import PyPDFLoader, UnstructuredPowerPointLoader, TextLoader, UnstructuredWordDocumentLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
import traceback

# Requires: pip install python-docx

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)

async def save_uploaded_file(file: UploadFile) -> Path:
    file_path = UPLOAD_DIR / file.filename
    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)
    return file_path

def extract_text_from_file(file_path: Path) -> str:
    ext = file_path.suffix.lower()
    print(f"[extract_text_from_file] Detected file type: {ext} for {file_path}")
    try:
        if ext == ".pdf":
            loader = PyPDFLoader(str(file_path))
        elif ext == ".docx":
            loader = UnstructuredWordDocumentLoader(str(file_path))
        elif ext == ".pptx":
            loader = UnstructuredPowerPointLoader(str(file_path))
        elif ext == ".txt":
            loader = TextLoader(str(file_path))
        else:
            raise ValueError(f"Unsupported file type: {ext}")
        docs = loader.load()
        return "\n".join(doc.page_content for doc in docs)
    except Exception as e:
        print(f"[extract_text_from_file] Error processing {file_path}: {e}")
        traceback.print_exc()
        raise

def chunk_text(text: str) -> List[str]:
    splitter = RecursiveCharacterTextSplitter(chunk_size=2000, chunk_overlap=200)
    return splitter.split_text(text)

def summarize_chunks(chunks: List[str]) -> str:
    summaries = []
    for chunk in chunks:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Summarize the following academic document chunk."},
                {"role": "user", "content": chunk}
            ],
            max_tokens=256,
            temperature=0.3
        )
        summary = response.choices[0].message.content.strip()
        summaries.append(summary)
    return "\n".join(summaries) 