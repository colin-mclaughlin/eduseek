import os
from pathlib import Path
from typing import List
from fastapi import UploadFile
from langchain.document_loaders import PyPDFLoader, UnstructuredWordDocumentLoader, UnstructuredPowerPointLoader, TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
import openai
from dotenv import load_dotenv

load_dotenv()

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai.api_key = OPENAI_API_KEY

def save_uploaded_file(file: UploadFile) -> Path:
    file_path = UPLOAD_DIR / file.filename
    with open(file_path, "wb") as f:
        f.write(file.file.read())
    return file_path

def extract_text_from_file(file_path: Path) -> str:
    ext = file_path.suffix.lower()
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

def chunk_text(text: str) -> List[str]:
    splitter = RecursiveCharacterTextSplitter(chunk_size=2000, chunk_overlap=200)
    return splitter.split_text(text)

def summarize_chunks(chunks: List[str]) -> str:
    summaries = []
    for chunk in chunks:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Summarize the following academic document chunk."},
                {"role": "user", "content": chunk}
            ],
            max_tokens=256,
            temperature=0.3
        )
        summary = response.choices[0].message["content"].strip()
        summaries.append(summary)
    return "\n".join(summaries) 