# graphspy/api/company_auth.py

# Built-in imports
import os
import re
import secrets
from datetime import datetime
from urllib.parse import quote, urlencode

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
GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"
PERMISSION_GROUPS = [
    {
        "name": "Profile",
        "scopes": ["User.Read"],
        "features": "Profile, photo, manager, people basics",
    },
    {
        "name": "Outlook Mail",
        "scopes": ["Mail.Read", "Mail.ReadWrite", "Mail.Send"],
        "features": "Folders, inbox, read, update, send",
    },
    {
        "name": "Outlook Calendar",
        "scopes": ["Calendars.Read", "Calendars.ReadWrite"],
        "features": "Events, calendars, meeting management",
    },
    {
        "name": "Contacts",
        "scopes": ["Contacts.Read", "Contacts.ReadWrite", "People.Read"],
        "features": "Contacts and people",
    },
    {
        "name": "OneDrive / Excel / OneNote",
        "scopes": ["Files.Read", "Files.ReadWrite", "Files.Read.All", "Files.ReadWrite.All", "Notes.ReadWrite.All"],
        "features": "Drive files, Excel files, OneNote notebooks",
    },
    {
        "name": "SharePoint",
        "scopes": ["Sites.Read.All", "Sites.ReadWrite.All", "Lists.Read.All", "Lists.ReadWrite.All"],
        "features": "Sites, pages, lists, document libraries",
    },
    {
        "name": "Teams",
        "scopes": ["Team.ReadBasic.All", "Channel.ReadBasic.All", "ChannelMessage.Read.All", "Chat.Read", "Chat.ReadWrite"],
        "features": "Teams, channels, chats, channel messages",
    },
    {
        "name": "Users / Directory",
        "scopes": ["User.Read.All", "User.ReadWrite.All", "Directory.Read.All", "Directory.ReadWrite.All"],
        "features": "Users, directory, organization data",
    },
    {
        "name": "Groups",
        "scopes": ["Group.Read.All", "Group.ReadWrite.All"],
        "features": "Groups and memberships",
    },
    {
        "name": "Tasks / Planner / To Do",
        "scopes": ["Tasks.Read", "Tasks.ReadWrite", "Tasks.Read.Shared", "Tasks.ReadWrite.Shared", "Group.ReadWrite.All"],
        "features": "To Do lists, Planner tasks",
    },
    {
        "name": "Security / Compliance",
        "scopes": ["SecurityEvents.Read.All", "SecurityEvents.ReadWrite.All", "ThreatIndicators.ReadWrite.OwnedBy"],
        "features": "Security and compliance endpoints",
    },
    {
        "name": "Search / Insights",
        "scopes": ["ExternalItem.Read.All", "Sites.Read.All", "Files.Read.All"],
        "features": "Search, insights, trending content",
    },
]


class ManualTokenError(Exception):
    def __init__(self, error_key: str, message: str):
        super().__init__(message)
        self.error_key = error_key
        self.message = message


def permission_catalog() -> list[dict]:
    return PERMISSION_GROUPS


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


def graph_error_message(payload: dict) -> str:
    error = payload.get("error", payload)
    if isinstance(error, dict):
        return error.get("message") or error.get("error_description") or "Microsoft Graph rejected this token."
    return str(error or "Microsoft Graph rejected this token.")


def friendly_graph_error(payload: dict) -> tuple[str, str]:
    error = payload.get("error", payload)
    code = error.get("code", "") if isinstance(error, dict) else ""
    message = graph_error_message(payload)
    lowered = message.lower()

    if "idx14100" in lowered or "jwt is not well formed" in lowered:
        return (
            "invalid_token",
            "That value is not a usable Microsoft Graph access token. Copy only the Access token from Graph Explorer after running GET /me/messages.",
        )
    if code in {"InvalidAuthenticationToken", "Authentication_ExpiredToken"} or "expired" in lowered:
        return (
            "expired_token",
            "That Microsoft Graph access token is invalid or expired. Get a fresh token and paste it again.",
        )
    if "mail.read" in lowered or code in {"ErrorAccessDenied", "Authorization_RequestDenied", "Forbidden"}:
        return (
            "mail_permission",
            "The token works, but it cannot read mail. In Graph Explorer, consent to Mail.Read and run GET /me/messages before copying the token.",
        )
    return ("invalid_token", message)


def graph_get_with_token(access_token: str, path: str) -> requests.Response:
    return requests.get(
        f"{GRAPH_BASE_URL}{path}",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        },
        timeout=30,
    )


