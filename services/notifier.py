"""Desktop notifications for play-time alerts."""
import logging
import platform
import shutil
import subprocess

logger = logging.getLogger(__name__)


def _mac_notify(title: str, message: str) -> None:
    """Send a macOS notification via terminal-notifier or osascript."""
    tn_path = shutil.which("terminal-notifier")
    if tn_path:
        subprocess.run(
            [tn_path, "-title", title, "-message", message, "-sound", "default"],
            check=True,
        )
        return

    safe_title = title.replace('"', '\\"')
    safe_message = message.replace('"', '\\"')
    script = f'display notification "{safe_message}" with title "{safe_title}"'
    subprocess.run(["osascript", "-e", script], check=True)


def send_notification(title: str, message: str) -> None:
    """Show a desktop notification. Uses terminal-notifier on macOS, plyer elsewhere."""
    if platform.system() == "Darwin":
        try:
            _mac_notify(title, message)
            logger.info("Notification sent (macOS): %s — %s", title, message)
            return
        except Exception as e:
            logger.warning("macOS notification failed (%s), logging instead.", e)
            logger.info("NOTIFICATION: %s — %s", title, message)
            return

    try:
        from plyer import notification

        notification.notify(
            title=title,
            message=message,
            app_name="TFT Monitor",
            timeout=10,
        )
        logger.info("Notification sent (plyer): %s — %s", title, message)
    except Exception as e:
        logger.warning("Failed to send notification (%s), logging instead.", e)
        logger.info("NOTIFICATION: %s — %s", title, message)
