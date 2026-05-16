# graphspy/api/owa.py

"""API endpoints for OWA (Outlook Web Access) token-based login."""

# Built-in imports
import base64
import json

# External library imports
from flask import Blueprint, redirect, request

# Local library imports
from ..db import connection

bp = Blueprint("owa", __name__)


@bp.get("/api/owa_login")
def owa_login():
    """Generate an OWA login URL that injects the active or specified access token.
    
    Query params:
        access_token_id (optional) — Use this token instead of the active one.
    
    Returns a redirect to OWA with the token embedded.
    """
    token_id = request.args.get("access_token_id")

    if not token_id:
        # Try active token
        row = connection.query_db(
            "SELECT value FROM settings WHERE setting = 'active_access_token_id'",
            one=True,
        )
        token_id = row[0] if row else None

    if not token_id or token_id == "0":
        return "[Error] No access token specified and no active token set", 400

    access_token = connection.query_db(
        "SELECT accesstoken FROM accesstokens WHERE id = ?",
        [token_id],
        one=True,
    )
    if not access_token:
        return f"[Error] Access token {token_id} not found", 404

    token_str = access_token[0]
    encoded_token = base64.b64encode(token_str.encode()).decode()

    # Build OWA login URL with injected token
    # Uses the Azure AD token-based login approach
    owa_url = (
        "https://outlook.office365.com/owa/?token={}".format(encoded_token)
    )
    return redirect(owa_url)


@bp.post("/api/owa_login_token")
def owa_login_token():
    """Return the OWA token data as JSON (for programmatic use).
    
    Form params:
        access_token_id (optional) — Use this token instead of the active one.
    
    Returns JSON with the access token and OWA URL.
    """
    token_id = request.form.get("access_token_id")

    if not token_id:
        row = connection.query_db(
            "SELECT value FROM settings WHERE setting = 'active_access_token_id'",
            one=True,
        )
        token_id = row[0] if row else None

    if not token_id or token_id == "0":
        return "[Error] No access token specified and no active token set", 400

    access_token = connection.query_db(
        "SELECT accesstoken FROM accesstokens WHERE id = ?",
        [token_id],
        one=True,
    )
    if not access_token:
        return f"[Error] Access token {token_id} not found", 404

    token_str = access_token[0]
    return json.dumps({
        "access_token": token_str,
        "owa_url": "https://outlook.office365.com/owa/",
        "token_id": token_id,
    })


@bp.get("/api/captured_tokens")
def captured_tokens():
    """Return tokens captured from device codes, ordered by most recent first."""
    rows = connection.query_db_json(
        """SELECT at.id as access_token_id, at.user, at.resource, at.stored_at, at.description,
                  rt.id as refresh_token_id, rt.foci, dc.user_code, dc.status as device_code_status
           FROM accesstokens at
           LEFT JOIN refreshtokens rt ON rt.captured_from_device_code = at.captured_from_device_code
           LEFT JOIN devicecodes dc ON dc.id = at.captured_from_device_code
           WHERE at.captured_from_device_code IS NOT NULL
           ORDER BY at.id DESC"""
    )
    return json.dumps(rows, default=str)
