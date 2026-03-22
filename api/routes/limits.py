"""Routes for viewing and updating play-time limits."""
from fastapi import APIRouter
from pydantic import BaseModel

from config import get_settings

router = APIRouter()
settings = get_settings()


class LimitsResponse(BaseModel):
    daily_game_cap: int
    session_game_cap: int
    enable_notification: bool
    enable_force_close: bool
    force_close_delay_seconds: int


@router.get("/", response_model=LimitsResponse)
def get_limits():
    """Return the current play-time limit configuration."""
    return LimitsResponse(
        daily_game_cap=settings.daily_game_cap,
        session_game_cap=settings.session_game_cap,
        enable_notification=settings.enable_notification,
        enable_force_close=settings.enable_force_close,
        force_close_delay_seconds=settings.force_close_delay_seconds,
    )
