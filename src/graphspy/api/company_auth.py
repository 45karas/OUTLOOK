# graphspy/api/company_auth.py

# Built-in imports
import os
import secrets
from urllib.parse import urlencode

# External library imports
import jwt
import requests
from flask import Blueprint, redirect, request, session, url_for
from loguru import logger

# Local library imports
from ..core import tokens
from ..db import connection

bp = Blueprint("company_auth", __name__)

DEFAULT_SCOPES = "openid profile User.Read Mail.Read Mail.ReadWrite Mail.Send"


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


@bp.get("/login")
def login():
    if not oauth_configured():
        return redirect("/setup-login")

    state = secrets.token_urlsafe(32)
    session["oauth_state"] = state
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
    decoded = jwt.decode(access_token, options={"verify_signature": False})
    user = (
        decoded.get("preferred_username")
        or decoded.get("upn")
        or decoded.get("unique_name")
        or decoded.get("oid")
        or "Microsoft user"
    )
    access_token_id = tokens.save_access_token(access_token, f"Microsoft company login for {user}")
    set_active_access_token(access_token_id)

    session["company_user"] = user
    session["company_access_token_id"] = access_token_id
    return redirect("/outlook_graph?autoload=1")


@bp.get("/logout")
def logout():
    session.clear()
    return redirect("/")
