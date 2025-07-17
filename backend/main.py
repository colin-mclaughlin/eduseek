import sys
import asyncio
import os

# Comprehensive Windows compatibility fixes for Playwright
if sys.platform.startswith("win"):
    print("[DEBUG] Windows detected, setting up event loop policy...")
    
    # Force creation of event loop before any imports
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        print("[DEBUG] Created new event loop")
    except Exception as e:
        print(f"[DEBUG] Failed to create new event loop: {e}")
    
    try:
        # Try WindowsSelectorEventLoopPolicy first
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        print("[DEBUG] Set WindowsSelectorEventLoopPolicy")
    except Exception as e:
        print(f"[DEBUG] WindowsSelectorEventLoopPolicy failed: {e}")
        try:
            # Fallback to WindowsProactorEventLoopPolicy
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
            print("[DEBUG] Set WindowsProactorEventLoopPolicy")
        except Exception as e2:
            print(f"[DEBUG] WindowsProactorEventLoopPolicy failed: {e2}")
    
    # Set environment variables for better Windows compatibility
    os.environ["PYTHONPATH"] = os.getcwd()
    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = "0"  # Force Playwright to use system browsers
    print(f"[DEBUG] Set PYTHONPATH to: {os.getcwd()}")
    print("[DEBUG] Set PLAYWRIGHT_BROWSERS_PATH to 0")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers.files import router as files_router
from routers.assistant import router as assistant_router
from routers.lms import router as lms_router

app = FastAPI()

# Enable CORS for frontend dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
print("CORS enabled for:", ["http://localhost:5173", "http://localhost:3000"])

# Change router prefix to /api for all files endpoints, including /import/lms
app.include_router(files_router, prefix="/api", tags=["Files"])
app.include_router(assistant_router)
app.include_router(lms_router, prefix="/api", tags=["LMS"])

@app.get("/ping")
async def ping():
    return {"message": "EduSeek backend is alive!"} 