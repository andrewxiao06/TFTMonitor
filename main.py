"""TFT Monitor - FastAPI entrypoint."""
import logging

from fastapi import FastAPI

from config import get_settings
from api.routes import games

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

settings = get_settings()
app = FastAPI(title="TFT Monitor", version="0.1.0")

app.include_router(games.router, prefix="/games", tags=["games"])


@app.get("/")
def read_root():
    return {"status": 200, "content": "TFT Monitor is running"}


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "riot_api_key_set": bool(settings.riot_api_key),
        "region": settings.riot_region,
        "platform": settings.riot_platform,
    }
