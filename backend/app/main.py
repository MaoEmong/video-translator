from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.router import api_router
from app.config import get_settings

settings = get_settings()

app = FastAPI(
    title="Video Translator API",
    version="0.1.0",
    description="Asynchronous video transcription and subtitle translation service",
)
app.include_router(api_router, prefix=settings.api_v1_prefix)

frontend_directory = Path(__file__).resolve().parents[2] / "frontend"
if frontend_directory.exists():
    app.mount("/", StaticFiles(directory=frontend_directory, html=True), name="frontend")
