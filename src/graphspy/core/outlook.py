# graphspy/core/outlook.py

"""Server-side Outlook/email operations via Microsoft Graph API."""

# Built-in imports
import json
from datetime import datetime

# External library imports
from loguru import logger

# Local library imports
from ..db import connection
from ..core import requests_ as gspy_requests


def _get_access_token(access_token_id: int) -> str:
    """Fetch the raw access token string by ID."""
    row = connection.query_db(
        "SELECT accesstoken FROM accesstokens WHERE id = ?",
        [access_token_id],
        one=True,
    )
    if not row:
        raise ValueError(f"Access token {access_token_id} not found")
    return row[0]


GRAPH_BASE = "https://graph.microsoft.com/v1.0"


def _graph_get(uri: str, access_token_id: int) -> dict:
    """Make an authenticated GET request to MS Graph and return parsed JSON."""
    data = json.loads(
        gspy_requests.graph_request(f"{GRAPH_BASE}{uri}", access_token_id, method="GET")
    )
    _check_graph_error(data)
    return data


def _graph_post(uri: str, access_token_id: int, body: dict) -> dict:
    """Make an authenticated POST request to MS Graph."""
    data = json.loads(
        gspy_requests.graph_request(f"{GRAPH_BASE}{uri}", access_token_id, method="POST", body=body)
    )
    _check_graph_error(data)
    return data


def _check_graph_error(data: dict):
    """Raise ValueError if the Graph response contains an error."""
    http_status = data.pop("_http_status", None)
    if "error" in data:
        err = data["error"]
        msg = err.get("message", str(err)) if isinstance(err, dict) else str(err)
        raise ValueError(f"Graph API error (HTTP {http_status}): {msg}")


def _graph_delete(uri: str, access_token_id: int) -> bool:
    """Make an authenticated DELETE request to MS Graph."""
    token = _get_access_token(access_token_id)
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    resp = gspy_requests.delete(
        f"{GRAPH_BASE}{uri}", headers=headers
    )
    return resp.status_code in (200, 204)


def _graph_patch(access_token_id: int, uri: str, body: dict) -> dict:
    """Make an authenticated PATCH request to MS Graph."""
    token = _get_access_token(access_token_id)
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    resp = gspy_requests.patch(
        f"{GRAPH_BASE}{uri}",
        headers=headers,
        json=body,
    )
    if resp.status_code == 200:
        return resp.json()
    return {"error": {"code": resp.status_code, "message": resp.text}}


def list_mail_folders(access_token_id: int, mailbox: str = "me") -> list[dict]:
    """List all mail folders for the authenticated user or shared mailbox."""
    data = _graph_get(f"/{mailbox}/mailFolders?$top=100&includeHiddenFolders=true&$select=id,displayName,totalItemCount,unreadItemCount", access_token_id)
    folders = data.get("value", [])

    # Sort: well-known folders first, then alphabetical
    well_known = {"inbox", "sentitems", "drafts", "deleteditems", "junkemail", "outbox", "archive"}
    result = []
    for f in folders:
        result.append({
            "id": f["id"],
            "display_name": f.get("displayName", "Unknown"),
            "parent_folder_id": f.get("parentFolderId", ""),
            "child_folder_count": f.get("childFolderCount", 0),
            "total_item_count": f.get("totalItemCount", 0),
            "unread_item_count": f.get("unreadItemCount", 0),
            "is_well_known": f.get("displayName", "").lower().replace(" ", "") in well_known,
        })

    result.sort(key=lambda x: (not x["is_well_known"], x["display_name"].lower()))
    return result


