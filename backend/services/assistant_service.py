import os
import openai
from typing import List
from models.deadline import Deadline
from dotenv import load_dotenv

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

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
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a helpful academic assistant."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=300,
        temperature=0.3
    )
    return response.choices[0].message["content"].strip() 