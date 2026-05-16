# graphspy/core/tokens.py

# Built-in imports
import uuid
from datetime import datetime

# External library imports
import jwt
from loguru import logger

# Local library imports
from ..db import connection
from ..core import user_agent as ua
from ..core import requests_ as gspy_requests


def parse_token_endpoint_error(response) -> str:
    try:
        error_code = response.json().get("error", "Unknown error")
        error_description = response.json().get("error_description", "Unknown error")
        return f"[{response.status_code}] {error_code}: {error_description}"
    except ValueError:
        return f"[{response.status_code}] {response.text}"


def is_valid_uuid(val) -> bool:
    try:
        uuid.UUID(str(val))
        return True
    except ValueError:
        return False


def _resolve_user_via_graph(access_token: str) -> str | None:
    """Call MS Graph /me to get the real userPrincipalName or mail.
    Falls back to displayName. Returns None on any failure.
    This avoids the 'live.com#...' JWT claim for personal accounts."""
    try:
        headers = {
            "Authorization": f"Bearer {access_token}",
            "User-Agent": ua.get(),
        }
        resp = gspy_requests.get(
            "https://graph.microsoft.com/v1.0/me?$select=userPrincipalName,mail,displayName",
            headers=headers,
        )
        if resp.status_code == 200:
            data = resp.json()
            resolved = data.get("userPrincipalName") or data.get("mail") or data.get("displayName")
            if resolved:
                logger.debug(f"Resolved user identity via Graph /me: {resolved}")
                return resolved
    except Exception as exc:
        logger.debug(f"Could not resolve user via Graph /me: {exc}")
    return None


def get_tenant_id(tenant_domain: str) -> str:
    headers = {"User-Agent": ua.get()}
    response = gspy_requests.get(
        f"https://login.microsoftonline.com/{tenant_domain}/.well-known/openid-configuration",
        headers=headers,
    )
    return response.json()["authorization_endpoint"].split("/")[3]


def save_access_token(accesstoken: str, description: str, captured_from_device_code: int = None) -> int:
    decoded = jwt.decode(accesstoken, options={"verify_signature": False})
    idtyp = decoded.get("idtyp")
    if idtyp == "user":
        user = decoded.get("unique_name") or decoded.get("upn") or "unknown"
    elif idtyp == "app":
        user = decoded.get("app_displayname") or decoded.get("appid") or "unknown"
    else:
        user = (
            decoded.get("unique_name")
            or decoded.get("upn")
            or decoded.get("app_displayname")
            or decoded.get("oid")
            or "unknown"
        )
    logger.debug(
        f"Saving access token for user '{user}', resource '{decoded.get('aud', 'unknown')}': {description}"
    )
    token_id = connection.execute_db(
        "INSERT INTO accesstokens (stored_at, issued_at, expires_at, description, user, resource, accesstoken, captured_from_device_code) VALUES (?,?,?,?,?,?,?,?)",
        (
            f"{datetime.now()}".split(".")[0],
            datetime.fromtimestamp(decoded["iat"]) if "iat" in decoded else "unknown",
            datetime.fromtimestamp(decoded["exp"]) if "exp" in decoded else "unknown",
            description,
            user,
            decoded.get("aud", "unknown"),
            accesstoken,
            captured_from_device_code,
        ),
    )

    # Try to resolve better user identity via Graph /me
    # (JWT unique_name often returns 'live.com#...' for personal accounts)
    resolved_user = _resolve_user_via_graph(accesstoken)
    if resolved_user and resolved_user != user:
        connection.execute_db(
            "UPDATE accesstokens SET user = ? WHERE id = ?",
            (resolved_user, token_id),
        )
        logger.debug(f"Updated access token {token_id} user: '{user}' -> '{resolved_user}'")

    return token_id


def save_refresh_token(
    refreshtoken: str,
    description: str,
    user: str,
    tenant: str,
    resource: str,
    foci: int,
    client_id: str = "d3590ed6-52b3-4102-aeff-aad2292ab01c",
    expires_at: int = None,
    auto_refresh: int = 1,
    captured_from_device_code: int = None,
) -> int:
    logger.debug(
        f"Saving refresh token for user '{user}', tenant '{tenant}': {description}"
    )
    foci_int = 1 if foci else 0
    if tenant == "common":
        tenant_id = "common"
    else:
        tenant_id = (
            tenant.strip("\"{}-[]\\/' ")
            if is_valid_uuid(tenant.strip("\"{}-[]\\/' "))
            else get_tenant_id(tenant)
        )
    return connection.execute_db(
        "INSERT INTO refreshtokens (stored_at, description, user, tenant_id, client_id, resource, foci, refreshtoken, expires_at, auto_refresh, captured_from_device_code) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (
            f"{datetime.now()}".split(".")[0],
            description,
            user,
            tenant_id,
            client_id,
            resource,
            foci_int,
            refreshtoken,
            expires_at,
            auto_refresh,
            captured_from_device_code,
        ),
    )


