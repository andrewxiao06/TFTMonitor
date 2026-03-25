"""Play-time limiting logic — runs after each game ends."""
import logging
import time
import platform

import psutil

from config import get_settings
from services.notifier import send_notification

logger = logging.getLogger(__name__)

settings = get_settings()

RIOT_PROCESS_NAMES_WINDOWS = [
    "RiotClientUx.exe",
    "LeagueClientUx.exe",
    "League of Legends.exe",
]
RIOT_PROCESS_NAMES_MAC = [
    "RiotClientUx",
    "LeagueClientUx",
    "League of Legends",
]


def _get_process_names() -> list[str]:
    """Return the correct process names for the current OS."""
    if platform.system() == "Windows":
        return RIOT_PROCESS_NAMES_WINDOWS
    return RIOT_PROCESS_NAMES_MAC


def _kill_riot_client() -> None:
    """Terminate Riot/League client processes after a short delay."""
    delay = settings.force_close_delay_seconds
    logger.info("Force-close enabled. Waiting %d seconds before closing...", delay)
    time.sleep(delay)

    process_names = _get_process_names()
    killed = []
    for proc in psutil.process_iter(["pid", "name"]):
        try:
            if proc.info["name"] in process_names:
                proc.terminate()
                killed.append(proc.info["name"])
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    if killed:
        logger.info("Terminated processes: %s", ", ".join(killed))
    else:
        logger.info("No Riot/League processes found to terminate.")


def on_game_end(session_game_count: int) -> None:
    """
    Called by lcu_monitor when a game ends.
    Checks limits and triggers notification or force-close.
    """
    logger.info(
        "Play limiter: session=%d, session_cap=%d, daily_cap=%d",
        session_game_count,
        settings.session_game_cap,
        settings.daily_game_cap,
    )

    over_session = session_game_count >= settings.session_game_cap
    over_daily = session_game_count >= settings.daily_game_cap

    if not over_session and not over_daily:
        remaining = settings.session_game_cap - session_game_count
        logger.info("Under limit. %d game(s) remaining this session.", remaining)

        if settings.enable_notification and remaining <= 2:
            send_notification(
                "TFT Monitor",
                f"Heads up — {remaining} game(s) left before your session cap.",
            )
        return

    over_by = session_game_count - max(settings.session_game_cap, settings.daily_game_cap) + 1

    if over_daily:
        msg = (
            f"Game {session_game_count}: You're {over_by} game(s) over your "
            f"daily cap of {settings.daily_game_cap}. Stop playing!"
        )
    else:
        msg = (
            f"Game {session_game_count}: You're {over_by} game(s) over your "
            f"session cap of {settings.session_game_cap}. Take a break!"
        )

    logger.warning(msg)

    if settings.enable_notification:
        send_notification("TFT Monitor — Limit Reached", msg)

    if settings.enable_force_close:
        _kill_riot_client()
