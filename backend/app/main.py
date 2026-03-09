"""
Главен модул на уеб платформата за анализ на техника при гребане.
"""
from pathlib import Path
from dotenv import load_dotenv

# Зареждане на .env от backend/
_env_path = Path(__file__).resolve().parent.parent / ".env"
if _env_path.exists():
    load_dotenv(dotenv_path=_env_path)
else:
    load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.routers import upload, analyze, results, reference, chat

from config import UPLOAD_DIR, OUTPUT_DIR

app = FastAPI(
    title="Rowing Technique Analysis Platform",
    description="Платформа за анализ на техника при гребане чрез компютърно зрение",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload.router, prefix="/api/upload", tags=["Upload"])
app.include_router(analyze.router, prefix="/api/analyze", tags=["Analysis"])
app.include_router(results.router, prefix="/api/results", tags=["Results"])
app.include_router(reference.router, prefix="/api/reference", tags=["Reference Model"])
app.include_router(chat.router, prefix="/api/chat", tags=["Chatbot"])


@app.get("/api")
async def root():
    return {"message": "Rowing Technique Analysis API", "version": "1.0.0"}


@app.get("/api/reference/values")
async def get_reference_values():
    """Фиксирани референтни стойности (fallback)."""
    from analysis.reference import REFERENCE_VALUES
    return REFERENCE_VALUES


from pathlib import Path
FRONTEND_DIR = Path(__file__).resolve().parent.parent.parent / "frontend"
if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