def refresh_to_access_token(
    refresh_token_id: int,
    client_id: str = "defined_in_token",
    resource: str = "defined_in_token",
    scope: str = "",
    store_refresh_token: bool = True,
    api_version: int = 1,
) -> int:
    refresh_token = connection.query_db(
        "SELECT refreshtoken FROM refreshtokens WHERE id = ?",
        [refresh_token_id],
        one=True,
    )[0]
    tenant_id = (
        connection.query_db(
            "SELECT tenant_id FROM refreshtokens WHERE id = ?",
            [refresh_token_id],
            one=True,
        )[0]
        or "common"
    )
    if resource == "defined_in_token":
        resource = connection.query_db(
            "SELECT resource FROM refreshtokens WHERE id = ?",
            [refresh_token_id],
            one=True,
        )[0]
    if client_id == "defined_in_token":
        client_id = connection.query_db(
            "SELECT client_id FROM refreshtokens WHERE id = ?",
            [refresh_token_id],
            one=True,
        )[0]

    body = {
        "client_id": client_id,
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
    }
    url = f"https://login.microsoftonline.com/{tenant_id}"
    if api_version == 1:
        body["resource"] = resource
        url += "/oauth2/token?api-version=1.0"
    elif api_version == 2:
        body["scope"] = scope
        url += "/oauth2/v2.0/token"

    response = gspy_requests.post(url, data=body, headers={"User-Agent": ua.get()})
    if response.status_code != 200:
        return {parse_token_endpoint_error(response)}

    access_token = response.json()["access_token"]
    save_access_token(access_token, f"Created using refresh token {refresh_token_id}")
    access_token_id = connection.query_db(
        "SELECT id FROM accesstokens WHERE accesstoken = ?", [access_token], one=True
    )[0]

    if store_refresh_token:
        decoded = jwt.decode(access_token, options={"verify_signature": False})
        idtyp = decoded.get("idtyp")
        if idtyp == "user":
            user = decoded.get("unique_name") or decoded.get("upn") or "unknown"
        elif idtyp == "app":
            user = decoded.get("app_displayname") or decoded.get("appid") or "unknown"
        else:
            user = "unknown"

        # Resolve real identity via Graph /me (fixes live.com#... for personal accounts)
        resolved_user = _resolve_user_via_graph(access_token)
        if resolved_user:
            user = resolved_user

        # Determine refresh token expiry from response or JWT
        rt_response = response.json()
        rt_expires_at = None
        if "refresh_token_expires_in" in rt_response:
            rt_expires_at = int(datetime.now().timestamp()) + int(rt_response["refresh_token_expires_in"])
        elif "expires_in" in rt_response:
            # Some endpoints return expires_in for the RT as well
            rt_expires_at = int(datetime.now().timestamp()) + int(rt_response["expires_in"])
        elif "expires_on" in rt_response:
            rt_expires_at = int(rt_response["expires_on"])

        new_rt_id = save_refresh_token(
            rt_response["refresh_token"],
            f"Created using refresh token {refresh_token_id}",
            user,
            tenant_id,
            rt_response.get("resource", "unknown"),
            rt_response.get("foci", 0),
            client_id,
            expires_at=rt_expires_at,
        )
        # Mark the old refresh token as superseded by the new one
        connection.execute_db(
            "UPDATE refreshtokens SET superseded_by = ? WHERE id = ?",
            (new_rt_id, refresh_token_id),
        )
        logger.debug(
            f"Refresh token {refresh_token_id} superseded by {new_rt_id}"
        )
    return access_token_id


def get_latest_refresh_token_id(refresh_token_id: int) -> int:
    """Follow the superseded_by chain to find the latest refresh token."""
    current_id = refresh_token_id
    visited = set()
    while current_id not in visited:
        visited.add(current_id)
        row = connection.query_db(
            "SELECT superseded_by FROM refreshtokens WHERE id = ?",
            [current_id],
            one=True,
        )
        if not row or row[0] is None:
            return current_id
        current_id = row[0]
    return current_id


def get_access_token_expiry(access_token_id: int) -> int | None:
    """Return the Unix timestamp when an access token expires, or None."""
    row = connection.query_db(
        "SELECT expires_at FROM accesstokens WHERE id = ?",
        [access_token_id],
        one=True,
    )
    if not row or not row[0]:
        return None
    try:
        return int(datetime.strptime(row[0], "%Y-%m-%d %H:%M:%S").timestamp())
    except (ValueError, TypeError):
        return None


def find_refresh_token_for_access(access_token_id: int) -> int | None:
    """Find a refresh token that was created alongside or for this access token.
    Looks for refresh tokens whose description references this access token ID,
    or tokens for the same user/resource that aren't superseded."""
    access_row = connection.query_db(
        "SELECT user, resource FROM accesstokens WHERE id = ?",
        [access_token_id],
        one=True,
    )
    if not access_row:
        return None
    user, resource = access_row

    # Try description-based match first (tokens created via refresh_to_access_token)
    row = connection.query_db(
        "SELECT id FROM refreshtokens WHERE description LIKE ? AND superseded_by IS NULL LIMIT 1",
        [f"%{access_token_id}%"],
        one=True,
    )
    if row:
        return row[0]

    # Fallback: find any active refresh token for same user and resource
    row = connection.query_db(
        "SELECT id FROM refreshtokens WHERE user = ? AND resource = ? AND superseded_by IS NULL AND auto_refresh = 1 ORDER BY id DESC LIMIT 1",
        [user, resource],
        one=True,
    )
    return row[0] if row else None