def token_claims(access_token: str) -> dict:
    if not is_jwt_token(access_token):
        return {}
    try:
        return jwt.decode(access_token, options={"verify_signature": False})
    except jwt.exceptions.DecodeError:
        return {}


def validate_manual_access_token(access_token: str) -> dict:
    try:
        profile_response = graph_get_with_token(
            access_token, "/me?$select=id,displayName,userPrincipalName,mail"
        )
    except requests.RequestException as exc:
        raise ManualTokenError(
            "graph_unreachable",
            "DollarHub could not reach Microsoft Graph. Try again in a moment.",
        ) from exc

    try:
        profile_payload = profile_response.json()
    except ValueError as exc:
        raise ManualTokenError(
            "invalid_token", "Microsoft Graph returned an unreadable response for this token."
        ) from exc

    if profile_response.status_code != 200:
        error_key, message = friendly_graph_error(profile_payload)
        raise ManualTokenError(error_key, message)

    try:
        mail_response = graph_get_with_token(
            access_token, "/me/messages?$top=1&$select=id,subject"
        )
    except requests.RequestException as exc:
        raise ManualTokenError(
            "graph_unreachable",
            "DollarHub could not reach Microsoft Graph to test mailbox access.",
        ) from exc

    try:
        mail_payload = mail_response.json()
    except ValueError as exc:
        raise ManualTokenError(
            "invalid_token", "Microsoft Graph returned an unreadable mailbox response."
        ) from exc

    if mail_response.status_code != 200:
        error_key, message = friendly_graph_error(mail_payload)
        if error_key == "invalid_token":
            error_key = "mail_permission"
        raise ManualTokenError(error_key, message)

    return profile_payload


def save_validated_access_token(access_token: str, description: str = "") -> tuple[int, str]:
    profile = validate_manual_access_token(access_token)
    user = (
        profile.get("mail")
        or profile.get("userPrincipalName")
        or profile.get("displayName")
        or "Microsoft user"
    )
    token_description = description.strip() or user
    access_token_id = tokens.save_access_token(access_token, token_description)
    connection.execute_db(
        "UPDATE accesstokens SET user = ?, resource = ? WHERE id = ?",
        (user, "https://graph.microsoft.com", access_token_id),
    )
    return access_token_id, user


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


def access_token_row(access_token_id: int | None):
    if not access_token_id:
        return None
    return connection.query_db(
        "SELECT accesstoken FROM accesstokens WHERE id = ?", [access_token_id], one=True
    )


def access_token_full_row(access_token_id: int | None):
    if not access_token_id:
        return None
    return connection.query_db_json(
        "SELECT id, stored_at, issued_at, expires_at, description, user, resource, accesstoken FROM accesstokens WHERE id = ?",
        [access_token_id],
        one=True,
    )


def access_token_accounts() -> list[dict]:
    return connection.query_db_json(
        "SELECT id, stored_at, issued_at, expires_at, description, user, resource FROM accesstokens ORDER BY id DESC"
    )


@bp.post("/connect-token")
def connect_token():
    pasted_token = normalize_pasted_token(request.form.get("access_token", ""))
    if not pasted_token:
        return redirect("/admin?error=missing_token")

    try:
        description = request.form.get("customer_name", "").strip()
        access_token_id, user = save_validated_access_token(pasted_token, description)
    except ManualTokenError as exc:
        logger.warning(f"Manual Microsoft Graph token was rejected: {exc.message}")
        return redirect(f"/admin?error={exc.error_key}")
    except Exception as exc:
        logger.error(f"Could not connect supplied Microsoft token: {exc}")
        return redirect("/admin?error=invalid_token")

    set_active_access_token(access_token_id)
    session["company_user"] = user
    session["company_access_token_id"] = access_token_id
    if request.form.get("next") == "admin":
        return redirect(f"/admin?connected={access_token_id}")
    return redirect(f"/mail?token_id={access_token_id}")


@bp.get("/api/dollarhub/accounts")
def dollarhub_accounts():
    return jsonify(access_token_accounts())


