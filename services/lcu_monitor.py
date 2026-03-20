"""LCU Monitor — detects when TFT games end via the League client."""
import asyncio
import logging
from typing import Callable, Optional

from lcu_driver import Connector

logger = logging.getLogger(__name__)

# Session game counter — incremented each time EndOfGame is detected
session_game_count: int = 0

# Callback to run when a game ends — set by play_limiter in Phase 3
_on_game_end_callback: Optional[Callable] = None

# Connector is created lazily to avoid event loop issues on import
_connector: Optional[Connector] = None


def _get_connector() -> Connector:
    """Create the Connector on first use (not at import time)."""
    global _connector
    if _connector is not None:
        return _connector

    loop = asyncio.new_event_loop()
    _connector = Connector(loop=loop)

    @_connector.ready
    async def connect(connection):
        """Fires when the League client is found and connected."""
        resp = await connection.request("get", "/lol-gameflow/v1/gameflow-phase")
        phase = await resp.json()
        logger.info("LCU connected. Current gameflow phase: %s", phase)

    @_connector.ws.register("/lol-gameflow/v1/gameflow-phase")
    async def on_gameflow_change(connection, event):
        """Fires every time the gameflow phase changes."""
        phase = event.data
        logger.info("Gameflow phase changed: %s", phase)

        if phase == "EndOfGame":
            global session_game_count
            session_game_count += 1
            logger.info("Game ended. Session total: %d", session_game_count)

            if _on_game_end_callback is not None:
                _on_game_end_callback(session_game_count)

    @_connector.close
    async def disconnect(connection):
        """Fires when the League client is closed."""
        logger.info("LCU disconnected — League client closed.")

    return _connector


def set_on_game_end(callback: Callable) -> None:
    """Register a callback that fires after each game ends."""
    global _on_game_end_callback
    _on_game_end_callback = callback


def start_monitor() -> None:
    """Start the LCU connector (blocking). Run in a background thread."""
    logger.info("Starting LCU monitor — waiting for League client...")
    connector = _get_connector()
    connector.start()
