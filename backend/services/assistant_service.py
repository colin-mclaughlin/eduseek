import os
from typing import List, Dict, Any
from models.deadline import Deadline
from services.embedding_service import get_or_create_chroma_collection
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=openai_api_key)

def generate_daily_plan(deadlines: List[Deadline]) -> str:
    if not deadlines:
        return "You have no upcoming deadlines. Use this time to review past material or get ahead!"
    # Format deadlines for the prompt
    formatted = "\n".join([
        f"- {d.title} (due {d.due_date.strftime('%Y-%m-%d')})" for d in deadlines
    ])
    prompt = (
        "You are an academic assistant. Given the following list of upcoming deadlines, "
        "generate a personalized daily study plan. Include what to focus on today, what's due soon, and how to prioritize tasks.\n\n"
        f"Deadlines:\n{formatted}"
    )
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a helpful academic assistant."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=300,
        temperature=0.3
    )
    return response.choices[0].message.content.strip()

def query_files(query: str, course_filter: str = None, user_id: int = None, course_id: str = None, file_id: str = None) -> Dict[str, Any]:
    """
    Query the embedded files and generate a contextual response.
    Args:
        query: The user's question
        course_filter: Optional course name to filter results
        course_id: Optional course ID to filter results
        file_id: Optional file ID to filter results
    Returns:
        Dict containing answer and sources
    """
    try:
        # Get the ChromaDB collection
        db = get_or_create_chroma_collection()
        print(f"[DEBUG] ChromaDB collection object: {db}")

        # Build filter for ChromaDB
        print(f"[DEBUG] file_id: {file_id} (type: {type(file_id)})")
        print(f"[DEBUG] course_id: {course_id} (type: {type(course_id)})")
        if file_id:
            chroma_filter = {"file_id": str(file_id)}
        elif course_id:
            chroma_filter = {"course_id": str(course_id)}
        else:
            chroma_filter = {}
        print(f"[Assistant] ChromaDB filter: {chroma_filter}")

        # Use the public retriever interface to ensure embedding function is used
        try:
            retriever = db.as_retriever(search_kwargs={"k": 5, "filter": chroma_filter})
            docs_and_scores = retriever.get_relevant_documents(query)
            # Simulate the previous (doc, score) tuple structure
            results = [(doc, 0.0) for doc in docs_and_scores]  # Score not available, set to 0.0
        except Exception as retriever_exc:
            print(f"[ERROR] Retriever interface failed: {retriever_exc}")
            # Fallback to direct _collection.query (may error if embedding function missing)
            try:
                query_result = db._collection.query(
                    query_texts=[query],
                    n_results=5,
                    where=chroma_filter
                )
                docs = query_result.get('documents', [[]])[0]
                metadatas = query_result.get('metadatas', [[]])[0]
                distances = query_result.get('distances', [[]])[0]
                results = []
                for doc, meta, dist in zip(docs, metadatas, distances):
                    class DocObj:
                        def __init__(self, page_content, metadata):
                            self.page_content = page_content
                            self.metadata = metadata
                    results.append((DocObj(doc, meta), dist))
            except Exception as fallback_exc:
                import traceback
                print(f"[ERROR] Both retriever and direct query failed: {fallback_exc}")
                traceback.print_exc()
                print(f"[ERROR CONTEXT] file_id: {file_id} (type: {type(file_id)})")
                print(f"[ERROR CONTEXT] course_id: {course_id} (type: {type(course_id)})")
                print(f"[ERROR CONTEXT] chroma_filter: {chroma_filter}")
                return {
                    "answer": "Sorry, I encountered an error while processing your question. Please try again.",
                    "sources": []
                }

        # Safeguard: Only include docs with a valid file_id
        results = [(doc, score) for doc, score in results if doc.metadata.get('file_id')]

        if not results:
            return {
                "answer": "I couldn't find any relevant information in your uploaded files. Try rephrasing your question or uploading more documents.",
                "sources": []
            }

        # Prepare context from top results
        context_parts = []
        sources = []

        for doc, score in results[:3]:  # Use top 3 results
            filename = doc.metadata.get('filename', 'Unknown file')
            chunk_text = doc.page_content[:50] + "..." if len(doc.page_content) > 50 else doc.page_content

            context_parts.append(f"From {filename}:\n{doc.page_content}")
            sources.append({
                "file_id": doc.metadata.get('file_id', ''),
                "filename": filename,
                "chunk_text": chunk_text,
                "similarity": round(1 - score, 3)  # Convert distance to similarity
            })

        context = "\n\n".join(context_parts)

        # Logging for debugging
        print("[Assistant] Context for prompt:", context)
        print("[Assistant] Sources:", sources)

        # Generate response using OpenAI
        prompt = f"""
You are EduSeek, an intelligent academic assistant. Answer the user's question based on the following context from their uploaded files.
Be helpful, accurate, and academic in tone. If the context doesn't contain enough information to answer the question, say so clearly.

Context from uploaded files:
{context}

User question: {query}

Answer:"""

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are EduSeek, a helpful academic assistant that answers questions based on uploaded course materials."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=800,
            temperature=0.3
        )
        answer = response.choices[0].message.content.strip()
        return {
            "answer": answer,
            "sources": sources
        }

    except Exception as e:
        import traceback
        print(f"[ERROR] Exception in query_files: {e}")
        traceback.print_exc()
        print(f"[ERROR CONTEXT] file_id: {file_id} (type: {type(file_id)})")
        print(f"[ERROR CONTEXT] course_id: {course_id} (type: {type(course_id)})")
        print(f"[ERROR CONTEXT] chroma_filter: {chroma_filter}")
        return {
            "answer": "Sorry, I encountered an error while processing your question. Please try again.",
            "sources": []
        } 