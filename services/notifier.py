"""Desktop notifications for play-time alerts."""
import logging
import platform

logger = logging.getLogger(__name__)


def send_notification(title: str, message: str) -> None:
    """Show a desktop notification. Falls back to logging if it fails."""
    try:
        from plyer import notification

        notification.notify(
            title=title,
            message=message,
            app_name="TFT Monitor",
            timeout=10,
        )
        logger.info("Notification sent: %s — %s", title, message)
    except Exception as e:
        logger.warning("Failed to send notification (%s), logging instead.", e)
        logger.info("NOTIFICATION: %s — %s", title, message)
