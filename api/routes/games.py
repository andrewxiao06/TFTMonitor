"""Routes for TFT game history and counts."""
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query

from config import get_settings
from models.schemas import GameCount, MatchSummary, SessionInfo
from services import riot_api

router = APIRouter()
settings = get_settings()

# In-memory session state — reset when the app restarts
_session_start: datetime = datetime.now(tz=timezone.utc)


def _get_puuid() -> str:
    """Resolve PUUID or raise a clean HTTP error."""
    try:
        return riot_api.resolve_puuid()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Riot API error: {e}")


@router.get("/count", response_model=GameCount)
def get_game_count():
    """Return total games, games today, and games this session."""
    puuid = _get_puuid()
    try:
        return riot_api.get_game_count(
            puuid=puuid,
            region=settings.riot_region,
            session_start=_session_start,
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Riot API error: {e}")


@router.get("/session", response_model=SessionInfo)
def get_session():
    """Return info about the current monitoring session."""
    puuid = _get_puuid()
    try:
        match_ids = riot_api.get_match_ids(
            puuid=puuid,
            region=settings.riot_region,
            count=100,
            start_time=int(_session_start.timestamp()),
        )
        return SessionInfo(
            session_start=_session_start,
            games_this_session=len(match_ids),
            puuid=puuid,
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Riot API error: {e}")


@router.get("/history", response_model=list[MatchSummary])
def get_match_history(count: int = Query(default=10, ge=1, le=100)):
    """
    Return recent TFT match summaries.
    Use ?count=N to request 1–100 matches (default 10).
    """
    puuid = _get_puuid()
    try:
        match_ids = riot_api.get_match_ids(
            puuid=puuid,
            region=settings.riot_region,
            count=count,
        )
        summaries = []
        for match_id in match_ids:
            detail = riot_api.get_match_detail(match_id, settings.riot_region)
            summary = riot_api.parse_match_summary(detail, puuid)
            summaries.append(summary)
        return summaries
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Riot API error: {e}")
