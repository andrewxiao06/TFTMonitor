"""Pydantic models for API request/response shapes."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class MatchSummary(BaseModel):
    match_id: str
    game_datetime: datetime
    placement: int
    augments: list[str]
    level: int


class GameCount(BaseModel):
    total: int
    today: int
    this_session: int


class SessionInfo(BaseModel):
    session_start: datetime
    games_this_session: int
    puuid: Optional[str] = None


class PlayerInfo(BaseModel):
    puuid: str
    game_name: str
    tag_line: str
    region: str
