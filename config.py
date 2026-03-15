from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Riot API
    riot_api_key: str = ""
    riot_region: str = "americas"       # americas, europe, asia, sea
    riot_platform: str = "na1"          # na1, euw1, kr, etc.

    # Player identity - provide puuid directly, or game_name + tag_line
    puuid: Optional[str] = None
    game_name: Optional[str] = None
    tag_line: Optional[str] = None

    # Play limits
    daily_game_cap: int = 10
    session_game_cap: int = 5
    enable_notification: bool = True
    enable_force_close: bool = False
    force_close_delay_seconds: int = 8

    # Match history polling interval (seconds)
    match_poll_interval: int = 90

    # API server
    host: str = "127.0.0.1"
    port: int = 8000


@lru_cache
def get_settings() -> Settings:
    return Settings()