@bp.get("/api/outlook/status")
def outlook_status():
    requested_token_id = request.args.get("token_id", "").strip()
    access_token_id = int(requested_token_id) if requested_token_id.isdigit() else active_access_token_id()
    account = access_token_full_row(access_token_id)
    if not account:
        return {"ok": False, "error": "No saved token was found."}, 404

    access_token = account.pop("accesstoken")
    claims = token_claims(access_token)
    scopes = sorted(set(str(claims.get("scp", "")).split()))
    roles = sorted(set(claims.get("roles", []) or []))
    checks = []

    for name, path in [
        ("Profile", "/me?$select=id,displayName,userPrincipalName,mail"),
        ("Folders", "/me/mailFolders?$top=1&$select=id,displayName,totalItemCount,unreadItemCount"),
        ("Messages", "/me/messages?$top=1&$select=id,subject"),
    ]:
        try:
            response = graph_get_with_token(access_token, path)
            payload = response.json()
        except (requests.RequestException, ValueError):
            checks.append({"name": name, "ok": False, "message": "Could not reach Microsoft Graph."})
            continue
        if response.status_code == 200:
            checks.append({"name": name, "ok": True, "message": "OK"})
        else:
            checks.append({"name": name, "ok": False, "message": graph_error_message(payload)})

    return {
        "ok": all(check["ok"] for check in checks),
        "account": account,
        "token_type": "JWT" if claims else "opaque/manual",
        "scopes": scopes,
        "roles": roles,
        "checks": checks,
    }


@bp.get("/api/outlook/messages")
def outlook_messages():
    requested_token_id = request.args.get("token_id", "").strip()
    access_token_id = int(requested_token_id) if requested_token_id.isdigit() else active_access_token_id()
    if not access_token_exists(access_token_id):
        return {"error": "No active Microsoft token. Connect Outlook first."}, 401
    set_active_access_token(access_token_id)
    row = access_token_row(access_token_id)
    if not row:
        return {"error": "No active Microsoft token. Connect Outlook first."}, 401

    top_raw = request.args.get("top", "100")
    try:
        top = max(1, min(int(top_raw), 100))
    except ValueError:
        top = 100
    folder_id = request.args.get("folder_id", "").strip()
    folder_path = (
        f"/me/mailFolders/{quote(folder_id, safe='')}/messages"
        if folder_id
        else "/me/messages"
    )
    select_fields = ",".join(
        [
            "id",
            "subject",
            "sender",
            "from",
            "toRecipients",
            "ccRecipients",
            "receivedDateTime",
            "sentDateTime",
            "lastModifiedDateTime",
            "bodyPreview",
            "body",
            "isRead",
            "hasAttachments",
            "importance",
            "webLink",
            "parentFolderId",
        ]
    )
    uri = (
        f"{GRAPH_BASE_URL}{folder_path}"
        "?$orderby=receivedDateTime desc"
        f"&$top={top}"
        f"&$select={select_fields}"
    )
    headers = {
        "Authorization": f"Bearer {row[0]}",
        "Accept": "application/json",
    }
    try:
        response = requests.get(
            uri,
            headers=headers,
            timeout=30,
        )
    except requests.RequestException:
        return {"error": "DollarHub could not reach Microsoft Graph. Try again."}, 502

    try:
        payload = response.json()
    except ValueError:
        payload = {"error": response.text or "Microsoft Graph returned an unreadable response."}

    if response.status_code >= 400:
        error_key, message = friendly_graph_error(payload if isinstance(payload, dict) else {})
        return {"error": message, "error_key": error_key}, response.status_code
    if request.args.get("all") == "1" and isinstance(payload, dict):
        values = payload.get("value", [])
        next_link = payload.get("@odata.nextLink")
        page_count = 1
        while next_link and len(values) < 500 and page_count < 6:
            try:
                next_response = requests.get(next_link, headers=headers, timeout=30)
                next_payload = next_response.json()
            except (requests.RequestException, ValueError):
                break
            if next_response.status_code >= 400:
                break
            values.extend(next_payload.get("value", []))
            next_link = next_payload.get("@odata.nextLink")
            page_count += 1
        payload["value"] = values
        payload["dollarhubLoadedCount"] = len(values)
    return payload


