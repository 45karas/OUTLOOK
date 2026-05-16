# graphspy/api/token_health.py

"""API endpoints for token health status and auto-refresh control."""

# Built-in imports
import json
from datetime import datetime

# External library imports
from flask import Blueprint, request

# Local library imports
from ..db import connection
from ..core import tokens as token_utils
from ..core.refresh_manager import refresh_manager

bp = Blueprint("token_health", __name__)


@bp.get("/api/token_status")
def token_status():
    """Return health status for all stored tokens."""
    now_ts = int(datetime.now().timestamp())
    status = {"access_tokens": [], "refresh_tokens": [], "auto_refresh_active": refresh_manager._thread is not None and refresh_manager._thread.is_alive()}

    at_rows = connection.query_db_json("SELECT * FROM accesstokens ORDER BY id")
    for row in at_rows:
        expires_str = row.get("expires_at", "")
        expires_ts = None
        status_label = "unknown"
        seconds_left = None
        if expires_str and expires_str != "unknown":
            try:
                expires_ts = int(datetime.strptime(expires_str, "%Y-%m-%d %H:%M:%S").timestamp())
                seconds_left = expires_ts - now_ts
                if seconds_left <= 0:
                    status_label = "expired"
                elif seconds_left < 300:
                    status_label = "expiring_soon"
                else:
                    status_label = "valid"
            except (ValueError, TypeError):
                pass

        # Find paired refresh token
        rt_id = token_utils.find_refresh_token_for_access(row["id"])
        rt_info = None
        if rt_id:
            rt_row = connection.query_db_json(
                "SELECT id, auto_refresh, superseded_by FROM refreshtokens WHERE id = ?",
                [rt_id],
                one=True,
            )
            if rt_row:
                rt_info = {
                    "id": rt_row["id"],
                    "auto_refresh": bool(rt_row["auto_refresh"]),
                    "superseded": rt_row["superseded_by"] is not None,
                }

        status["access_tokens"].append({
            "id": row["id"],
            "user": row.get("user", "unknown"),
            "resource": row.get("resource", "unknown"),
            "description": row.get("description", ""),
            "status": status_label,
            "seconds_left": seconds_left,
            "expires_at": expires_str,
            "has_refresh": rt_info is not None,
            "refresh_info": rt_info,
        })

    rt_rows = connection.query_db_json("SELECT * FROM refreshtokens ORDER BY id")
    for row in rt_rows:
        status["refresh_tokens"].append({
            "id": row["id"],
            "user": row.get("user", "unknown"),
            "resource": row.get("resource", "unknown"),
            "description": row.get("description", ""),
            "auto_refresh": bool(row.get("auto_refresh", 1)),
            "superseded_by": row.get("superseded_by"),
            "expires_at": row.get("expires_at"),
            "stored_at": row.get("stored_at", ""),
        })

    return json.dumps(status, default=str)


@bp.post("/api/toggle_auto_refresh")
def toggle_auto_refresh():
    """Enable or disable auto-refresh for a specific refresh token."""
    token_id = request.form.get("refresh_token_id")
    state = request.form.get("state", "1")
    if not token_id:
        return "[Error] refresh_token_id is required", 400
    try:
        token_id = int(token_id)
    except ValueError:
        return "[Error] Invalid refresh_token_id", 400

    auto_refresh = 1 if state in ("1", "true", "enabled") else 0
    connection.execute_db(
        "UPDATE refreshtokens SET auto_refresh = ? WHERE id = ?",
        (auto_refresh, token_id),
    )
    return f"[Success] Auto-refresh {'enabled' if auto_refresh else 'disabled'} for refresh token {token_id}"