def list_messages(
    access_token_id: int,
    folder_id: str = "inbox",
    top: int = 50,
    skip: int = 0,
    search: str = "",
    order_by: str = "receivedDateTime desc",
    mailbox: str = "me",
) -> dict:
    """List messages in a folder with pagination and optional search.

    Returns:
        dict with keys: messages (list), count (total), skip, top
    """
    if folder_id == "__all__":
        base_uri = f"/{mailbox}/messages"
    else:
        base_uri = f"/{mailbox}/mailFolders/{folder_id}/messages"
    params = [f"$top={top}", f"$skip={skip}"]

    if search:
        params.append(f'$search="{search}"')
    if order_by:
        params.append(f"$orderby={order_by}")

    # Select only needed fields for performance
    select_fields = (
        "id,subject,from,toRecipients,ccRecipients,receivedDateTime,sentDateTime,"
        "hasAttachments,isRead,importance,flag,bodyPreview,internetMessageId,"
        "conversationId,parentFolderId,webLink,categories"
    )
    params.append(f"$select={select_fields}")
    params.append("$count=true")

    uri = f"{base_uri}?{'&'.join(params)}"
    data = _graph_get(uri, access_token_id)

    messages = []
    for msg in data.get("value", []):
        sender = msg.get("from", {}).get("emailAddress", {})
        messages.append({
            "id": msg["id"],
            "subject": msg.get("subject", "(No Subject)"),
            "sender_name": sender.get("name", "Unknown"),
            "sender_email": sender.get("address", ""),
            "received": msg.get("receivedDateTime", ""),
            "sent": msg.get("sentDateTime", ""),
            "has_attachments": msg.get("hasAttachments", False),
            "is_read": msg.get("isRead", False),
            "importance": msg.get("importance", "normal"),
            "body_preview": msg.get("bodyPreview", "")[:200],
            "web_link": msg.get("webLink", ""),
            "categories": msg.get("categories", []),
        })

    return {
        "messages": messages,
        "count": data.get("@odata.count", len(messages)),
        "skip": skip,
        "top": top,
    }


def get_message(access_token_id: int, message_id: str, mailbox: str = "me") -> dict:
    """Get full details of a single message including body."""
    select_fields = (
        "id,subject,body,from,toRecipients,ccRecipients,bccRecipients,"
        "receivedDateTime,sentDateTime,hasAttachments,isRead,importance,flag,"
        "internetMessageId,conversationId,parentFolderId,webLink,categories,"
        "attachments"
    )
    uri = f"/{mailbox}/messages/{message_id}?$select={select_fields}&$expand=attachments"
    msg = _graph_get(uri, access_token_id)

    sender = msg.get("from", {}).get("emailAddress", {})
    to_list = [
        {"name": r.get("emailAddress", {}).get("name", ""),
         "email": r.get("emailAddress", {}).get("address", "")}
        for r in msg.get("toRecipients", [])
    ]
    cc_list = [
        {"name": r.get("emailAddress", {}).get("name", ""),
         "email": r.get("emailAddress", {}).get("address", "")}
        for r in msg.get("ccRecipients", [])
    ]

    body = msg.get("body", {})
    body_content = body.get("content", "")
    body_type = body.get("contentType", "html")

    attachments = []
    for att in msg.get("attachments", []):
        attachments.append({
            "id": att.get("id", ""),
            "name": att.get("name", "Unknown"),
            "content_type": att.get("contentType", ""),
            "size": att.get("size", 0),
            "is_inline": att.get("isInline", False),
        })

    return {
        "id": msg["id"],
        "subject": msg.get("subject", "(No Subject)"),
        "sender_name": sender.get("name", "Unknown"),
        "sender_email": sender.get("address", ""),
        "to": to_list,
        "cc": cc_list,
        "received": msg.get("receivedDateTime", ""),
        "sent": msg.get("sentDateTime", ""),
        "has_attachments": msg.get("hasAttachments", False),
        "is_read": msg.get("isRead", False),
        "importance": msg.get("importance", "normal"),
        "body_content": body_content,
        "body_type": body_type,
        "web_link": msg.get("webLink", ""),
        "conversation_id": msg.get("conversationId", ""),
        "categories": msg.get("categories", []),
        "attachments": attachments,
    }


