# graphspy/api/owa.py

"""API endpoints for OWA (Outlook Web Access) token-based login."""

# Built-in imports
import json

# External library imports
from flask import Blueprint, redirect, request

# Local library imports
from ..db import connection

bp = Blueprint("owa", __name__)


@bp.get("/api/owa_login")
def owa_login():
    """Redirect to OWA with silent SSO attempt using the access token.

    Query params:
        access_token_id (optional) — Use this token instead of the active one.
        client_id (optional) — Override the client ID (default: Microsoft Office).
        resource (optional) — Override the resource (default: https://outlook.office365.com).

    Tries a silent SSO redirect through login.microsoftonline.com with
    prompt=none. If the browser has an active Microsoft session, the user
    lands in OWA automatically. Otherwise they see the normal login page.
    """
    token_id = request.args.get("access_token_id")

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

    import jwt as jwt_lib
    token_str = access_token[0]
    decoded = jwt_lib.decode(token_str, options={"verify_signature": False})

    # Extract user info from token for login_hint
    email = decoded.get("email") or decoded.get("upn") or ""
    unique_name = decoded.get("unique_name") or ""
    tid = decoded.get("tid", "")

    # Extract domain from email or unique_name for domain_hint
    domain = ""
    if "@" in email:
        domain = email.split("@")[1]
    elif "@" in unique_name and "live.com#" in unique_name:
        domain = unique_name.split("@")[1]

    # Allow overriding client_id and resource via query params
    client_id = request.args.get("client_id", "d3590ed6-52b3-4102-aeff-aad2292ab01c")
    resource = request.args.get("resource", "https://outlook.office365.com")

    # Build silent SSO URL: prompt=none tries silent auth if browser has session
    params = {
        "response_type": "id_token",
        "client_id": client_id,
        "redirect_uri": "https://outlook.office365.com/owa/",
        "resource": resource,
        "prompt": "none",
        "response_mode": "form_post",
    }
    if email:
        params["login_hint"] = email
    if domain:
        params["domain_hint"] = domain

    from urllib.parse import urlencode
    auth_url = f"https://login.microsoftonline.com/common/oauth2/authorize?{urlencode(params)}"
    return redirect(auth_url)


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
