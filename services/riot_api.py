"""Riot API client for TFT match history and player lookup."""
import time
import logging
from datetime import datetime, timezone
from typing import Optional

from riotwatcher import TftWatcher, ApiError

from config import get_settings
from models.schemas import MatchSummary, GameCount

logger = logging.getLogger(__name__)

settings = get_settings()

_watcher: Optional[TftWatcher] = None


def get_watcher() -> TftWatcher:
    """Return a shared TftWatcher instance."""
    global _watcher
    if _watcher is None:
        if not settings.riot_api_key:
            raise ValueError("RIOT_API_KEY is not set in .env")
        _watcher = TftWatcher(settings.riot_api_key)
    return _watcher


def get_puuid(game_name: str, tag_line: str, region: str) -> str:
    """
    Look up a player's PUUID by Riot ID (game_name#tag_line).
    region should be one of: americas, europe, asia, sea
    """
    watcher = get_watcher()
    try:
        account = watcher.account.by_riot_id(region, game_name, tag_line)
        return account["puuid"]
    except ApiError as e:
        logger.error("Failed to get PUUID for %s#%s: %s", game_name, tag_line, e)
        raise


def resolve_puuid() -> str:
    """
    Return the PUUID from settings — either stored directly or looked up
    via game_name + tag_line.
    """
    if settings.puuid:
        return settings.puuid
    if settings.game_name and settings.tag_line:
        return get_puuid(settings.game_name, settings.tag_line, settings.riot_region)
    raise ValueError(
        "Set either PUUID or both GAME_NAME and TAG_LINE in your .env file."
    )


def get_match_ids(
    puuid: str,
    region: str,
    count: int = 20,
    start_time: Optional[int] = None,
) -> list[str]:
    """
    Fetch a list of recent TFT match IDs for a given PUUID.
    start_time is an optional Unix epoch (seconds) to filter from.
    """
    watcher = get_watcher()
    try:
        match_ids = watcher.match.by_puuid(
            region=region,
            puuid=puuid,
            count=count,
            start_time=start_time,
        )
        return match_ids
    except ApiError as e:
        logger.error("Failed to get match IDs for puuid %s: %s", puuid, e)
        raise


def get_match_detail(match_id: str, region: str) -> dict:
    """Fetch full match data for a given match ID."""
    watcher = get_watcher()
    try:
        return watcher.match.by_id(region=region, match_id=match_id)
    except ApiError as e:
        logger.error("Failed to get match detail for %s: %s", match_id, e)
        raise


def parse_match_summary(match_data: dict, puuid: str) -> MatchSummary:
    """
    Extract a MatchSummary from raw Riot match data for a specific player.
    """
    info = match_data["info"]
    participants = info["participants"]

    player = next((p for p in participants if p["puuid"] == puuid), None)
    if player is None:
        raise ValueError(f"PUUID {puuid} not found in match participants")

    game_datetime = datetime.fromtimestamp(
        info["game_datetime"] / 1000, tz=timezone.utc
    )

    return MatchSummary(
        match_id=match_data["metadata"]["match_id"],
        game_datetime=game_datetime,
        placement=player["placement"],
        augments=player.get("augments", []),
        level=player.get("level", 0),
    )


def get_game_count(
    puuid: str,
    region: str,
    session_start: datetime,
) -> GameCount:
    """
    Return total recent games, games played today, and games this session.
    """
    now = datetime.now(tz=timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    # Fetch up to 100 matches within today
    today_ids = get_match_ids(
        puuid=puuid,
        region=region,
        count=100,
        start_time=int(today_start.timestamp()),
    )

    # Fetch matches since session started
    session_ids = get_match_ids(
        puuid=puuid,
        region=region,
        count=100,
        start_time=int(session_start.timestamp()),
    )

    # Total uses last 100 matches as a reasonable "total recent" figure
    total_ids = get_match_ids(puuid=puuid, region=region, count=100)

    return GameCount(
        total=len(total_ids),
        today=len(today_ids),
        this_session=len(session_ids),
    )
