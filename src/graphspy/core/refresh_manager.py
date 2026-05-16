# graphspy/core/refresh_manager.py

"""Background thread that auto-refreshes access tokens before they expire."""

# Built-in imports
import threading
import time
from datetime import datetime

# External library imports
from loguru import logger

# Local library imports
from ..db import connection
from ..core import tokens as token_utils
from ..core import user_agent as ua
from ..core import requests_ as gspy_requests

# Default: check every 60 seconds, refresh tokens expiring within 300 seconds (5 min)
DEFAULT_CHECK_INTERVAL = 60
DEFAULT_REFRESH_WINDOW = 300


class RefreshManager:
    def __init__(self, app=None):
        self._thread = None
        self._stop_event = threading.Event()
        self._check_interval = DEFAULT_CHECK_INTERVAL
        self._refresh_window = DEFAULT_REFRESH_WINDOW
        self._app = app

    def init_app(self, app):
        """Store app reference for app-context operations."""
        self._app = app

    def start(self):
        """Start the background refresh thread."""
        if self._thread and self._thread.is_alive():
            logger.debug("Refresh manager thread already running")
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True, name="token-refresh")
        self._thread.start()
        logger.info("Token auto-refresh manager started (check every {}s, refresh window {}s)".format(
            self._check_interval, self._refresh_window))

    def stop(self):
        """Signal the refresh thread to stop."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=10)
        logger.info("Token auto-refresh manager stopped")

    def _run(self):
        """Main loop: periodically check and refresh tokens."""
        while not self._stop_event.is_set():
            try:
                if self._app:
                    with self._app.app_context():
                        self._check_and_refresh()
                else:
                    self._check_and_refresh()
            except Exception as exc:
                logger.error(f"Error in token refresh cycle: {exc}")
            self._stop_event.wait(self._check_interval)

    def _check_and_refresh(self):
        """Check all active access tokens and refresh those near expiry."""
        now_ts = int(datetime.now().timestamp())
        threshold_ts = now_ts + self._refresh_window

        # Get all access tokens
        rows = connection.query_db(
            "SELECT id, expires_at, user, resource FROM accesstokens ORDER BY id"
        )
        for row in rows:
            token_id = row[0]
            expires_str = row[1]
            user = row[2]
            resource = row[3]

            if not expires_str or expires_str == "unknown":
                continue

            try:
                expires_ts = int(datetime.strptime(expires_str, "%Y-%m-%d %H:%M:%S").timestamp())
            except (ValueError, TypeError):
                continue

            # Skip if not near expiry or already expired too far in the past
            if expires_ts > threshold_ts:
                continue
            if expires_ts < now_ts - 3600:
                # Expired more than an hour ago — skip
                continue

            # Find a refresh token for this access token
            rt_id = token_utils.find_refresh_token_for_access(token_id)
            if not rt_id:
                continue

            # Follow the chain to get the latest refresh token
            latest_rt_id = token_utils.get_latest_refresh_token_id(rt_id)

            # Check if this refresh token has auto_refresh enabled
            auto_check = connection.query_db(
                "SELECT auto_refresh FROM refreshtokens WHERE id = ?",
                [latest_rt_id],
                one=True,
            )
            if not auto_check or not auto_check[0]:
                continue

            logger.info(
                f"Auto-refreshing access token {token_id} (user={user}, resource={resource}, "
                f"expires in {expires_ts - now_ts}s)"
            )
            try:
                new_at_id = token_utils.refresh_to_access_token(
                    refresh_token_id=latest_rt_id,
                    store_refresh_token=True,
                )
                if isinstance(new_at_id, int):
                    logger.info(
                        f"Auto-refreshed: access token {token_id} → new token {new_at_id}"
                    )
                else:
                    logger.warning(
                        f"Auto-refresh failed for token {token_id}: {new_at_id}"
                    )
            except Exception as exc:
                logger.error(f"Auto-refresh error for token {token_id}: {exc}")


# Singleton instance
refresh_manager = RefreshManager()
