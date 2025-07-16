from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers.files import router as files_router
from routers.assistant import router as assistant_router

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

app.include_router(files_router, prefix="/api/files", tags=["Files"])
app.include_router(assistant_router)

@app.get("/ping")
async def ping():
    return {"message": "EduSeek backend is alive!"} 