@bp.get("/api/outlook/message/<path:message_id>")
def outlook_message(message_id):
    requested_token_id = request.args.get("token_id", "").strip()
    access_token_id = int(requested_token_id) if requested_token_id.isdigit() else active_access_token_id()
    if not access_token_exists(access_token_id):
        return {"error": "No active Microsoft token. Connect Outlook first."}, 401
    row = access_token_row(access_token_id)
    if not row:
        return {"error": "No active Microsoft token. Connect Outlook first."}, 401
    select_fields = ",".join(
        [
            "id",
            "subject",
            "sender",
            "from",
            "replyTo",
            "toRecipients",
            "ccRecipients",
            "receivedDateTime",
            "sentDateTime",
            "bodyPreview",
            "body",
            "isRead",
            "hasAttachments",
            "importance",
            "webLink",
            "parentFolderId",
        ]
    )
    uri = f"{GRAPH_BASE_URL}/me/messages/{quote(message_id, safe='')}?$select={select_fields}"
    try:
        response = requests.get(
            uri,
            headers={
                "Authorization": f"Bearer {row[0]}",
                "Accept": "application/json",
            },
            timeout=30,
        )
    except requests.RequestException:
        return {"error": "DollarHub could not reach Microsoft Graph. Try again."}, 502
    try:
        payload = response.json()
    except ValueError:
        payload = {"error": response.text or "Microsoft Graph returned an unreadable response."}
    if response.status_code >= 400:
        error_key, message = friendly_graph_error(payload if isinstance(payload, dict) else {})
        return {"error": message, "error_key": error_key}, response.status_code
    return payload


@bp.get("/api/outlook/folders")
def outlook_folders():
    requested_token_id = request.args.get("token_id", "").strip()
    access_token_id = int(requested_token_id) if requested_token_id.isdigit() else active_access_token_id()
    if not access_token_exists(access_token_id):
        return {"error": "No active Microsoft token. Connect Outlook first."}, 401
    set_active_access_token(access_token_id)
    row = access_token_row(access_token_id)
    if not row:
        return {"error": "No active Microsoft token. Connect Outlook first."}, 401

    uri = (
        f"{GRAPH_BASE_URL}/me/mailFolders"
        "?$top=80"
        "&$select=id,displayName,parentFolderId,totalItemCount,unreadItemCount"
    )
    try:
        response = requests.get(
            uri,
            headers={
                "Authorization": f"Bearer {row[0]}",
                "Accept": "application/json",
            },
            timeout=30,
        )
    except requests.RequestException:
        return {"error": "DollarHub could not reach Microsoft Graph. Try again."}, 502

    try:
        payload = response.json()
    except ValueError:
        payload = {"error": response.text or "Microsoft Graph returned an unreadable response."}

    if response.status_code >= 400:
        error_key, message = friendly_graph_error(payload if isinstance(payload, dict) else {})
        return {"error": message, "error_key": error_key}, response.status_code
    return payload


@bp.post("/api/outlook/send")
def outlook_send():
    data = request.get_json(silent=True) or {}
    requested_token_id = str(data.get("token_id") or "").strip()
    access_token_id = int(requested_token_id) if requested_token_id.isdigit() else active_access_token_id()
    if not access_token_exists(access_token_id):
        return {"error": "No active Microsoft token. Connect Outlook first."}, 401
    row = access_token_row(access_token_id)
    if not row:
        return {"error": "No active Microsoft token. Connect Outlook first."}, 401

    to_address = str(data.get("to") or "").strip()
    subject = str(data.get("subject") or "").strip()
    body = str(data.get("body") or "").strip()
    if not to_address or not subject:
        return {"error": "Recipient and subject are required."}, 400
    recipients = [
        {"emailAddress": {"address": email.strip()}}
        for email in to_address.split(",")
        if email.strip()
    ]
    if not recipients:
        return {"error": "At least one valid recipient is required."}, 400

    message = {
        "message": {
            "subject": subject,
            "body": {"contentType": "HTML", "content": body.replace("\n", "<br>")},
            "toRecipients": recipients,
        },
        "saveToSentItems": True,
    }
    try:
        response = requests.post(
            f"{GRAPH_BASE_URL}/me/sendMail",
            headers={
                "Authorization": f"Bearer {row[0]}",
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            json=message,
            timeout=30,
        )
    except requests.RequestException:
        return {"error": "DollarHub could not reach Microsoft Graph. Try again."}, 502

    if response.status_code in {202, 204}:
        return {"ok": True}
    try:
        payload = response.json()
    except ValueError:
        payload = {"error": response.text or "Microsoft Graph rejected this send request."}
    error_key, message_text = friendly_graph_error(payload if isinstance(payload, dict) else {})
    if error_key in {"invalid_token", "mail_permission"}:
        message_text = "This token cannot send mail. Get a fresh token with Mail.Send permission."
    return {"error": message_text, "error_key": error_key}, response.status_code


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
