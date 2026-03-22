"""TFT Monitor - FastAPI entrypoint."""
import logging
import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI

from config import get_settings
from api.routes import games, limits
from services import lcu_monitor
from services.play_limiter import on_game_end

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

settings = get_settings()

# Wire the play limiter callback into the LCU monitor
lcu_monitor.set_on_game_end(on_game_end)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start the LCU monitor in a background thread on app startup."""
    monitor_thread = threading.Thread(
        target=lcu_monitor.start_monitor,
        daemon=True,
    )
    monitor_thread.start()
    logging.getLogger(__name__).info("LCU monitor thread started.")
    yield
    logging.getLogger(__name__).info("Shutting down.")


app = FastAPI(title="TFT Monitor", version="0.1.0", lifespan=lifespan)

app.include_router(games.router, prefix="/games", tags=["games"])
app.include_router(limits.router, prefix="/limits", tags=["limits"])


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
        "session_games": lcu_monitor.session_game_count,
    }
