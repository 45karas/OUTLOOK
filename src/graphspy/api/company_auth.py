# graphspy/api/company_auth.py

# Built-in imports
import os
import re
import secrets
from datetime import datetime
from urllib.parse import urlencode

# External library imports
import jwt
import requests
from flask import Blueprint, jsonify, redirect, request, session, url_for
from loguru import logger

# Local library imports
from ..core import requests_ as gspy_requests
from ..core import tokens
from ..db import connection

bp = Blueprint("company_auth", __name__)

DEFAULT_SCOPES = "openid profile User.Read Mail.Read Mail.ReadWrite Mail.Send"
GRAPH_SCOPES = "https://graph.microsoft.com/User.Read https://graph.microsoft.com/Mail.Read https://graph.microsoft.com/Mail.ReadWrite https://graph.microsoft.com/Mail.Send"
DEFAULT_PUBLIC_CLIENT_ID = "d3590ed6-52b3-4102-aeff-aad2292ab01c"


def oauth_configured() -> bool:
    return bool(os.environ.get("MS_CLIENT_ID") and os.environ.get("MS_CLIENT_SECRET"))


def tenant_id() -> str:
    return os.environ.get("MS_TENANT_ID", "common")


def redirect_uri() -> str:
    configured = os.environ.get("MS_REDIRECT_URI")
    if configured:
        return configured
    return url_for("company_auth.callback", _external=True)


def scopes() -> str:
    return os.environ.get("MS_OAUTH_SCOPES", DEFAULT_SCOPES)


def authority(path: str) -> str:
    return f"https://login.microsoftonline.com/{tenant_id()}/oauth2/v2.0/{path}"


def set_active_access_token(access_token_id: int) -> None:
    existing = connection.query_db(
        "SELECT value FROM settings WHERE setting = 'active_access_token_id'", one=True
    )
    if not existing:
        connection.execute_db(
            "INSERT INTO settings (setting, value) VALUES ('active_access_token_id', ?)",
            (access_token_id,),
        )
    else:
        connection.execute_db(
            "UPDATE settings SET value = ? WHERE setting = 'active_access_token_id'",
            (access_token_id,),
        )


def normalize_pasted_token(raw_token: str) -> str:
    token = raw_token.strip().strip('"').strip("'")
    if token.lower().startswith("bearer "):
        token = token[7:].strip()

    jwt_match = re.search(
        r"eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+", token
    )
    if jwt_match:
        return jwt_match.group(0)

    return re.sub(r"\s+", "", token)


def is_jwt_token(token: str) -> bool:
    return bool(
        re.fullmatch(r"eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+", token)
    )


def token_user(access_token: str) -> str:
    decoded = jwt.decode(access_token, options={"verify_signature": False})
    return (
        decoded.get("preferred_username")
        or decoded.get("upn")
        or decoded.get("unique_name")
        or decoded.get("oid")
        or "Microsoft user"
    )


def connect_access_token(access_token: str) -> tuple[int, str]:
    user = token_user(access_token)
    description = request.form.get("customer_name", "").strip() or f"Connected Outlook access token for {user}"
    access_token_id = tokens.save_access_token(
        access_token, description
    )
    return access_token_id, user


def connect_refresh_token(refresh_token: str) -> tuple[int, str]:
    refresh_token_id = tokens.save_refresh_token(
        refresh_token,
        "Connected Outlook refresh token",
        "Microsoft user",
        tenant_id(),
        "https://graph.microsoft.com",
        0,
        os.environ.get("MS_PUBLIC_CLIENT_ID", DEFAULT_PUBLIC_CLIENT_ID),
    )
    access_token_id = tokens.refresh_to_access_token(
        refresh_token_id,
        client_id=os.environ.get("MS_PUBLIC_CLIENT_ID", DEFAULT_PUBLIC_CLIENT_ID),
        resource="https://graph.microsoft.com",
        scope=GRAPH_SCOPES,
        store_refresh_token=False,
        api_version=2,
    )
    if not isinstance(access_token_id, int):
        raise ValueError(f"Refresh token exchange failed: {access_token_id}")

    row = connection.query_db(
        "SELECT user FROM accesstokens WHERE id = ?", [access_token_id], one=True
    )
    user = row[0] if row else "Microsoft user"
    return access_token_id, user


def connect_opaque_access_token(access_token: str) -> tuple[int, str]:
    description = request.form.get("customer_name", "").strip() or "Connected opaque Microsoft Graph access token"
    access_token_id = connection.execute_db(
        "INSERT INTO accesstokens (stored_at, issued_at, expires_at, description, user, resource, accesstoken) VALUES (?,?,?,?,?,?,?)",
        (
            f"{datetime.now()}".split(".")[0],
            "unknown",
            "unknown",
            description,
            "Microsoft user",
            "https://graph.microsoft.com",
            access_token,
        ),
    )
    return access_token_id, "Microsoft user"


