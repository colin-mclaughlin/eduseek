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

def query_files(query: str, course_filter: str = None, user_id: int = None, course_id: int = None) -> Dict[str, Any]:
    """
    Query the embedded files and generate a contextual response.

    Args:
        query: The user's question
        course_filter: Optional course name to filter results

    Returns:
        Dict containing answer and sources
    """
    try:
        # Get the ChromaDB collection
        db = get_or_create_chroma_collection()

        # Search for relevant documents
        print(f"[Assistant] Query: {query}")
        results = db.similarity_search_with_score(query, k=5)
        print(f"[Assistant] Retrieved {len(results)} results from ChromaDB.")
        filters = {}
        if user_id is not None:
            filters['user_id'] = str(user_id)
        if course_id is not None:
            filters['course_id'] = str(course_id)
        print(f"[Assistant] Filters used: {filters}")
        # Filter results by user_id and course_id if present
        if filters:
            def match_filters(meta):
                for k, v in filters.items():
                    if meta.get(k) != v:
                        return False
                return True
            results = [(doc, score) for doc, score in results if match_filters(doc.metadata)]
        for idx, (doc, score) in enumerate(results):
            print(f"[Assistant] Result {idx}: score={score}, metadata={doc.metadata}")

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
        print(f"Error in query_files: {e}")
        return {
            "answer": "Sorry, I encountered an error while processing your question. Please try again.",
            "sources": []
        } 