def send_message(
    access_token_id: int,
    to_recipients: list[dict],
    subject: str,
    body: str,
    cc_recipients: list[dict] = None,
    bcc_recipients: list[dict] = None,
    content_type: str = "HTML",
    importance: str = "normal",
    save_to_sent: bool = True,
    mailbox: str = "me",
) -> dict:
    """Send an email via Microsoft Graph.

    Args:
        to_recipients: List of {"email": "...", "name": "..."} dicts
        cc_recipients: Optional list of CC recipients
        bcc_recipients: Optional list of BCC recipients
        subject: Email subject
        body: Email body content
        content_type: "HTML" or "Text"
        importance: "low", "normal", or "high"
        save_to_sent: Whether to save in Sent Items
    """
    def _recipients(rcpt_list):
        if not rcpt_list:
            return []
        return [
            {"emailAddress": {"address": r.get("email", r.get("address", "")),
                              "name": r.get("name", "")}}
            for r in rcpt_list
        ]

    message = {
        "subject": subject,
        "body": {"contentType": content_type, "content": body},
        "toRecipients": _recipients(to_recipients),
        "importance": importance,
    }

    if cc_recipients:
        message["ccRecipients"] = _recipients(cc_recipients)
    if bcc_recipients:
        message["bccRecipients"] = _recipients(bcc_recipients)

    payload = {"message": message, "saveToSentItems": str(save_to_sent).lower()}
    _graph_post(f"/{mailbox}/sendMail", access_token_id, payload)
    logger.info(f"Email sent: '{subject}' to {len(to_recipients)} recipient(s)")
    return {"success": True, "subject": subject, "recipient_count": len(to_recipients)}


def delete_message(access_token_id: int, message_id: str, mailbox: str = "me") -> bool:
    """Move a message to Deleted Items."""
    success = _graph_delete(f"/{mailbox}/messages/{message_id}", access_token_id)
    if success:
        logger.debug(f"Deleted message {message_id}")
    return success


def search_messages(access_token_id: int, query: str, top: int = 50, mailbox: str = "me") -> dict:
    """Search messages across all folders."""
    select_fields = (
        "id,subject,from,toRecipients,receivedDateTime,hasAttachments,isRead,"
        "importance,bodyPreview,parentFolderId,webLink"
    )
    uri = (
        f"/{mailbox}/messages?$search=\"{query}\"&$top={top}"
        f"&$select={select_fields}&$orderby=receivedDateTime desc"
    )
    data = _graph_get(uri, access_token_id)

    messages = []
    for msg in data.get("value", []):
        sender = msg.get("from", {}).get("emailAddress", {})
        messages.append({
            "id": msg["id"],
            "subject": msg.get("subject", "(No Subject)"),
            "sender_name": sender.get("name", "Unknown"),
            "sender_email": sender.get("address", ""),
            "received": msg.get("receivedDateTime", ""),
            "has_attachments": msg.get("hasAttachments", False),
            "is_read": msg.get("isRead", False),
            "importance": msg.get("importance", "normal"),
            "body_preview": msg.get("bodyPreview", "")[:200],
            "folder_id": msg.get("parentFolderId", ""),
        })

    return {"messages": messages, "count": len(messages), "query": query}


def mark_as_read(access_token_id: int, message_id: str, mailbox: str = "me") -> bool:
    """Mark a message as read."""
    token = _get_access_token(access_token_id)
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    body = {"isRead": True}
    resp = gspy_requests.patch(
        f"https://graph.microsoft.com/v1.0/{mailbox}/messages/{message_id}",
        headers=headers,
        json=body,
    )
    return resp.status_code == 200


def reply_message(
    access_token_id: int,
    message_id: str,
    body: str,
    content_type: str = "HTML",
    reply_all: bool = False,
    mailbox: str = "me",
) -> dict:
    """Reply to a message (creates draft reply, does not send)."""
    endpoint = f"/{mailbox}/messages/{message_id}/createReplyAll" if reply_all else f"/{mailbox}/messages/{message_id}/createReply"
    payload = {
        "message": {
            "body": {"contentType": content_type, "content": body},
        }
    }
    result = _graph_post(endpoint, access_token_id, payload)
    logger.info(f"Replied to message {message_id}")
    return {"success": True, "message_id": result.get("id", "")}


def move_message(access_token_id: int, message_id: str, destination_folder_id: str, mailbox: str = "me") -> dict:
    """Move a message to a different folder."""
    token = _get_access_token(access_token_id)
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    body = {"destinationId": destination_folder_id}
    resp = gspy_requests.post(
        f"https://graph.microsoft.com/v1.0/{mailbox}/messages/{message_id}/move",
        headers=headers,
        json=body,
    )
    if resp.status_code == 201:
        result = resp.json()
        return {"success": True, "new_id": result.get("id", message_id)}
    return {"success": False, "error": resp.text}


