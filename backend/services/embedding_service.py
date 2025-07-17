import os
from typing import List, Dict
from dotenv import load_dotenv

try:
    from langchain_openai import OpenAIEmbeddings
except ImportError:
    from langchain_community.embeddings import OpenAIEmbeddings

try:
    from langchain_chroma import Chroma
except ImportError:
    from langchain_community.vectorstores import Chroma

from langchain.schema import Document

load_dotenv()

CHROMA_PERSIST_DIR = os.path.abspath("chroma_db")
COLLECTION_NAME = "eduseek"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


def get_or_create_chroma_collection():
    """
    Get or create a ChromaDB collection for storing file embeddings.
    """
    embeddings = OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY, model="text-embedding-ada-002")
    db = Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=embeddings,
        persist_directory=CHROMA_PERSIST_DIR
    )
    return db


def embed_chunks(chunks: List[str], metadata: dict):
    """
    Embed text chunks and store them in ChromaDB with associated metadata.
    """
    db = get_or_create_chroma_collection()
    docs = [Document(page_content=chunk, metadata=metadata) for chunk in chunks]
    for doc in docs:
        print(f"[EmbeddingService] Embedding chunk with metadata: {doc.metadata}")
    print(f"[EmbeddingService] Embedding {len(docs)} chunks with metadata: {metadata}")
    db.add_documents(docs)
    db.persist()


def delete_file_embeddings(file_id: int):
    """
    Delete all embeddings for a specific file from ChromaDB by file_id.
    """
    db = get_or_create_chroma_collection()
    # Always use string for file_id in metadata filter
    str_file_id = str(file_id)
    db.delete(where={"file_id": str_file_id})
    db.persist()
    print(f"[EmbeddingService] Deleted embeddings for file_id: {str_file_id}")


def create_file_embeddings(file_id: int, filename: str, text: str, user_id: int = None, course_id: int = None):
    """
    Create embeddings for a file's text content and store them in ChromaDB.
    """
    from services.file_service import chunk_text
    # Remove any existing embeddings for this file
    delete_file_embeddings(file_id)
    # Chunk the text
    chunks = chunk_text(text)
    # Create documents with metadata
    docs = []
    for i, chunk in enumerate(chunks):
        chunk_metadata = {
            "file_id": str(file_id),
            "filename": filename,
            "chunk_index": i
        }
        if user_id is not None:
            chunk_metadata["user_id"] = str(user_id)
        if course_id is not None:
            chunk_metadata["course_id"] = str(course_id)
        docs.append(Document(page_content=chunk, metadata=chunk_metadata))
        print(f"[EmbeddingService] Embedding chunk with metadata: {chunk_metadata}")
    print(f"[EmbeddingService] Embedding {len(docs)} chunks for file_id={file_id}, filename={filename}")
    if docs:
        print(f"[EmbeddingService] Sample metadata: {docs[0].metadata}")
    # Add to ChromaDB
    db = get_or_create_chroma_collection()
    db.add_documents(docs)
    db.persist()


def prune_stale_embeddings(valid_file_ids: List[int]):
    """
    Remove all embeddings from ChromaDB that do not match any file_id in valid_file_ids.
    Useful for cleaning up after file deletions.
    """
    db = get_or_create_chroma_collection()
    # Chroma does not support direct 'not in' queries, so fetch all and filter
    all_docs = db.get()
    stale_ids = [doc['id'] for doc in all_docs['metadatas'] if doc.get('file_id') not in map(str, valid_file_ids)]
    if stale_ids:
        db.delete(ids=stale_ids)
        db.persist() 