"""Play-time limiting logic — runs after each game ends."""
import logging
import threading
import time
import platform

import psutil

from config import get_settings
from services.notifier import send_notification

logger = logging.getLogger(__name__)

settings = get_settings()

# Substring match (case-insensitive) against psutil process names.
# RiotClientServices is the background launcher that can silently
# relaunch the League client after it's been killed, so it must be
# included or the "block reopening" behavior won't hold.
RIOT_PROCESS_NAMES_WINDOWS = [
    "riotclientservices.exe",
    "riotclientux.exe",
    "leagueclient.exe",
    "leagueclientux.exe",
    "league of legends.exe",
]
RIOT_PROCESS_NAMES_MAC = [
    "riotclientservices",
    "riotclientux",
    "leagueclientux",
    "league of legends",
]

# Guards the shared block deadline so a new game-end event can extend
# an in-progress block window instead of racing a second watcher thread.
_block_lock = threading.Lock()
_block_deadline = 0.0
_watcher_thread: threading.Thread | None = None


def _get_process_names() -> list[str]:
    """Return the correct process name fragments for the current OS."""
    if platform.system() == "Windows":
        return RIOT_PROCESS_NAMES_WINDOWS
    return RIOT_PROCESS_NAMES_MAC


def _terminate_process(proc: psutil.Process) -> None:
    """Kill a process outright. SIGTERM is routinely ignored/handled by
    the Riot client, so go straight to SIGKILL and confirm it's dead."""
    try:
        proc.kill()
        proc.wait(timeout=3)
    except (psutil.NoSuchProcess, psutil.TimeoutExpired, psutil.AccessDenied):
        pass


def _sweep_riot_processes() -> list[str]:
    """Find and kill every running Riot/League process. Returns the names killed."""
    targets = _get_process_names()
    killed = []
    for proc in psutil.process_iter(["pid", "name"]):
        try:
            name = proc.info["name"] or ""
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
        if any(target in name.lower() for target in targets):
            _terminate_process(proc)
            killed.append(name)
    return killed


def _watch_and_block(duration_seconds: float, poll_interval: float = 2.0) -> None:
    """Keep sweeping and killing Riot/League processes until the block
    window expires, so re-launching the game doesn't just undo the close."""
    global _block_deadline

    with _block_lock:
        _block_deadline = max(_block_deadline, time.monotonic() + duration_seconds)

    logger.info("Blocking Riot/League from reopening for %.0f minute(s).", duration_seconds / 60)

    while True:
        with _block_lock:
            deadline = _block_deadline
        if time.monotonic() >= deadline:
            break
        killed = _sweep_riot_processes()
        if killed:
            logger.info("Blocked relaunch attempt, terminated: %s", ", ".join(killed))
        time.sleep(poll_interval)

    logger.info("Riot/League block window ended.")


def _kill_riot_client() -> None:
    """Terminate Riot/League client processes and keep them closed for a while.

    Runs on its own thread (see on_game_end) since it sleeps and then
    polls for the duration of the block window — it must not block the
    asyncio event loop the LCU monitor runs on.
    """
    global _watcher_thread

    delay = settings.force_close_delay_seconds
    logger.info("Force-close enabled. Waiting %d seconds before closing...", delay)
    time.sleep(delay)

    killed = _sweep_riot_processes()
    if killed:
        logger.info("Terminated processes: %s", ", ".join(killed))
    else:
        logger.info("No Riot/League processes found to terminate.")

    block_minutes = settings.force_close_block_minutes
    if block_minutes <= 0:
        return

    if _watcher_thread is not None and _watcher_thread.is_alive():
        with _block_lock:
            global _block_deadline
            _block_deadline = time.monotonic() + block_minutes * 60
        logger.info("Extended existing block window by %d minute(s).", block_minutes)
    else:
        _watcher_thread = threading.Thread(
            target=_watch_and_block, args=(block_minutes * 60,), daemon=True
        )
        _watcher_thread.start()


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
        threading.Thread(target=_kill_riot_client, daemon=True).start()