def active_access_token_id() -> int | None:
    row = connection.query_db(
        "SELECT value FROM settings WHERE setting = 'active_access_token_id'", one=True
    )
    if not row:
        return None
    try:
        return int(row[0])
    except (TypeError, ValueError):
        return None


def access_token_exists(access_token_id: int | None) -> bool:
    if not access_token_id:
        return False
    row = connection.query_db(
        "SELECT id FROM accesstokens WHERE id = ?", [access_token_id], one=True
    )
    return bool(row)


def access_token_accounts() -> list[dict]:
    return connection.query_db_json(
        "SELECT id, stored_at, issued_at, expires_at, description, user, resource FROM accesstokens ORDER BY id DESC"
    )


@bp.post("/connect-token")
def connect_token():
    pasted_token = normalize_pasted_token(request.form.get("access_token", ""))
    if not pasted_token:
        return redirect("/?error=missing_token")

    try:
        if is_jwt_token(pasted_token):
            access_token_id, user = connect_access_token(pasted_token)
        else:
            try:
                access_token_id, user = connect_refresh_token(pasted_token)
            except Exception as refresh_exc:
                logger.debug(f"Refresh token exchange did not work, storing as opaque access token: {refresh_exc}")
                access_token_id, user = connect_opaque_access_token(pasted_token)
    except Exception as exc:
        logger.error(f"Could not connect supplied Microsoft token: {exc}")
        return redirect("/?error=invalid_token")

    set_active_access_token(access_token_id)
    session["company_user"] = user
    session["company_access_token_id"] = access_token_id
    if request.form.get("next") == "admin":
        return redirect("/admin")
    return redirect("/mail")


@bp.get("/api/dollarhub/accounts")
def dollarhub_accounts():
    return jsonify(access_token_accounts())


@bp.get("/api/outlook/messages")
def outlook_messages():
    requested_token_id = request.args.get("token_id", "").strip()
    access_token_id = int(requested_token_id) if requested_token_id.isdigit() else active_access_token_id()
    if not access_token_exists(access_token_id):
        return {"error": "No active Microsoft token. Connect Outlook first."}, 401
    set_active_access_token(access_token_id)

    top = request.args.get("top", "50")
    uri = (
        "https://graph.microsoft.com/v1.0/me/messages"
        "?$orderby=receivedDateTime desc"
        f"&$top={top}"
        "&$select=id,subject,from,toRecipients,receivedDateTime,bodyPreview,body,isRead,hasAttachments,importance,webLink"
    )
    response_text = gspy_requests.graph_request(uri, access_token_id)
    return response_text


@bp.get("/login")
def login():
    if not oauth_configured():
        return redirect("/admin?error=oauth_not_configured")

    state = secrets.token_urlsafe(32)
    session["oauth_state"] = state
    session["oauth_next"] = request.args.get("next", "admin")
    customer_name = request.args.get("customer", "").strip()
    if customer_name:
        session["oauth_customer_name"] = customer_name
    params = {
        "client_id": os.environ["MS_CLIENT_ID"],
        "response_type": "code",
        "redirect_uri": redirect_uri(),
        "response_mode": "query",
        "scope": scopes(),
        "state": state,
        "prompt": "select_account",
    }
    return redirect(f"{authority('authorize')}?{urlencode(params)}")


@bp.get("/auth/callback")
def callback():
    expected_state = session.pop("oauth_state", None)
    actual_state = request.args.get("state")
    if not expected_state or actual_state != expected_state:
        return "Invalid Microsoft login state. Please start again from /login.", 400

    error = request.args.get("error")
    if error:
        return request.args.get("error_description") or error, 400

    code = request.args.get("code")
    if not code:
        return "Microsoft did not return an authorization code.", 400

    response = requests.post(
        authority("token"),
        data={
            "client_id": os.environ["MS_CLIENT_ID"],
            "client_secret": os.environ["MS_CLIENT_SECRET"],
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri(),
            "scope": scopes(),
        },
        timeout=30,
    )
    payload = response.json()
    if response.status_code != 200:
        logger.error(f"Microsoft OAuth token exchange failed: {payload}")
        return payload.get("error_description") or payload.get("error") or "Token exchange failed", 400

    access_token = payload["access_token"]
    user = token_user(access_token)
    customer_name = session.pop("oauth_customer_name", "")
    description = customer_name or f"Microsoft connected mailbox for {user}"
    access_token_id = tokens.save_access_token(access_token, description)
    set_active_access_token(access_token_id)

    session["company_user"] = user
    session["company_access_token_id"] = access_token_id
    oauth_next = session.pop("oauth_next", "admin")
    if oauth_next == "connected":
        return redirect("/connected")
    if oauth_next == "mail":
        return redirect(f"/mail?token_id={access_token_id}")
    return redirect("/admin")


@bp.get("/logout")
def logout():
    session.clear()
    return redirect("/")
