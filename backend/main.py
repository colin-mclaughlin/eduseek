import sys
if sys.platform.startswith("win"):
    import asyncio
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        print("WindowsSelectorEventLoopPolicy set for Playwright compatibility.")
    except Exception as e:
        print(f"Could not set WindowsSelectorEventLoopPolicy: {e}")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers.files import router as files_router
from routers.assistant import router as assistant_router
from routers.lms import router as lms_router
import os

# Set environment variables for better Windows compatibility
if sys.platform.startswith("win"):
    os.environ["PYTHONPATH"] = os.getcwd()
    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = "0"  # Force Playwright to use system browsers
    print(f"Set PYTHONPATH to: {os.getcwd()}")
    print("Set PLAYWRIGHT_BROWSERS_PATH to 0")

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