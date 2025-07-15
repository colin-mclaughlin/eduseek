import os
from typing import List, Dict
from langchain.vectorstores import Chroma
from langchain.embeddings import OpenAIEmbeddings
from langchain.schema import Document
from dotenv import load_dotenv

load_dotenv()

CHROMA_PERSIST_DIR = os.path.abspath("chroma_db")
COLLECTION_NAME = "eduseek"

openai_api_key = os.getenv("OPENAI_API_KEY")


def get_or_create_chroma_collection():
    embeddings = OpenAIEmbeddings(openai_api_key=openai_api_key, model="text-embedding-ada-002")
    db = Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=embeddings,
        persist_directory=CHROMA_PERSIST_DIR
    )
    return db


def embed_chunks(chunks: List[str], metadata: dict):
    db = get_or_create_chroma_collection()
    docs = [Document(page_content=chunk, metadata=metadata) for chunk in chunks]
    db.add_documents(docs)
    db.persist() 