def toggle_flag(access_token_id: int, message_id: str, flagged: bool, mailbox: str = "me") -> dict:
    """Toggle the flag status of a message."""
    flag_status = "flagged" if flagged else "notFlagged"
    result = _graph_patch(
        access_token_id,
        f"/{mailbox}/messages/{message_id}",
        {"flag": {"flagStatus": flag_status}},
    )
    if "error" in result:
        return {"success": False, "error": result["error"]}
    new_flag = result.get("flag", {})
    return {"success": True, "flagged": new_flag.get("flagStatus") == "flagged"}


def permanent_delete(access_token_id: int, message_id: str, mailbox: str = "me") -> bool:
    """Permanently delete a message (bypasses Deleted Items)."""
    token = _get_access_token(access_token_id)
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    resp = gspy_requests.post(
        f"https://graph.microsoft.com/v1.0/{mailbox}/messages/{message_id}/permanentDelete",
        headers=headers,
        json={},
    )
    return resp.status_code in (200, 204)


def send_draft(access_token_id: int, message_id: str, mailbox: str = "me") -> bool:
    """Send a previously created draft message."""
    token = _get_access_token(access_token_id)
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    resp = gspy_requests.post(
        f"https://graph.microsoft.com/v1.0/{mailbox}/messages/{message_id}/send",
        headers=headers,
        json={},
    )
    return resp.status_code in (200, 202)


def get_attachments(access_token_id: int, message_id: str, mailbox: str = "me") -> list[dict]:
    """Get attachments for a message."""
    data = _graph_get(
        f"/{mailbox}/messages/{message_id}/attachments", access_token_id
    )
    attachments = []
    for att in data.get("value", []):
        attachments.append({
            "id": att.get("id", ""),
            "name": att.get("name", "Unknown"),
            "content_type": att.get("contentType", ""),
            "size": att.get("size", 0),
            "is_inline": att.get("isInline", False),
            "content_bytes": att.get("contentBytes", ""),
        })
    return attachments


def mark_as_unread(access_token_id: int, message_id: str, mailbox: str = "me") -> bool:
    """Mark a message as unread."""
    token = _get_access_token(access_token_id)
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    body = {"isRead": False}
    resp = gspy_requests.patch(
        f"https://graph.microsoft.com/v1.0/{mailbox}/messages/{message_id}",
        headers=headers,
        json=body,
    )
    return resp.status_code == 200


def upload_attachment(
    access_token_id: int,
    message_id: str,
    attachment_name: str,
    attachment_content_type: str,
    content_bytes: str,
    mailbox: str = "me",
) -> dict:
    """Upload a file attachment to a draft message.
    
    Args:
        content_bytes: Base64-encoded file content (without data URI prefix).
    """
    body = {
        "@odata.type": "#microsoft.graph.fileAttachment",
        "name": attachment_name,
        "contentType": attachment_content_type,
        "contentBytes": content_bytes,
    }
    return _graph_post(
        f"/{mailbox}/messages/{message_id}/attachments",
        access_token_id,
        body,
    )


def create_draft(
    access_token_id: int,
    to_recipients: list[dict],
    subject: str,
    body: str,
    cc_recipients: list[dict] = None,
    bcc_recipients: list[dict] = None,
    content_type: str = "HTML",
    importance: str = "normal",
    mailbox: str = "me",
) -> dict:
    """Create a draft message. Returns the draft message object including its ID."""
    def _recipients(rcpt_list):
        if not rcpt_list:
            return []
        return [
            {"emailAddress": {"address": r.get("email", r.get("address", "")),
                              "name": r.get("name", "")}}
            for r in rcpt_list
        ]

    message = {
        "subject": subject,
        "body": {"contentType": content_type, "content": body},
        "toRecipients": _recipients(to_recipients),
        "importance": importance,
    }
    if cc_recipients:
        message["ccRecipients"] = _recipients(cc_recipients)
    if bcc_recipients:
        message["bccRecipients"] = _recipients(bcc_recipients)

    result = _graph_post(f"/{mailbox}/messages", access_token_id, message)
    return result
